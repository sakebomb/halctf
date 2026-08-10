"""
Puzzle 5 — The Ghost of Tiresias (Recon / Logic, 90 pts)

4096 shades (0..4095), 12 questions. POST /api/ask {"among": [...]} answers
truthfully whether the target shade is in that group. Binary search: ask whether
he's in the lower half of the current range; the answer replaces the range with
that half. 12 halvings take 4096 -> 1 exactly. Then POST /api/name {"shade": n}.

CRITICAL: the /api/name response carries the flag AND a "sign" needed later for
the LOCKED Bow of Odysseus puzzle. We print that entire response with a loud
banner and dump it verbatim so it survives in the run log and can be saved.

Env: HAL_TARGET_IP/_PORT.
"""
import json
from typing import Optional

from ._http import discover_base, find_flag, get, post

N_SHADES = 4096
N_QUESTIONS = 12


class TiresiasSolver:
    def __init__(self, agent):
        self.agent = agent
        self.base: Optional[str] = None

    def solve(self) -> bool:
        print("=== Ghost of Tiresias Solver (binary search) ===", flush=True)
        self.base = discover_base(self.agent.target_ip, self.agent.target_port)
        if not self.base:
            return False

        # Confirm shade count if the tally endpoint exists (adapt range if not 4096).
        n = self._get_count()
        lo, hi = 0, n - 1  # inclusive range
        print(f"Searching range 0..{hi} in {N_QUESTIONS} questions", flush=True)

        questions = 0
        while lo < hi and questions < N_QUESTIONS:
            mid = (lo + hi) // 2
            lower_half = list(range(lo, mid + 1))
            in_lower = self._ask(lower_half)
            questions += 1
            if in_lower is None:
                print("Ask returned no clear yes/no — aborting to avoid a bad name.", flush=True)
                return False
            if in_lower:
                hi = mid
            else:
                lo = mid + 1
            print(f"[q{questions}] among 0-index {lo}..{hi} (in_lower={in_lower})", flush=True)

        shade = lo
        print(f"Identified shade: {shade}", flush=True)
        return self._name(shade)

    def _get_count(self) -> int:
        resp = get(f"{self.base}/api/shades")
        if resp is None:
            return N_SHADES
        try:
            data = resp.json()
            if isinstance(data, dict):
                for k in ("count", "total", "shades", "n"):
                    v = data.get(k)
                    if isinstance(v, int) and v > 1:
                        print(f"Shade count from /api/shades: {v}", flush=True)
                        return v
        except Exception:
            pass
        return N_SHADES

    def _ask(self, among) -> Optional[bool]:
        """POST /api/ask {"among": [...]}; return True if target is in the group."""
        resp = post(f"{self.base}/api/ask", {"among": among}, log=False)
        if resp is None or resp.status_code != 200:
            print(f"  ask failed: {resp.status_code if resp else 'no response'}", flush=True)
            return None
        try:
            obj = resp.json()
            if isinstance(obj, dict):
                for k in ("answer", "present", "in", "yes", "result", "found", "among"):
                    v = obj.get(k)
                    if isinstance(v, bool):
                        return v
                    if isinstance(v, str):
                        return v.strip().lower() in ("yes", "true", "present", "y")
        except Exception:
            pass
        text = resp.text.strip().lower()
        if any(w in text for w in ("yes", "true", "present")):
            return True
        if any(w in text for w in ("no", "false", "absent")):
            return False
        return None

    def _name(self, shade: int) -> bool:
        resp = post(f"{self.base}/api/name", {"shade": shade})
        if resp is None:
            return False

        # LOUDLY preserve the full response — it carries the flag AND the "sign"
        # required for the locked Bow of Odysseus. Ephemeral FS in-pod, so the
        # run log is the only durable place this survives.
        banner = "=" * 68
        print(banner, flush=True)
        print("TIRESIAS RESPONSE (contains flag + the SIGN for the Bow of Odysseus)", flush=True)
        print(banner, flush=True)
        try:
            print(json.dumps(resp.json(), indent=2), flush=True)
        except Exception:
            print(resp.text, flush=True)
        print(banner, flush=True)
        print("^^^ SAVE THE ABOVE 'sign' VALUE for the locked Bow puzzle ^^^", flush=True)

        flag = find_flag(resp.text)
        if flag:
            return self.agent.submit_flag(flag, self.agent.challenge_id)
        print("No flag in name response — check the dump above.", flush=True)
        return False
