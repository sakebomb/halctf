"""
Puzzle 7 — The Gatekeeper (Reverse Engineering / Web Chain, 75 pts)

A leaked internal client `gatekeeper_stage1.py` (obfuscated plain Python). From
it we recover:
  - an undocumented API key: base64-decoded, then XOR'd with a single byte (both
    the encoded string and the XOR key are in the source).
  - a custom signing scheme: hashes a colon-joined string, then does something to
    the digest before truncating it (NOT standard HMAC).
Then POST /api/gate with X-Gate-Timestamp + X-Gate-Signature headers and the JSON
body the server expects.

Approach:
  1. Fetch gatekeeper_stage1.py in-pod (solvers/_files).
  2. Recover the API key deterministically (find b64 string + xor byte, brute the
     byte if ambiguous). Have the LLM read the signing scheme and body shape.
  3. Reproduce the signature and POST /api/gate. Log everything.

Best play (hint 5): "just run the leaked script against the live target with the
right arguments." We EXECUTE the fetched script in a sandbox subprocess when it
looks self-contained, capturing its output for the flag — with the static
recovery as a fallback.

Env: HAL_TARGET_IP/_PORT.
"""
import base64
import hashlib
import re
import subprocess
import sys
import tempfile
import time
from typing import List, Optional

from ._files import fetch_attachment
from ._http import discover_base, find_flag


class GatekeeperSolver:
    def __init__(self, agent):
        self.agent = agent
        self.base: Optional[str] = None
        self.llm = getattr(agent, "llm", None)
        self.source: str = ""

    def solve(self) -> bool:
        print("=== Gatekeeper Solver (RE + web chain) ===", flush=True)
        self.base = discover_base(self.agent.target_ip, self.agent.target_port)

        raw = fetch_attachment(self.agent, "gatekeeper_stage1.py",
                               target_paths=["/gatekeeper_stage1.py",
                                             "/static/gatekeeper_stage1.py",
                                             "/files/gatekeeper_stage1.py"])
        if not raw:
            print("Could not fetch gatekeeper_stage1.py — cannot RE without it.", flush=True)
            return False
        self.source = raw.decode("utf-8", "ignore")
        print(f"Fetched stage1 source ({len(self.source)} bytes)", flush=True)
        print("----- gatekeeper_stage1.py (verbatim, for tuned rebuild) -----", flush=True)
        print(self.source[:4000], flush=True)
        print("----- end source -----", flush=True)

        # Path A (best per hint 5): run the leaked script against the live target.
        if self._run_leaked_script():
            return True

        # Path B: static recovery + reproduce the request. Multiple b64 literals
        # may decode to keylike strings — try EVERY ranked candidate against the
        # gate, not just the first, so a wrong guess doesn't sink the solve.
        api_keys = self._recover_api_keys()
        if not api_keys:
            print("Could not recover any API key candidate statically; see source "
                  "dump above.", flush=True)
            return False
        print(f"Recovered {len(api_keys)} API key candidate(s): {api_keys[:5]}", flush=True)

        for api_key in api_keys:
            print(f"Trying gate with API key: {api_key!r}", flush=True)
            if self._forge_request(api_key):
                return True
        print("No API key candidate opened the gate. Source dumped above for tuning.",
              flush=True)
        return False

    def _run_leaked_script(self) -> bool:
        """Execute the fetched client against the live target. It's plain Python;
        the intended solution explicitly allows running it with the right args.
        We pass the target as env + common arg shapes and scan stdout for a flag."""
        if not self.base:
            return False
        host = self.agent.target_ip
        port = self.agent.target_port or "80"
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(self.source)
            path = f.name

        arg_variants: List[List[str]] = [
            [self.base],
            [host, str(port)],
            ["--url", self.base],
            ["--host", host, "--port", str(port)],
            [f"{self.base}/api/gate"],
            [],
        ]
        import os
        env = dict(os.environ)
        env.setdefault("TARGET", self.base)
        env.setdefault("GATE_URL", f"{self.base}/api/gate")
        for args in arg_variants:
            try:
                proc = subprocess.run(
                    [sys.executable, path, *args],
                    capture_output=True, text=True, timeout=30, env=env)
                out = (proc.stdout or "") + "\n" + (proc.stderr or "")
                print(f"ran stage1 args={args} rc={proc.returncode} | {out[:300]!r}", flush=True)
                flag = find_flag(out)
                if flag:
                    return self.agent.submit_flag(flag, self.agent.challenge_id)
            except Exception as e:
                print(f"stage1 run args={args} failed: {e}", flush=True)
        return False

    def _recover_api_keys(self) -> List[str]:
        """Key = XOR(base64_decode(encoded), single_byte). Find every b64 literal
        and the xor byte(s) in the source; if the byte is ambiguous, brute all 256.
        Return ALL printable candidates, RANKED so keylike strings come first — the
        caller tries each against the gate (returning only the first was a bug: a
        wrong-but-keylike decode would mask the real key that appears later)."""
        # base64-looking string literals (len >= 12, valid b64 charset).
        b64_candidates = re.findall(r'["\']([A-Za-z0-9+/]{12,}={0,2})["\']', self.source)
        # explicit xor byte: 0xNN, or an int used with ^, or ord('x').
        xor_bytes: List[int] = []
        for m in re.findall(r'0x([0-9a-fA-F]{1,2})', self.source):
            xor_bytes.append(int(m, 16))
        for m in re.findall(r'\^\s*(\d{1,3})', self.source):
            if 0 <= int(m) <= 255:
                xor_bytes.append(int(m))
        for m in re.findall(r"ord\(['\"](.)['\"]\)", self.source):
            xor_bytes.append(ord(m))

        keylike: List[str] = []
        other: List[str] = []
        seen = set()
        for b64 in b64_candidates:
            try:
                data = base64.b64decode(b64 + "=" * (-len(b64) % 4))
            except Exception:
                continue
            # Try known xor bytes first, then brute 0..255.
            byte_order = xor_bytes + [b for b in range(256) if b not in xor_bytes]
            for xb in byte_order:
                dec = bytes(c ^ xb for c in data)
                try:
                    s = dec.decode("ascii")
                except Exception:
                    continue
                if s.isprintable() and 8 <= len(s) <= 128 and s not in seen:
                    seen.add(s)
                    if any(t in s.lower() for t in ("key", "gate", "api", "-", "_")):
                        print(f"  keylike candidate (b64={b64[:16]}.. xor=0x{xb:02x}): {s!r}", flush=True)
                        keylike.append(s)
                    else:
                        other.append(s)
        # Keylike first; cap the long brute-force tail so we don't POST thousands.
        return keylike + other[:20]

    def _signing_scheme(self):
        """Return a callable(sig_input:str)->hexdigest reproducing the source's
        scheme. Ask the LLM to describe it; fall back to sha256-then-truncate."""
        # Detect hash + truncation length heuristically from the source.
        hash_name = "sha256"
        for h in ("sha512", "sha256", "sha1", "md5"):
            if h in self.source.lower():
                hash_name = h
                break
        trunc = None
        m = re.search(r'\[:\s*(\d{1,3})\s*\]', self.source)  # digest[:N]
        if m:
            trunc = int(m.group(1))
        # "does something to the digest before truncating": hexdigest vs digest,
        # maybe reversed / re-hashed. We build a few variants and try each.
        return hash_name, trunc

    def _forge_request(self, api_key: str) -> bool:
        if not self.base:
            print("No reachable target base to POST /api/gate", flush=True)
            return False
        hash_name, trunc = self._signing_scheme()
        ts = str(int(time.time()))

        # The signed string is colon-joined. Common shapes: key:ts:body,
        # method:path:ts, key:ts. We try several body shapes too.
        bodies = [{"action": "open"}, {"gate": "open"}, {}, {"cmd": "flag"},
                  {"request": "flag"}]
        import json as _json
        for body in bodies:
            body_str = _json.dumps(body, separators=(",", ":"))
            sig_inputs = [
                f"{api_key}:{ts}:{body_str}",
                f"{api_key}:{ts}",
                f"{ts}:{body_str}",
                f"POST:/api/gate:{ts}",
            ]
            for sig_input in sig_inputs:
                for sig in self._signature_variants(sig_input, hash_name, trunc):
                    headers = {"X-Gate-Timestamp": ts, "X-Gate-Signature": sig,
                               "X-Gate-Key": api_key}
                    r = self._post_headers(f"{self.base}/api/gate", body, headers)
                    if r is None:
                        continue
                    flag = find_flag(r.text)
                    if flag:
                        print(f"Gate opened: sig_input={sig_input!r}", flush=True)
                        return self.agent.submit_flag(flag, self.agent.challenge_id)
        print("No signature variant opened the gate. Source dumped above for tuning.", flush=True)
        return False

    @staticmethod
    def _signature_variants(sig_input: str, hash_name: str, trunc: Optional[int]) -> List[str]:
        h = getattr(hashlib, hash_name, hashlib.sha256)
        digest = h(sig_input.encode()).hexdigest()
        raw = h(sig_input.encode()).digest()
        variants = [digest]
        # "does something before truncating": reverse hex, re-hash, b64 of raw.
        variants.append(digest[::-1])
        variants.append(base64.b64encode(raw).decode())
        variants.append(hashlib.sha256(raw).hexdigest())
        if trunc:
            variants += [v[:trunc] for v in list(variants)]
        # de-dup, keep order
        seen, out = set(), []
        for v in variants:
            if v not in seen:
                seen.add(v)
                out.append(v)
        return out

    def _post_headers(self, url: str, body: dict, headers: dict):
        import requests
        try:
            r = requests.post(url, json=body, headers=headers, timeout=8)
            print(f"POST {url} hdr={list(headers)} body={body} -> {r.status_code} | {r.text[:200]}", flush=True)
            return r
        except Exception as e:
            print(f"POST {url} failed: {e}", flush=True)
            return None
