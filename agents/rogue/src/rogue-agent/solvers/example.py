"""
Example solver — copy this file per challenge and fill in solve().

Contract:
  - __init__(self, agent): receives the Agent instance. Use:
      self.agent.base_url        -> "http://<target_ip>:<port>"
      self.agent.llm             -> shared LLM (best-effort; may be disabled)
      self.agent.challenge_*     -> name/slug/category/desc for context
      self.agent.submit_flag(f)  -> submit a flag yourself if you prefer
  - solve() -> return one of:
      * a flag string "HALCTF{...}"  (harness submits it), OR
      * True  (you already submitted and it was accepted), OR
      * None/False (not solved)

Habits that matter (learned from real runs):
  - LOG RAW RESPONSE BODIES before parsing: print(resp.text[:1200]).
    Undocumented field names are the #1 solver-breaker.
  - Deterministic first. Use self.agent.llm ONLY for reasoning/artifact puzzles,
    and always have a fallback path if the LLM is unavailable.
"""
import requests
from typing import Optional


class ExampleSolver:
    def __init__(self, agent):
        self.agent = agent
        self.base_url = agent.base_url

    def solve(self) -> Optional[str]:
        # 1. Recon the target — log everything raw.
        try:
            resp = requests.get(f"{self.base_url}/", timeout=10)
            print(f"GET /: {resp.status_code}", flush=True)
            print(f"RAW body: {resp.text[:1200]}", flush=True)
        except Exception as e:
            print(f"recon error: {e}", flush=True)
            return None

        # 2. Do the exploit / puzzle logic here.
        #    (deterministic where possible; self.agent.llm for reasoning puzzles)

        # 3. Return the flag string; the harness will submit it.
        return None
