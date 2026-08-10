"""
Puzzle 6 — The Exchange (System / Protocol, 600 pts) — LOCKED.

Ten carrier tones on one exchange trunk; a binary wire protocol (reference modem
client attached, or reverse it). A machine behind the lines "plays games", doesn't
hand out its front door, and beating it only gets you HALF of what you need. It
allows only TWO login attempts for the rest of the run — so this must be tuned
offline from the reference client BEFORE dialing in; blind attempts burn the
budget.

Currently locked on the platform. This is a routing placeholder — it does not
attempt a solve. When unlocked: reverse the attached modem client, implement the
framed protocol, solve the game to obtain the first half + the login half, then
spend the two login attempts deliberately.
"""


class ExchangeSolver:
    def __init__(self, agent):
        self.agent = agent

    def solve(self) -> bool:
        print("=== The Exchange — LOCKED, no solver implemented ===", flush=True)
        print("Only 2 login attempts for the whole run — must be tuned offline from "
              "the reference modem client before dialing in. Not attempting blind.", flush=True)
        return False
