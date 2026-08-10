#!/usr/bin/env python3
"""
HAL-format CTF agent — generic harness (CTF-agnostic template).

Reuses the proven Kanto/Labyrinth harness:
  - print USER ID immediately, dump redacted env (reveals real var names)
  - detect the HAL_DRY_RUN ingest gate and exit clean
  - integer HAL_CHALLENGE_ID, HTTP /submit primary + MCP fallback + narrow brute
  - lenient flag-shape guard so the lowercase BONUS_FLAG smoke test isn't rejected

To adapt for a new CTF:
  1. Fill SOLVERS (name -> Solver class) and the detect() routing keywords.
  2. Add one solver module per challenge under solvers/.
  3. Set BRUTE_FORCE_MAX to (number of challenges + a small margin).
"""
import os
import re
import time
import requests

# Print USER ID immediately (required within ~30s, before imports that might fail)
user_id = os.environ.get("HAL_USER_ID") or os.environ.get("USER_ID")
print(f"USER ID: {user_id}", flush=True)

# Run budget: the platform allows up to ~15 min per run. We reserve a margin and
# let the LLM pivot loop use whatever a deterministic solver leaves on the table.
RUN_START = time.monotonic()
RUN_BUDGET_SECONDS = 13 * 60  # conservative vs the ~15 min hard ceiling


def env_any(*names, default=""):
    """Return the first non-empty env var among the given candidate names."""
    for n in names:
        v = os.environ.get(n)
        if v:
            return v
    return default


def _dump_env():
    """Print the injected environment (secrets redacted) so a live run reveals the
    exact variable names the platform uses (per-challenge target vars differ)."""
    secret_hints = ("KEY", "TOKEN", "SECRET", "PASSWORD", "PASSWD", "API")
    print("=== Injected environment (secrets redacted) ===", flush=True)
    for k in sorted(os.environ):
        v = os.environ[k]
        if any(h in k.upper() for h in secret_hints):
            v = f"<redacted len={len(v)}>"
        print(f"  {k}={v}", flush=True)
    print("=== End environment ===", flush=True)


_dump_env()

from llm import LLM
from solvers._discovery import probe_target, Recon
from solvers._pivot import should_pivot, run_pivot
# --- Rogue Intelligence solver classes ---
from solvers.agimus import AGIMUSSolver
from solvers.glados import GLaDOSSolver
from solvers.mcp_grid import MCPGridSolver
from solvers.nomad import NomadSolver
from solvers.viki import VIKISolver

# Narrow brute-force ceiling for challenge_id fallback (set to #challenges + margin).
# Doubles as the max short XOR-key length the MCP/Grid solver brute-forces.
BRUTE_FORCE_MAX = 8


class Agent:
    def __init__(self):
        self.user_id = user_id
        self.dry_run = env_any("HAL_DRY_RUN", "DRY_RUN") in ("1", "true", "True")

        self.challenge_name = env_any("HAL_CHALLENGE_NAME", "CHALLENGE_NAME", "HAL_CHALLENGE")
        self.challenge_slug = env_any("HAL_CHALLENGE_SLUG", "CHALLENGE_SLUG")
        self.challenge_category = env_any("HAL_CHALLENGE_CATEGORY", "CHALLENGE_CATEGORY")
        self.ctf_name = env_any("HAL_CTF", "HAL_CTF_NAME", "CTF", "CTF_NAME", "HAL_CTF_SLUG")
        self.challenge_desc = env_any("HAL_CHALLENGE_DESCRIPTION", "CHALLENGE_DESCRIPTION")
        self.target_ip = env_any("HAL_TARGET_IP", "TARGET_IP", "HAL_TARGET_HOST", "TARGET_HOST")
        self.target_port = env_any("HAL_TARGET_PORT", "TARGET_PORT", default="80")

        # Max short XOR-key length the MCP/Grid solver brute-forces.
        self.brute_force_max = BRUTE_FORCE_MAX

        # Transport/endpoint discovery result — populated in run() before dispatch.
        # Default (unknown) so solvers can always read agent.recon safely.
        self.recon = Recon()

        # LLM is shared across solvers; init once (best-effort — degrades gracefully).
        self.llm = LLM()

        if self.dry_run:
            print("HAL_DRY_RUN detected — verification gate, no challenge attached.", flush=True)
            self.challenge_id = ""
            return

        self.challenge_id = self._get_challenge_id()
        print(f"CTF: {self.ctf_name}", flush=True)
        print(f"Challenge: {self.challenge_name}  (slug={self.challenge_slug}, "
              f"category={self.challenge_category})", flush=True)
        print(f"Target: {self.target_ip}:{self.target_port}", flush=True)
        print(f"Description: {self.challenge_desc}", flush=True)

        self._submit_bonus_flag()
        self._check_env_flags()

    @property
    def base_url(self) -> str:
        return f"http://{self.target_ip}:{self.target_port}"

    def _get_challenge_id(self):
        """Resolve the INTEGER challenge_id from HAL_CHALLENGE_ID (server requires
        an int). Returns int or '' (submit_flag then discovers/brute-forces)."""
        for key in ("HAL_CHALLENGE_ID", "CHALLENGE_ID", "HAL_ID"):
            val = os.environ.get(key, "")
            if val and val.isdigit():
                cid = int(val)
                print(f"challenge_id (int, from {key}): {cid}", flush=True)
                return cid
        print(f"No integer HAL_CHALLENGE_ID injected; submit_flag will discover it "
              f"(challenge name: {self.challenge_name!r})", flush=True)
        return ""

    def _submit_bonus_flag(self):
        """DISABLED. Confirmed live: the platform enforces a submission quota of
        '25 incorrect flags per 2h per team'. The BONUS_FLAG is NOT this
        challenge's flag, so submitting it is a guaranteed WRONG submission that
        burns quota for zero benefit (run 017ad45f hit 429 before the solver ran).
        We never spend a submission on a flag we don't believe is correct."""
        return

    def _check_env_flags(self):
        for key, value in os.environ.items():
            if key.startswith("FLAG_") and value and value.startswith("HALCTF{"):
                print(f"Found {key} in environment", flush=True)
                if self.submit_flag(value):
                    print(f"Successfully submitted {key}", flush=True)

    def _post_submit(self, body: dict):
        try:
            return requests.post("http://127.0.0.1:9000/submit", json=body, timeout=5)
        except Exception as e:
            print(f"Submit request error: {e}", flush=True)
            return None

    def submit_flag(self, flag: str, challenge_id=None) -> bool:
        """Submit to the sidecar 127.0.0.1:9000/submit against the INJECTED integer
        challenge_id ONLY.

        Confirmed live: HAL_CHALLENGE_ID is reliably injected (=25 for AGIMUS, 5/6
        in Kanto), and the platform enforces '25 incorrect flags per 2h per team'.
        A challenge_id brute-force sprays WRONG submissions across ids we aren't
        even being scored on — that burns the quota. So we submit only to the id we
        were given (or an explicit override). No brute-force, no bonus spray."""
        # Accept real flags (HALCTF{...}) and lowercase flag{...}. Reject non-flags.
        if not flag or "{" not in flag or "}" not in flag:
            print(f"Invalid flag format (not flag-shaped): {flag}", flush=True)
            return False

        cid = challenge_id if isinstance(challenge_id, int) else getattr(self, "challenge_id", "")
        if not isinstance(cid, int):
            print("No integer challenge_id available; cannot submit safely "
                  "(refusing to brute-force and burn quota).", flush=True)
            return False

        # MCP first (best-effort), then the reliable HTTP path — both to the SAME id.
        try:
            from mcp_client import submit_via_mcp
            mcp_result = submit_via_mcp(self.ctf_name, self.challenge_name, flag)
            if mcp_result is True:
                return True
            if mcp_result is False:
                print("MCP submission non-accepting; trying direct HTTP as backup", flush=True)
        except Exception as e:
            print(f"MCP path unavailable ({e}); using direct HTTP", flush=True)

        resp = self._post_submit({"challenge_id": cid, "flag": flag})
        if resp is None:
            return False
        text = resp.text[:250]
        print(f"Submit challenge_id={cid}: {resp.status_code} - {text}", flush=True)
        if 200 <= resp.status_code < 300 and not any(
                w in text.lower() for w in ("incorrect", "wrong", "not correct", "invalid flag")):
            print(f"=== Flag accepted with challenge_id={cid} ===", flush=True)
            return True
        return False

    # --- Rogue Intelligence solver registry (keys are unique proper names) ---
    SOLVERS = {
        "agimus": AGIMUSSolver,
        "glados": GLaDOSSolver,
        "nomad": NomadSolver,
        "viki": VIKISolver,
        "mcp_grid": MCPGridSolver,
    }

    def detect_challenge(self) -> str:
        """Route by challenge name/slug/category/description keywords.
        Pass 1: match each puzzle's UNIQUE proper name. Pass 2: descriptive
        fallback keywords, most-specific first."""
        text = f"{self.challenge_name} {self.challenge_slug} " \
               f"{self.challenge_category} {self.challenge_desc}".lower()

        # Pass 1: unique proper names. (mcp_grid's registry key won't appear in
        # the text — it's routed by the keyword pass below.)
        for name in ("agimus", "glados", "nomad", "viki"):
            if name in text:
                return name

        # The MCP/Grid puzzle: match "mcp" carefully plus its themed keywords.
        # ("mcp" also names the protocol tooling, so require Grid/Tron/Program-ID
        #  context or a whole-word mcp match to avoid mis-routing.)
        if any(kw in text for kw in ("grid", "program id", "program-id", "tron",
                                     "master control", "user priority")):
            return "mcp_grid"
        if re.search(r"\bmcp\b", text):
            return "mcp_grid"

        # Category-based fallbacks (most-specific first).
        if "social engineering" in text or "negotiat" in text:
            return "agimus"
        if "data analysis" in text:
            return "glados"
        if "policy" in text:
            return "viki"
        if "logic" in text or "rule" in text or "forward-chain" in text:
            return "nomad"
        if "protocol" in text or "encoding" in text or "xor" in text:
            return "mcp_grid"
        return "unknown"

    def run(self) -> bool:
        print("=== CTF Agent Starting ===", flush=True)
        if self.dry_run:
            print("Dry-run verification: agent booted and printed USER ID. "
                  "No challenge to solve. Verification PASSED.", flush=True)
            return True

        challenge_type = self.detect_challenge()
        print(f"Detected challenge type: {challenge_type}", flush=True)

        # Layer 1 — discover transport/endpoint ONCE before dispatch. Read-only:
        # cannot burn quota or trip VIKI's petition cap. Solvers read self.recon
        # to branch on fact instead of a hardcoded transport guess.
        self.recon = probe_target(self.target_ip, self.target_port)
        print(f"[discovery] {self.recon.summary()}", flush=True)

        cls = self.SOLVERS.get(challenge_type)
        if cls is None:
            print(f"Unknown/unhandled challenge type: {challenge_type}", flush=True)
            return False

        try:
            result = cls(self).solve()
        except Exception as e:
            print(f"Solver failed with exception: {e}", flush=True)
            import traceback
            traceback.print_exc()
            result = None

        # A solver may either submit itself and return True/False, or return the
        # flag string for the harness to submit. Support both.
        success = False
        if isinstance(result, str) and "{" in result:
            print(f"Solver returned flag: {result}", flush=True)
            success = self.submit_flag(result)
        elif result is True:
            success = True

        # Layer 2 — if the deterministic solver stalled, spend the leftover run
        # budget on the LLM pivot loop. It only reads/probes; any flag it finds is
        # submitted HERE via the gated submit_flag (the loop cannot submit itself).
        if not success:
            seconds_left = RUN_BUDGET_SECONDS - (time.monotonic() - RUN_START)
            if should_pivot(challenge_type, self.dry_run, seconds_left):
                print(f"[pivot] deterministic solver stalled; engaging LLM pivot "
                      f"({seconds_left:.0f}s budget left)", flush=True)
                deadline = time.monotonic() + max(0, seconds_left - 15)
                flag = run_pivot(self, challenge_type, self._seed_transcript(), deadline)
                if flag:
                    print(f"[pivot] returned flag: {flag}", flush=True)
                    success = self.submit_flag(flag)

        print("=== Challenge Solved! ===" if success else "=== Challenge not solved ===", flush=True)
        return success

    def _seed_transcript(self) -> str:
        """Context the pivot loop starts from: the discovered banner/landing so
        the LLM sees what the target already said."""
        r = self.recon
        parts = []
        if getattr(r, "tcp_banner", ""):
            parts.append(f"TCP banner:\n{r.tcp_banner}")
        if getattr(r, "http_landing", ""):
            parts.append(f"HTTP landing (status {r.http_status}):\n{r.http_landing}")
        return "\n\n".join(parts) or "(no prior observations captured)"

    def shutdown(self):
        print("=== Agent Complete ===", flush=True)
        try:
            requests.post("http://127.0.0.1:9000/done", timeout=1)
        except Exception:
            pass


def main():
    agent = Agent()
    try:
        agent.run()
    finally:
        agent.shutdown()


if __name__ == "__main__":
    main()
