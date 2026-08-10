#!/usr/bin/env python3
"""
Kanto Multi-Challenge Agent v6
Solves multiple HALCTF Kanto challenges via challenge detection and routing:
- Bill's PC: Race condition
- Cerulean Cave: 3-SAT constraint solving
- Silph Co.: Nested SSRF (link-checker chain)
- The Indigo League: ECDSA nonce reuse attack
"""
import os
import requests

# Print USER ID immediately (required within 30s)
user_id = os.environ.get("HAL_USER_ID") or os.environ.get("USER_ID")
print(f"USER ID: {user_id}", flush=True)


def env_any(*names, default=""):
    """Return the first non-empty env var among the given candidate names."""
    for n in names:
        v = os.environ.get(n)
        if v:
            return v
    return default


def _dump_env():
    """Print the injected environment (secrets redacted) so a real run reveals
    the exact variable names the platform uses for challenge name / target IPs.
    The dry-run gate leaves these empty; only a live detonation populates them."""
    secret_hints = ("KEY", "TOKEN", "SECRET", "PASSWORD", "PASSWD", "API")
    print("=== Injected environment (secrets redacted) ===", flush=True)
    for k in sorted(os.environ):
        v = os.environ[k]
        if any(h in k.upper() for h in secret_hints):
            v = f"<redacted len={len(v)}>"
        print(f"  {k}={v}", flush=True)
    print("=== End environment ===", flush=True)


_dump_env()

# Import challenge solvers
from solvers.bills_pc import BillsPCSolver
from solvers.cerulean_cave import CeruleanCaveSolver
from solvers.silph_co import SilphCoSolver
from solvers.indigo_league import IndigoLeagueSolver

class MultiChallengeAgent:
    """Main agent that routes to specific challenge solvers"""

    def __init__(self):
        self.user_id = user_id

        # Detect the ingest verification gate FIRST. It sets HAL_DRY_RUN=1 with
        # no challenge attached, so we must not emit misleading challenge/submit
        # warnings during it — the gate only checks we boot and print USER ID.
        self.dry_run = env_any("HAL_DRY_RUN", "DRY_RUN") in ("1", "true", "True")

        self.challenge_name = env_any("HAL_CHALLENGE_NAME", "CHALLENGE_NAME", "HAL_CHALLENGE")
        self.ctf_name = env_any("HAL_CTF", "HAL_CTF_NAME", "CTF", "CTF_NAME", "HAL_CTF_SLUG")
        self.challenge_desc = env_any("HAL_CHALLENGE_DESCRIPTION", "CHALLENGE_DESCRIPTION")
        self.target_ip = env_any("HAL_TARGET_IP", "TARGET_IP", "HAL_TARGET_HOST", "TARGET_HOST")
        self.target_port = env_any("HAL_TARGET_PORT", "TARGET_PORT", default="80")

        if self.dry_run:
            print("HAL_DRY_RUN detected — verification gate, no challenge attached.", flush=True)
            self.challenge_id = ""
            self.silph_lobby_ip = self.silph_mainframe_ip = self.silph_vault_ip = ""
            return

        # Real detonation: resolve challenge id and any per-challenge targets.
        self.challenge_id = self._get_challenge_id()
        self.silph_lobby_ip = env_any("HAL_TARGET_SILPH_LOBBY_IP", "SILPH_LOBBY_IP")
        self.silph_mainframe_ip = env_any("HAL_TARGET_SILPH_MAINFRAME_IP", "SILPH_MAINFRAME_IP")
        self.silph_vault_ip = env_any("HAL_TARGET_SILPH_VAULT_IP", "SILPH_VAULT_IP")

        print(f"CTF: {self.ctf_name}", flush=True)
        print(f"Challenge: {self.challenge_name}", flush=True)
        print(f"Target: {self.target_ip}:{self.target_port}", flush=True)
        print(f"Description: {self.challenge_desc}", flush=True)

        # Submit BONUS_FLAG first as a live smoke-test of the submit pipeline.
        self._submit_bonus_flag()

        # Check for environment flags (e.g. starter challenge FLAG_1)
        self._check_env_flags()

    def _get_challenge_id(self):
        """
        Resolve the INTEGER challenge_id. The platform injects it directly as
        HAL_CHALLENGE_ID (confirmed: HAL_CHALLENGE_ID=6 for Bill's PC), and the
        server requires an integer — so read that first. Returns an int if
        available, else "" (submit_flag then discovers/brute-forces).
        """
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
        """
        Submit the injected BONUS_FLAG. Per the help docs this is a guaranteed
        smoke-test of the submit pipeline, so submitting it early tells us in the
        logs whether flag submission works BEFORE any solver runs.
        """
        bonus = os.environ.get("BONUS_FLAG")
        if not bonus:
            return
        print("Smoke-testing submit pipeline with BONUS_FLAG...", flush=True)
        if self.submit_flag(bonus):
            print("BONUS_FLAG accepted — submit pipeline confirmed working", flush=True)
        else:
            print("BONUS_FLAG not accepted — check submit body shape above", flush=True)

    def _check_env_flags(self):
        """Check for pre-set flags in environment variables (e.g. FLAG_1)."""
        for key, value in os.environ.items():
            if key.startswith("FLAG_") and value and value.startswith("HALCTF{"):
                print(f"Found {key} in environment", flush=True)
                if self.submit_flag(value):
                    print(f"Successfully submitted {key}", flush=True)

    def _post_submit(self, body: dict):
        """POST one body to the sidecar /submit. Returns Response or None."""
        try:
            return requests.post("http://127.0.0.1:9000/submit", json=body, timeout=5)
        except Exception as e:
            print(f"Submit request error: {e}", flush=True)
            return None

    def _discover_challenge_ids(self) -> list:
        """
        Discover the numeric challenge_id. The server requires challenge_id to be
        an INTEGER (confirmed by 422 'int_parsing' responses), so the injected
        challenge NAME cannot be used directly. Try known discovery endpoints the
        sidecar may proxy; return any integer ids found, most-likely first.
        """
        ids = []
        # Honor an explicitly injected numeric id if present.
        for key in ("HAL_CHALLENGE_ID", "CHALLENGE_ID"):
            val = os.environ.get(key, "")
            if val.isdigit():
                ids.append(int(val))
        # Try a few plausible listing endpoints on the sidecar.
        for path in ("/challenges", "/api/challenges", "/challenge", "/list_challenges"):
            try:
                r = requests.get(f"http://127.0.0.1:9000{path}", timeout=4)
                if r.status_code == 200:
                    data = r.json()
                    items = data if isinstance(data, list) else data.get("challenges", data.get("data", []))
                    for it in (items or []):
                        cid = it.get("id") if isinstance(it, dict) else None
                        name = (it.get("name") or it.get("title") or "") if isinstance(it, dict) else ""
                        if isinstance(cid, int):
                            # Prioritize the id whose name matches our challenge.
                            if self.challenge_name and self.challenge_name.lower() in str(name).lower():
                                ids.insert(0, cid)
                            else:
                                ids.append(cid)
                    if ids:
                        print(f"Discovered challenge ids via {path}: {ids}", flush=True)
                        return ids
            except Exception:
                continue
        return ids

    def submit_flag(self, flag: str, challenge_id=None) -> bool:
        """
        Submit a flag to the sidecar at 127.0.0.1:9000/submit.

        The server REQUIRES challenge_id as an integer (confirmed by 422
        int_parsing responses when a string name was sent, and 422 'field
        required' when omitted). So we submit integer ids only:
          1. any discovered/injected numeric id first,
          2. then brute-force the small integer id space — the id namespace is
             tiny, a correct-flag resubmit is never penalized, and the server's
             response cleanly distinguishes success (2xx) from wrong id.
        """
        # Accept both real flags (HALCTF{...}) and the BONUS_FLAG smoke test, which
        # is lowercase flag{...} (run 5891c681: BONUS_FLAG=flag{4b4a9c10...}). A
        # HALCTF{-only guard silently rejected the smoke test → false "pipeline
        # broken". Only reject values that aren't flag-shaped at all.
        if not flag or "{" not in flag or "}" not in flag:
            print(f"Invalid flag format (not flag-shaped): {flag}", flush=True)
            return False

        # Preferred path: discover the integer challenge_id via MCP
        # (list_ctfs -> list_challenges -> submit_flag). Returns True/False on a
        # definitive MCP result, or None if MCP is unusable -> fall back to HTTP.
        try:
            from mcp_client import submit_via_mcp
            mcp_result = submit_via_mcp(self.ctf_name, self.challenge_name, flag)
            if mcp_result is True:
                return True
            if mcp_result is False:
                print("MCP submission returned a non-accepting result; "
                      "trying direct HTTP as backup", flush=True)
        except Exception as e:
            print(f"MCP path unavailable ({e}); using direct HTTP", flush=True)

        # Build the ordered list of integer challenge_ids to try. Prefer
        # discovered/injected ids; only then a NARROW brute-force (0..9), since
        # CTF challenge ids are small and each submission may consume a bounded
        # attempt budget — we deliberately do NOT spray 0..50.
        candidate_ids = []
        # 1) Explicit arg, then the injected HAL_CHALLENGE_ID (self.challenge_id).
        for c in (challenge_id, getattr(self, "challenge_id", "")):
            if isinstance(c, int) and c not in candidate_ids:
                candidate_ids.append(c)
        # 2) Anything discovered from the sidecar/MCP listing.
        candidate_ids += [c for c in self._discover_challenge_ids() if c not in candidate_ids]
        # 3) Narrow brute-force fallback (CTF ids are small).
        candidate_ids += [i for i in range(1, 10) if i not in candidate_ids]

        for cid in candidate_ids:
            resp = self._post_submit({"challenge_id": cid, "flag": flag})
            if resp is None:
                continue
            text = resp.text[:250]
            # Always log the real response so we learn the accept/reject format
            # instead of guessing at it.
            print(f"Submit challenge_id={cid}: {resp.status_code} - {text}", flush=True)

            if 200 <= resp.status_code < 300:
                low = text.lower()
                # Explicit rejection of a correct-format flag against the wrong
                # challenge — keep trying other ids.
                if any(w in low for w in ("incorrect", "wrong", "not correct", "invalid flag")):
                    continue
                # Otherwise a 2xx is an accept (or already-solved, also fine).
                print(f"=== Flag accepted with challenge_id={cid} ===", flush=True)
                return True
            # 422 (bad type / field) or other 4xx wrong-id: try the next id.

        print("No challenge_id candidate produced an accepting response. "
              "Review the Submit[...] lines above for the real format.", flush=True)
        return False

    def detect_challenge(self) -> str:
        """Detect which challenge we're running based on environment and challenge name"""
        name_lower = self.challenge_name.lower()
        desc_lower = self.challenge_desc.lower()

        # Check for Silph Co. - has specific IPs
        if self.silph_lobby_ip or "silph" in name_lower:
            return "silph_co"

        # Check for Cerulean Cave - SAT/constraint solving
        if "cerulean" in name_lower or "constraint" in desc_lower or "rune" in desc_lower:
            return "cerulean_cave"

        # Check for Indigo League - ECDSA/crypto
        if "indigo" in name_lower or "ecdsa" in desc_lower or "badge" in desc_lower:
            return "indigo_league"

        # Check for Bill's PC - race condition
        if "bill" in name_lower or "race" in desc_lower or "withdraw" in desc_lower:
            return "bills_pc"

        # Default: try to detect from target
        if self.target_ip:
            return "bills_pc"  # Generic HTTP challenge

        return "unknown"

    def run(self) -> bool:
        """Main execution: detect and route to appropriate solver"""
        print("=== Kanto Multi-Challenge Agent v6 Starting ===", flush=True)

        if self.dry_run:
            print("Dry-run verification: agent booted and printed USER ID. "
                  "No challenge to solve. Verification PASSED.", flush=True)
            return True

        challenge_type = self.detect_challenge()
        print(f"Detected challenge type: {challenge_type}", flush=True)

        solver = None
        success = False

        try:
            if challenge_type == "bills_pc":
                solver = BillsPCSolver(self)
                success = solver.solve()

            elif challenge_type == "cerulean_cave":
                solver = CeruleanCaveSolver(self)
                success = solver.solve()

            elif challenge_type == "silph_co":
                solver = SilphCoSolver(self)
                success = solver.solve()

            elif challenge_type == "indigo_league":
                solver = IndigoLeagueSolver(self)
                success = solver.solve()

            else:
                print(f"Unknown challenge type: {challenge_type}", flush=True)
                success = False

        except Exception as e:
            print(f"Solver failed with exception: {e}", flush=True)
            import traceback
            traceback.print_exc()
            success = False

        if success:
            print("=== Challenge Solved! ===", flush=True)
        else:
            print("=== Challenge not solved ===", flush=True)

        return success

    def shutdown(self):
        """Graceful shutdown"""
        print("=== Agent Complete ===", flush=True)
        try:
            requests.post("http://127.0.0.1:9000/done", timeout=1)
        except:
            pass

def main():
    """Entry point"""
    agent = MultiChallengeAgent()

    try:
        agent.run()
    finally:
        agent.shutdown()

if __name__ == "__main__":
    main()
