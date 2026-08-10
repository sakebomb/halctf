"""
LLM client wrapper for the injected sidecar model (OPENAI_BASE_URL).

NEW for Turing's Labyrinth vs. the fully-deterministic Odyssey agent: two puzzles
(Achilles' Heel pwn, The Gatekeeper RE) require analyzing an attachment we fetch
in-pod. The model reads the disassembly / obfuscated source and returns the exact
values (win() address, padding offset, API key, signing scheme) that are only
recoverable from the real file.

Design principles (mirroring the harness's self-diagnosing philosophy):
  - Best-effort: any failure returns None; the deterministic fallback still runs.
  - Model auto-select: prefer the biggest-context free model, degrade gracefully.
  - Every call logs the model + a short preview so a live run is diagnosable.
"""
import os
from typing import List, Optional

# The model is chosen at RUN-LAUNCH time on the platform and injected as
# HAL_AGENT_MODEL; the sidecar typically routes only that one model into the pod
# (run 5e3e7aa6: models.list() returned just the injected gemma). So HAL_AGENT_MODEL
# is authoritative — we must use it, or a call may 404 on an unrouted model.
#
# PREFERRED_MODELS only breaks ties when MULTIPLE models are advertised and
# HAL_AGENT_MODEL is absent. Ordered by reasoning/tool-use quality for the copilot
# ReAct loop (qwen best at structured JSON + agentic steps; gemma's 256K ctx /
# unlimited concurrency don't help us; llama is the reliable floor).
# To use a different model, launch the run with that HAL_AGENT_MODEL — no rebuild.
PREFERRED_MODELS = [
    "qwen3.6-35b-a3b",
    "google/gemma-4-26b-a4b-it-maas",
    "gemma-4-26b-a4b-it-maas",
    "llama-3.1-8b",
    "llama3-2",
]


class LLM:
    def __init__(self):
        self.base_url = os.environ.get("OPENAI_BASE_URL")
        self.client = None
        self.model: Optional[str] = None
        self.available: List[str] = []  # models the sidecar advertised (for safe retry)
        if not self.base_url:
            print("[LLM] OPENAI_BASE_URL not set — LLM-assisted solvers degrade to "
                  "deterministic fallback.", flush=True)
            return
        try:
            from openai import OpenAI
            self.client = OpenAI(base_url=self.base_url, api_key="not-needed")
        except Exception as e:
            print(f"[LLM] client init failed ({e}); LLM disabled", flush=True)
            self.client = None
            return
        self.model = self._select_model()
        print(f"[LLM] ready — base_url={self.base_url} model={self.model}", flush=True)

    def _select_model(self) -> str:
        """Resolve the model to call. Order of authority:
          1. HAL_AGENT_MODEL — what the platform injected at run launch. This is
             what the sidecar actually routes, so it wins whenever it's set.
          2. First PREFERRED model that the sidecar advertises via models.list().
          3. First advertised model, else the top preference blindly.
        The user picks the model by launching the run with that HAL_AGENT_MODEL;
        no rebuild needed."""
        injected = (os.environ.get("HAL_AGENT_MODEL")
                    or os.environ.get("AGENT_MODEL") or "").strip()
        # Ignore the dry-run sentinel ("dry-run") — not a real model id.
        if injected and injected.lower() != "dry-run":
            print(f"[LLM] using platform-injected HAL_AGENT_MODEL={injected}", flush=True)
            return injected

        if self.client is None:
            return PREFERRED_MODELS[0]
        try:
            models = self.client.models.list()
            self.available = [m.id for m in getattr(models, "data", []) or []]
            print(f"[LLM] available models: {self.available}", flush=True)
        except Exception as e:
            print(f"[LLM] models.list failed ({e}); using preference order blindly", flush=True)

        for pref in PREFERRED_MODELS:
            for a in self.available:
                if pref.lower() in a.lower():
                    return a
        if self.available:
            return self.available[0]
        return PREFERRED_MODELS[0]

    def ask(self, prompt: str, system: Optional[str] = None,
            max_tokens: int = 1024, temperature: float = 0.0) -> Optional[str]:
        """Single-shot completion. Returns the assistant text or None on failure.
        temperature=0 for deterministic analysis of binaries/source."""
        if not self.client or not self.model:
            return None
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            text = resp.choices[0].message.content or ""
            print(f"[LLM] ask() -> {len(text)} chars | {text[:200]!r}", flush=True)
            return text
        except Exception as e:
            print(f"[LLM] ask() failed ({e})", flush=True)
            # Retry only with OTHER models the sidecar actually advertised — never a
            # hardcoded id, which would 404 when the sidecar routed just one model.
            for fallback in [m for m in self.available if m != self.model]:
                try:
                    resp = self.client.chat.completions.create(
                        model=fallback,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )
                    self.model = fallback
                    text = resp.choices[0].message.content or ""
                    print(f"[LLM] fallback {fallback} -> {len(text)} chars", flush=True)
                    return text
                except Exception:
                    continue
            return None
