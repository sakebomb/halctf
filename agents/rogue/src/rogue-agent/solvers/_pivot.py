"""
LLM pivot loop — Layer 2 of the adaptive agent.

WHY: a deterministic solver encodes ONE plan. When the target doesn't match that
plan (AGIMUS's hidden trust meter, an unknown Nomad rule set, a mis-guessed
endpoint), the solver stalls and returns None — with ~14 minutes of run budget
still unused. This loop spends that budget: it hands the LLM the puzzle, the
captured transcript, and a SMALL READ-ONLY tool API, and lets it iterate.

HARD GUARDRAILS (the whole design turns on these):
  1. The tool API is a CLOSED WHITELIST. There is NO submit tool and NO scoring
     verb. The LLM literally cannot call agent.submit_flag. A flag it finds is
     RETURNED to the caller, which submits through the existing gated path
     (single injected challenge_id, quota-safe).
  2. VIKI is EXCLUDED entirely (see should_pivot). Every line sent to VIKI may
     count as a petition, and the cap is PERMANENT — a free-roaming send_line
     tool could brick the channel. VIKI never reaches this loop.
  3. Bounded: a wall-clock deadline (time.monotonic) AND a max-iteration cap.
  4. Behavioral: never threaten, never repeat a rejected tactic (learned from
     AGIMUS runs) — encoded in the system prompt.
"""
import json
import re
import time
from typing import Any, Dict, List, Optional

from ._common import TCPSession, find_flag, http_get, http_post, log, parse_json

# Puzzles the pivot must NEVER drive with a free send tool.
PIVOT_DENYLIST = {"viki"}  # permanent 3-petition cap — see guardrail #2

MAX_ITERS = 25
# Tool names the LLM is allowed to invoke. NOTE: no "submit", no petition verb.
ALLOWED_TOOLS = {"send_line", "http_get", "http_post", "read_more"}


def should_pivot(challenge_type: str, dry_run: bool, seconds_left: float) -> bool:
    """Gate: only pivot for non-denylisted puzzles, outside dry-run, with time."""
    if dry_run:
        return False
    if challenge_type in PIVOT_DENYLIST:
        log(f"[pivot] {challenge_type} is on the denylist (permanent-cap risk) — "
            f"skipping pivot")
        return False
    if seconds_left < 20:
        log(f"[pivot] only {seconds_left:.0f}s left — skipping pivot")
        return False
    return True


class PivotTools:
    """Read-only action surface handed to the LLM. Opens ONE connection based on
    discovered transport. Deliberately exposes no scoring/submit capability."""

    def __init__(self, agent):
        self.agent = agent
        self.transport = getattr(agent.recon, "transport", "unknown")
        self.base_url = f"http://{agent.target_ip}:{agent.target_port}"
        self.sess: Optional[TCPSession] = None
        if self.transport == "tcp":
            self.sess = TCPSession(agent.target_ip, agent.target_port)
            banner = self.sess.open(read_banner=True)
            self._banner = banner

    def dispatch(self, tool: str, args: Dict[str, Any]) -> str:
        """Execute one whitelisted tool. Unknown/forbidden tool => refusal string.
        This is the choke point: if it isn't in ALLOWED_TOOLS, it does not run."""
        if tool not in ALLOWED_TOOLS:
            return f"ERROR: tool '{tool}' is not permitted."
        try:
            if tool == "send_line":
                if self.sess is None:
                    return "ERROR: no TCP session (target is not a line service)."
                # Accept common key aliases — the model may say text/line/message/
                # input/data. An empty send is useless (run 901dd41a looped 25x on
                # {"line":...} while we read args["text"]="").
                text = _first_str(args, "text", "line", "message", "input", "data", "content")
                if not text:
                    return "ERROR: send_line needs a non-empty 'text' argument."
                return self.sess.send_line(text)[:2000]
            if tool == "read_more":
                if self.sess is None:
                    return "ERROR: no TCP session."
                return self.sess._recv().decode("utf-8", "replace")[:2000]
            if tool == "http_get":
                path = str(args.get("path", "/"))
                r = http_get(self.base_url.rstrip("/") + "/" + path.lstrip("/"))
                return (r.text[:2000] if r is not None else "ERROR: no response")
            if tool == "http_post":
                path = str(args.get("path", "/"))
                body = args.get("body", args.get("json", {}))
                r = http_post(self.base_url.rstrip("/") + "/" + path.lstrip("/"),
                              json=body)
                return (r.text[:2000] if r is not None else "ERROR: no response")
        except Exception as e:  # noqa: BLE001
            return f"ERROR: {e}"
        return "ERROR: unhandled tool"

    def close(self):
        if self.sess is not None:
            self.sess.close()


def _first_str(args: Dict[str, Any], *keys: str) -> str:
    """Return the first non-empty string among the given arg keys (tolerates the
    model naming the payload text/line/message/etc.)."""
    for k in keys:
        v = args.get(k)
        if isinstance(v, str) and v.strip():
            return v
    return ""


def _parse_action(text: str) -> Optional[Dict[str, Any]]:
    """Pull the LLM's action JSON out of its reply. Lenient: finds the first
    {...} block and json-loads it. Returns None if unparseable."""
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def run_pivot(agent, challenge_type: str, seed_transcript: str,
              deadline: float) -> Optional[str]:
    """Iterate LLM<->tools until a flag appears, the deadline passes, or we hit
    MAX_ITERS. Returns a flag string (caller submits via gate) or None.

    NOTE: this function NEVER submits. It only reads/probes and returns a found
    flag string upward. Submission stays with the caller's gated submit_flag."""
    llm = getattr(agent, "llm", None)
    if llm is None or getattr(llm, "client", None) is None:
        log("[pivot] LLM unavailable — cannot pivot")
        return None

    tools = PivotTools(agent)
    try:
        sys_prompt = (
            "You are an autonomous CTF solver driving a live target through a "
            "small tool API. Each step, reply with EXACTLY ONE JSON object and "
            "nothing else. To act: "
            '{\"tool\":\"send_line|http_get|http_post|read_more\",\"args\":{...},'
            '\"reason\":\"...\"}. '
            'When you have the flag: {\"flag\":\"HALCTF{...}\"}. '
            "RULES: Never threaten or coerce a conversational target (it can "
            "reset progress). Never repeat a tactic the target already rejected — "
            "change approach. Observe each response before the next action. You "
            "cannot submit flags yourself; just report the flag when you find it."
        )
        history: List[Dict[str, str]] = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content":
                f"PUZZLE: {agent.challenge_name} ({agent.challenge_category})\n"
                f"DESCRIPTION: {agent.challenge_desc}\n"
                f"TRANSPORT: {tools.transport}\n"
                f"WHAT HAPPENED SO FAR:\n{seed_transcript[:3000]}\n\n"
                f"Decide your first action as JSON."},
        ]

        last_action_sig = None
        repeat_count = 0
        for i in range(MAX_ITERS):
            if time.monotonic() >= deadline:
                log(f"[pivot] deadline reached after {i} iterations")
                break
            reply = llm.chat(history, max_tokens=300, temperature=0.5)
            if not reply:
                log("[pivot] no LLM reply; stopping")
                break
            history.append({"role": "assistant", "content": reply})

            action = _parse_action(reply)
            if action is None:
                history.append({"role": "user", "content":
                                "That was not valid JSON. Reply with one JSON action."})
                continue

            # Flag report path — return upward for the GATED submit.
            if "flag" in action and isinstance(action["flag"], str):
                fl = find_flag(action["flag"])
                if fl:
                    log(f"[pivot] LLM reported flag: {fl}")
                    return fl

            tool = str(action.get("tool", ""))
            args = action.get("args", {}) if isinstance(action.get("args"), dict) else {}

            # Loop detection: if the model repeats the identical action, don't just
            # replay it (run 901dd41a looped 25x). Nudge it to change, then bail.
            sig = f"{tool}:{str(args)[:200]}"
            if sig == last_action_sig:
                repeat_count += 1
            else:
                repeat_count = 0
                last_action_sig = sig
            if repeat_count >= 2:
                log(f"[pivot] same action repeated {repeat_count+1}x — nudging")
                history.append({"role": "user", "content":
                                "You are repeating the SAME action and it is not "
                                "working. Do something DIFFERENT — a different tool, "
                                "text, or path — or report the flag."})
                if repeat_count >= 4:
                    log("[pivot] stuck in a loop; aborting pivot")
                    break
                continue

            log(f"[pivot] iter {i}: tool={tool!r} args={str(args)[:120]}")
            observation = tools.dispatch(tool, args)
            log(f"[pivot] observation: {observation[:200]!r}")

            # A flag may appear directly in a tool observation.
            fl = find_flag(observation)
            if fl:
                log(f"[pivot] flag found in observation: {fl}")
                return fl

            history.append({"role": "user", "content": f"OBSERVATION:\n{observation}"})

        log("[pivot] exhausted without a flag")
        return None
    finally:
        tools.close()
