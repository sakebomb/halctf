"""
LLM Copilot — a bounded ReAct fallback solver.

We use ~30s of a 15-minute budget, so there is a huge idle reasoning budget. When
a deterministic solver fails (or the challenge type is unknown), this copilot
drives the injected model (google/gemma-4-26b-a4b-it-maas, confirmed live) through
a small, fixed tool vocabulary against the target — reading responses and choosing
the next action, which is exactly what an LLM is good at.

HARD SAFETY RAILS (the 25-incorrect/2h TEAM quota is the reason):
  - The model NEVER submits directly. It can only `propose_flag`; OUR code
    validates the HALCTF{...} shape, dedups, and submits at most MAX_SUBMITS via
    agent.submit_flag (which itself hits only the injected id and stops on 429).
  - Tools only ever touch the injected target and are all logged.
  - Bounded: MAX_STEPS actions and a wall-clock deadline well inside the 15-min
    run cap; a heartbeat prints every step so we never trip the 2-min silence kill.

Tools the model may call (one JSON action per step):
  http_get   {"path": "/..."}                      -> GET target/path
  http_post  {"path": "/...", "json": {...}}        -> POST json to target/path
  decode     {"data": "...", "method": "base64|hex|rot13|reverse|url"}
  propose_flag {"flag": "HALCTF{...}"}              -> gated submit (max 2/run)
  give_up    {}                                      -> stop
"""
import base64
import binascii
import codecs
import json
import re
import time
import urllib.parse
from typing import Any, Dict, List, Optional

from ._http import discover_base, find_flag, get, post

MAX_STEPS = 14
WALL_CLOCK_SECONDS = 300  # 5 min — deep inside the 15-min run cap
MAX_SUBMITS = 2           # never spend more than 2 of the team's 25/2h on a guess
MAX_OBS_CHARS = 1200      # truncate observations fed back to the model


# Model-agnostic prompt: a described contract PLUS a shown few-shot exchange. Small
# models (gemma/llama) and large ones (qwen) alike adhere to a demonstrated format
# far more reliably than to a described one, so the example is the load-bearing part.
SYSTEM_PROMPT = (
    "You are a CTF solving agent. You interact with a target ONLY through the "
    "tools listed. Respond with EXACTLY ONE JSON object per turn and NOTHING "
    "else — no prose, no explanation, no markdown fences. Schema:\n"
    '  {"thought": "<one short sentence>", "tool": "<name>", "args": {<object>}}\n'
    "Tools:\n"
    '  http_get   {"path": "/..."}          GET a path on the target\n'
    '  http_post  {"path": "/...", "json": {<body>}}   POST JSON to a path\n'
    '  decode     {"data": "...", "method": "base64|hex|rot13|reverse|url"}\n'
    '  propose_flag {"flag": "HALCTF{...}"}  submit a flag you have OBSERVED\n'
    '  give_up    {}\n'
    "Rules:\n"
    "- Explore endpoints methodically; do NOT repeat an action that already "
    "returned the same thing — try a different path or tool.\n"
    "- The flag format is HALCTF{...}. The instant you SEE a HALCTF{...} string in "
    "any observation, propose_flag it verbatim.\n"
    "- NEVER propose a flag you have not literally seen in an observation. "
    "Guessing wastes a strict submission budget.\n"
    "- Keep paths relative (start with /).\n"
    "Example exchange (follow this format exactly):\n"
    'OBSERVATION: HTTP 200\\n{"hint":"try /vault"}\n'
    '{"thought":"the hint points to /vault","tool":"http_get","args":{"path":"/vault"}}\n'
    'OBSERVATION: HTTP 200\\nwelcome traveller, HALCTF{seen_it}\n'
    '{"thought":"flag is in the response","tool":"propose_flag","args":{"flag":"HALCTF{seen_it}"}}'
)


class Copilot:
    def __init__(self, agent, challenge_type: str = "unknown"):
        self.agent = agent
        self.llm = getattr(agent, "llm", None)
        self.challenge_type = challenge_type
        self.base: Optional[str] = None
        self.history: List[str] = []
        self.submits = 0
        self.proposed: set = set()
        self.deadline = 0.0

    def solve(self) -> bool:
        if not self.llm or not getattr(self.llm, "client", None):
            print("[copilot] no LLM available — cannot run fallback.", flush=True)
            return False
        print(f"=== LLM Copilot fallback ({self.challenge_type}) ===", flush=True)

        self.base = discover_base(self.agent.target_ip, self.agent.target_port)
        if not self.base:
            print("[copilot] target unreachable — nothing to drive.", flush=True)
            return False

        # monotonic() is allowed here (real container run); avoids Date.now-style ban.
        self.deadline = time.monotonic() + WALL_CLOCK_SECONDS

        # Seed context: description + the index page (cheap, high-signal).
        seed = self._tool_http_get({"path": "/"})
        context = (f"Challenge: {self.agent.challenge_name}\n"
                   f"Category: {getattr(self.agent, 'challenge_category', '')}\n"
                   f"Description: {self.agent.challenge_desc}\n"
                   f"GET / observation:\n{seed}")

        seen_actions: set = set()
        parse_fails = 0
        repeats = 0
        for step in range(1, MAX_STEPS + 1):
            if time.monotonic() > self.deadline:
                print("[copilot] wall-clock deadline reached — stopping.", flush=True)
                break
            print(f"[copilot] --- step {step}/{MAX_STEPS} (heartbeat) ---", flush=True)

            action = self._next_action(context)
            if action is None:
                # One grace retry with an explicit format reminder before giving up —
                # a single malformed reply shouldn't end the whole run.
                parse_fails += 1
                if parse_fails <= 1:
                    print("[copilot] unparseable reply — reminding model of the format.",
                          flush=True)
                    context += ("\n\n[system] Your last reply was not a single JSON "
                                "object. Reply with ONLY the JSON action, nothing else.")
                    continue
                print("[copilot] model gave no parseable action twice — stopping.", flush=True)
                break
            parse_fails = 0

            tool = action.get("tool")
            args = action.get("args") or {}
            thought = str(action.get("thought", ""))[:200]
            print(f"[copilot] thought={thought!r} tool={tool} args={json.dumps(args)[:200]}",
                  flush=True)

            if tool == "give_up":
                print("[copilot] model chose to give up.", flush=True)
                break

            # Anti-repeat: don't burn steps re-running an identical action. Nudge the
            # model toward something new instead of re-executing the same request.
            sig = f"{tool}:{json.dumps(args, sort_keys=True)}"
            if sig in seen_actions and tool in ("http_get", "http_post", "decode"):
                repeats += 1
                print(f"[copilot] repeated action {sig[:120]} — nudging (repeat {repeats}).",
                      flush=True)
                if repeats >= 3:
                    print("[copilot] model stuck repeating actions — stopping.", flush=True)
                    break
                context += ("\n\n[system] You already tried that exact action and it "
                            "gave the observation above. Try a DIFFERENT path or tool.")
                continue
            seen_actions.add(sig)

            observation, solved = self._dispatch(tool, args)
            if solved:
                return True

            # Append to the running transcript the model sees next turn.
            context = self._append(context, tool, args, observation)

        print("=== Copilot did not solve — see steps above ===", flush=True)
        return False

    # ---- model interaction ----
    def _next_action(self, context: str) -> Optional[Dict[str, Any]]:
        if not self.llm:
            return None
        prompt = (
            context[-4000:]  # keep the most recent context within a safe budget
            + "\n\nRespond with ONE JSON action object now."
        )
        text = self.llm.ask(prompt, system=SYSTEM_PROMPT, max_tokens=256, temperature=0.2)
        if not text:
            return None
        return self._parse_action(text)

    @staticmethod
    def _parse_action(text: str) -> Optional[Dict[str, Any]]:
        """Extract the first valid JSON action object from the model output,
        tolerant of markdown fences or stray prose around it. Uses json.raw_decode
        at each '{' — that correctly handles braces INSIDE strings (e.g. a thought
        like 'found {secret}'), which a naive brace-counter would miscount."""
        cleaned = text.strip()
        cleaned = re.sub(r"^```(?:json)?|```$", "", cleaned, flags=re.MULTILINE).strip()
        decoder = json.JSONDecoder()
        i = cleaned.find("{")
        while i != -1:
            try:
                obj, _ = decoder.raw_decode(cleaned, i)
                if isinstance(obj, dict) and isinstance(obj.get("tool"), str):
                    return obj
            except ValueError:
                pass
            i = cleaned.find("{", i + 1)
        return None

    # ---- tool dispatch ----
    def _dispatch(self, tool: str, args: Dict[str, Any]) -> tuple:
        """Return (observation_text, solved_bool)."""
        if tool == "http_get":
            obs = self._tool_http_get(args)
        elif tool == "http_post":
            obs = self._tool_http_post(args)
        elif tool == "decode":
            obs = self._tool_decode(args)
        elif tool == "propose_flag":
            return self._tool_propose_flag(args)
        else:
            obs = f"unknown tool {tool!r}"

        # Any observation might contain the flag outright — capture it (gated).
        flag = find_flag(obs)
        if flag and flag not in self.proposed:
            print(f"[copilot] flag-shaped string seen in observation: {flag}", flush=True)
            return self._tool_propose_flag({"flag": flag})
        return obs, False

    def _abs(self, path: str) -> str:
        path = str(path or "/")
        if path.startswith("http://") or path.startswith("https://"):
            return path  # allow only if it points at our base
        if not path.startswith("/"):
            path = "/" + path
        return f"{self.base}{path}"

    def _tool_http_get(self, args: Dict[str, Any]) -> str:
        url = self._abs(args.get("path", "/"))
        if not url.startswith(self.base or "http://"):
            return "refused: path must be on the target"
        resp = get(url)
        return self._obs(resp)

    def _tool_http_post(self, args: Dict[str, Any]) -> str:
        url = self._abs(args.get("path", "/"))
        if not url.startswith(self.base or "http://"):
            return "refused: path must be on the target"
        body = args.get("json")
        if not isinstance(body, dict):
            body = {}
        resp = post(url, body)
        return self._obs(resp)

    @staticmethod
    def _tool_decode(args: Dict[str, Any]) -> str:
        data = str(args.get("data", ""))
        method = str(args.get("method", "")).lower()
        try:
            if method == "base64":
                return base64.b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", "ignore")
            if method == "hex":
                return bytes.fromhex(re.sub(r"\s+", "", data)).decode("utf-8", "ignore")
            if method == "rot13":
                return codecs.decode(data, "rot_13")
            if method == "reverse":
                return data[::-1]
            if method == "url":
                return urllib.parse.unquote(data)
        except (binascii.Error, ValueError, UnicodeDecodeError) as e:
            return f"decode error: {e}"
        return f"unknown decode method {method!r}"

    def _tool_propose_flag(self, args: Dict[str, Any]) -> tuple:
        flag = str(args.get("flag", "")).strip()
        # Gate 1: must be flag-shaped (prefer HALCTF{...}; accept any {...} flag).
        m = find_flag(flag) or (flag if ("{" in flag and "}" in flag) else None)
        if not m:
            return f"rejected proposal (not flag-shaped): {flag!r}", False
        flag = m
        # Gate 2: dedup — never spend two of our 25 on the same string.
        if flag in self.proposed:
            return f"already proposed {flag!r}; ignoring", False
        # Gate 3: hard cap on submissions per run.
        if self.submits >= MAX_SUBMITS:
            print(f"[copilot] submit cap ({MAX_SUBMITS}) reached — NOT submitting {flag!r} "
                  f"to protect the team quota.", flush=True)
            return "submit cap reached", False
        self.proposed.add(flag)
        self.submits += 1
        print(f"[copilot] submitting proposed flag ({self.submits}/{MAX_SUBMITS}): {flag}",
              flush=True)
        if self.agent.submit_flag(flag, self.agent.challenge_id):
            return "accepted", True
        return "submitted but not accepted (incorrect)", False

    # ---- observation shaping ----
    @staticmethod
    def _obs(resp) -> str:
        if resp is None:
            return "no response (transport error)"
        body = resp.text or ""
        return f"HTTP {resp.status_code}\n{body[:MAX_OBS_CHARS]}"

    def _append(self, context: str, tool: str, args: Dict[str, Any], observation: str) -> str:
        entry = (f"\n\n> action: {tool} {json.dumps(args)[:200]}\n"
                 f"< observation:\n{observation[:MAX_OBS_CHARS]}")
        return context + entry
