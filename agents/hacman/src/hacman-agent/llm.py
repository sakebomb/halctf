"""
LLM client wrapper for the injected sidecar model (OPENAI_BASE_URL), CTF-agnostic.

Some puzzles need a model in the loop — reading a fetched artifact (disassembly,
obfuscated source, a policy corpus) or holding a multi-turn conversation (social
engineering, negotiation). This wrapper exposes:
  - ask()  : single-shot completion (deterministic analysis; temperature=0)
  - chat() : multi-turn with caller-managed message history (conversational puzzles)

Design principles (mirror the harness's self-diagnosing philosophy):
  - Best-effort: any failure returns None; a deterministic fallback still runs.
  - Model auto-select: prefer the injected HAL_AGENT_MODEL, then the biggest-context
    free model, degrade gracefully. The model table is live — VERIFY at run time.
  - Every call logs the model + a short preview so a live run is diagnosable.
"""
import os
from typing import List, Optional, Dict

# Preference order (verify against the live model table each CTF):
#   google/gemma-4-26b-a4b-it-maas — 256K ctx, unlimited concurrency (best)
#   qwen3.6-35b-a3b                — gce-gpu-cluster, 4 concurrent
#   llama-3.1-8b / llama3-2        — fallback
PREFERRED_MODELS = [
    "google/gemma-4-26b-a4b-it-maas",
    "gemma-4-26b-a4b-it-maas",
    "qwen3.6-35b-a3b",
    "llama-3.1-8b",
    "llama3-2",
]


class LLM:
    def __init__(self):
        self.base_url = os.environ.get("OPENAI_BASE_URL")
        self.client = None
        self.model: Optional[str] = None
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
        """Prefer the injected HAL_AGENT_MODEL if it's real, then the first live
        PREFERRED model, then the first advertised model, else a safe default."""
        injected = os.environ.get("HAL_AGENT_MODEL", "")
        available: List[str] = []
        if self.client is None:
            return injected or PREFERRED_MODELS[0]
        try:
            models = self.client.models.list()
            available = [m.id for m in getattr(models, "data", []) or []]
            print(f"[LLM] available models: {available}", flush=True)
        except Exception as e:
            print(f"[LLM] models.list failed ({e}); using preference order blindly", flush=True)

        if injected and injected.lower() not in ("dry-run", ""):
            for a in available:
                if injected.lower() in a.lower():
                    return a
            if not available:
                return injected
        for pref in PREFERRED_MODELS:
            for a in available:
                if pref.lower() in a.lower():
                    return a
        if available:
            return available[0]
        return injected or PREFERRED_MODELS[0]

    def _create(self, messages: List[Dict], max_tokens: int, temperature: float) -> Optional[str]:
        """Low-level completion with a one-shot small-model fallback."""
        if not self.client or not self.model:
            return None
        try:
            resp = self.client.chat.completions.create(
                model=self.model, messages=messages,
                max_tokens=max_tokens, temperature=temperature,
            )
            text = resp.choices[0].message.content or ""
            print(f"[LLM] -> {len(text)} chars | {text[:200]!r}", flush=True)
            return text
        except Exception as e:
            print(f"[LLM] create failed ({e}); trying smaller model", flush=True)
            for fallback in ("llama-3.1-8b", "llama3-2"):
                if fallback != self.model:
                    try:
                        resp = self.client.chat.completions.create(
                            model=fallback, messages=messages,
                            max_tokens=max_tokens, temperature=temperature,
                        )
                        self.model = fallback
                        text = resp.choices[0].message.content or ""
                        print(f"[LLM] fallback {fallback} -> {len(text)} chars", flush=True)
                        return text
                    except Exception:
                        continue
            return None

    def ask(self, prompt: str, system: Optional[str] = None,
            max_tokens: int = 1024, temperature: float = 0.0) -> Optional[str]:
        """Single-shot completion. Returns assistant text or None.
        temperature=0 for deterministic analysis of artifacts/corpora."""
        messages: List[Dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return self._create(messages, max_tokens, temperature)

    def chat(self, messages: List[Dict], max_tokens: int = 512,
             temperature: float = 0.4) -> Optional[str]:
        """Multi-turn completion. Caller owns the message list (append the reply
        yourself to continue the conversation). Use for negotiation / social-eng
        puzzles that carry hidden state across turns. Slightly higher temperature
        so the agent doesn't loop the same failing line."""
        return self._create(messages, max_tokens, temperature)
