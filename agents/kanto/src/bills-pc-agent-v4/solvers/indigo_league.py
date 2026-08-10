"""
Indigo League Solver
Exploits ECDSA nonce reuse to recover private key and forge signature
"""
import requests
import hashlib
from typing import Optional, List, Dict, Tuple


class IndigoLeagueSolver:
    """Solves the Indigo League ECDSA challenge"""

    def __init__(self, agent):
        self.agent = agent
        self.base_url = f"http://{agent.target_ip}:{agent.target_port}"

    def get_badges(self) -> Optional[List[Dict]]:
        """GET /api/badges - retrieve signed badges"""
        try:
            resp = requests.get(f"{self.base_url}/api/badges", timeout=10)
            print(f"GET /api/badges: {resp.status_code}", flush=True)

            if resp.status_code == 200:
                # Raw dump — the badge message field name is undocumented (champion's
                # was 'trial_message', not any fixed guess), and a wrong message means
                # a wrong hash z, which makes recovered d fail to match the pubkey.
                print(f"RAW /api/badges body: {resp.text[:1200]}", flush=True)
                data = resp.json()
                badges = data.get("badges", data if isinstance(data, list) else [])
                print(f"Retrieved {len(badges)} badges", flush=True)
                return badges
            else:
                print(f"Failed to get badges: {resp.text}", flush=True)
                return None

        except Exception as e:
            print(f"Error getting badges: {e}", flush=True)
            return None

    def get_pubkey(self) -> Optional[Dict]:
        """GET /api/pubkey - retrieve Authority's public key"""
        try:
            resp = requests.get(f"{self.base_url}/api/pubkey", timeout=10)
            print(f"GET /api/pubkey: {resp.status_code}", flush=True)

            if resp.status_code == 200:
                pubkey = resp.json()
                print(f"Retrieved public key", flush=True)
                return pubkey
            else:
                print(f"Failed to get pubkey: {resp.text}", flush=True)
                return None

        except Exception as e:
            print(f"Error getting pubkey: {e}", flush=True)
            return None

    def get_params(self) -> Optional[Dict]:
        """GET /api/params - retrieve curve and hashing parameters"""
        try:
            resp = requests.get(f"{self.base_url}/api/params", timeout=10)
            print(f"GET /api/params: {resp.status_code}", flush=True)

            if resp.status_code == 200:
                params = resp.json()
                print(f"Retrieved params: {params}", flush=True)
                return params
            else:
                print(f"Failed to get params: {resp.text}", flush=True)
                return None

        except Exception as e:
            print(f"Error getting params: {e}", flush=True)
            return None

    def get_champion_message(self) -> Optional[str]:
        """
        GET /api/champion - retrieve the message to sign.

        The exact JSON field name for the message is NOT documented, and a fixed
        guess (message/msg/text/challenge) previously extracted an EMPTY string
        from a 200 response (run 5891c681), killing the solve before any crypto.
        So: (1) ALWAYS dump the raw body on 200 so a miss is self-diagnosing, and
        (2) find the message robustly — known keys first, then keyword-named
        string fields, then the longest string value anywhere in the response.
        """
        try:
            resp = requests.get(f"{self.base_url}/api/champion", timeout=10)
            print(f"GET /api/champion: {resp.status_code}", flush=True)
            if resp.status_code != 200:
                print(f"Failed to get champion message: {resp.text}", flush=True)
                return None

            # Raw dump — never hide what the server actually returned.
            print(f"RAW /api/champion body: {resp.text[:800]}", flush=True)

            try:
                data = resp.json()
            except Exception:
                # Non-JSON: the body itself may be the message to sign.
                body = resp.text.strip()
                print(f"Champion message (raw text): {body!r}", flush=True)
                return body or None

            message = self._extract_message(data)
            if message:
                print(f"Champion message: {message!r}", flush=True)
            else:
                print("Champion message: <none found> — inspect RAW body above; "
                      "may be at a different endpoint or key.", flush=True)
            return message or None

        except Exception as e:
            print(f"Error getting champion message: {e}", flush=True)
            return None

    @staticmethod
    def _extract_message(data) -> str:
        """
        Pull the message-to-sign out of the champion response in whatever shape it
        uses. Order: known keys -> keyword-named string fields -> longest string.
        """
        if isinstance(data, str):
            return data.strip()
        if not isinstance(data, dict):
            return ""

        # 1) Documented / common key names.
        for k in ("message", "msg", "text", "challenge", "trial", "prompt",
                  "champion", "champion_message", "challenge_message",
                  "statement", "data", "payload"):
            v = data.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()

        # 2) Any string-valued key whose NAME hints it's the message.
        kw = ("message", "msg", "text", "challenge", "trial", "champion",
              "sign", "statement", "prompt")
        for key, v in data.items():
            if isinstance(v, str) and v.strip() and any(w in str(key).lower() for w in kw):
                return v.strip()

        # 3) Last resort: the longest string value anywhere (the message is
        #    typically the longest human-readable field). Logged so it's obvious.
        strings = [v.strip() for v in data.values() if isinstance(v, str) and v.strip()]
        if strings:
            best = max(strings, key=len)
            print(f"  (guessed champion message as longest string field: {best!r})", flush=True)
            return best
        return ""

    @staticmethod
    def _extract_badge_message(badge: Dict) -> str:
        """
        Pull the SIGNED message out of a badge. Unlike the champion helper, a badge
        also contains r/s (long numeric/hex strings), so 'longest string' would grab
        the signature. So: exclude signature/name/id fields, reject purely
        numeric/hex values, then prefer keyword-named fields, else longest remaining
        human-readable string.
        """
        if isinstance(badge, str):
            return badge.strip()
        if not isinstance(badge, dict):
            return ""

        # 1) Known message key names first.
        for k in ("message", "msg", "text", "trial_message", "badge_message",
                  "challenge", "trial", "statement", "data", "payload", "citation"):
            v = badge.get(k)
            if isinstance(v, str) and v.strip() and not IndigoLeagueSolver._looks_numeric(v):
                return v.strip()

        # Fields that are NOT the message (signature components, identifiers).
        exclude = {"r", "s", "signature", "sig", "name", "badge", "id", "pubkey",
                   "public_key", "x", "y", "z", "hash"}

        def candidate_items():
            for key, v in badge.items():
                if str(key).lower() in exclude:
                    continue
                if isinstance(v, str) and v.strip() and not IndigoLeagueSolver._looks_numeric(v):
                    yield key, v.strip()

        # 2) Keyword-named field among the non-excluded, non-numeric strings.
        kw = ("message", "msg", "text", "trial", "challenge", "sign", "statement", "cite")
        for key, v in candidate_items():
            if any(w in str(key).lower() for w in kw):
                return v

        # 3) Longest remaining human-readable string.
        remaining = [v for _, v in candidate_items()]
        if remaining:
            best = max(remaining, key=len)
            print(f"  (guessed badge message as longest non-numeric field: {best!r})", flush=True)
            return best
        return ""

    @staticmethod
    def _looks_numeric(v: str) -> bool:
        """True if v is a bare integer or hex string (i.e. a signature component,
        not a human-readable message)."""
        s = v.strip()
        if not s:
            return False
        low = s.lower()
        if low.startswith("0x"):
            low = low[2:]
        return len(low) >= 8 and all(ch in "0123456789abcdef" for ch in low)

    @staticmethod
    def _sig_field(badge: Dict, *names):
        """Pull r/s out of a badge whether nested under 'signature' or flat."""
        sig = badge.get("signature", badge)
        for n in names:
            if n in sig:
                return sig[n]
            if n in badge:
                return badge[n]
        return None

    @staticmethod
    def _parse_int(val) -> int:
        """Parse r/s/key values that may be decimal, hex ('0x..'), or int."""
        if isinstance(val, int):
            return val
        s = str(val).strip()
        if s.lower().startswith("0x"):
            return int(s, 16)
        # Bare hex (all hex digits, has a-f) vs decimal.
        try:
            return int(s)
        except ValueError:
            return int(s, 16)

    def find_nonce_reuse(self, badges: List[Dict]) -> Optional[Tuple[Dict, Dict]]:
        """Find the two signatures that share an r (same nonce k)."""
        print(f"Analyzing {len(badges)} badges for nonce reuse...", flush=True)

        # Hint 4: the Thunder badge uses a DIFFERENT nonce — never pair it.
        filtered = [b for b in badges if "thunder" not in str(b.get("name", b.get("badge", ""))).lower()]
        if len(filtered) != len(badges):
            print(f"Excluded Thunder badge; {len(filtered)} badges remain", flush=True)
        badges = filtered

        r_values = {}
        for badge in badges:
            r = self._sig_field(badge, "r")
            if r is not None:
                r_key = str(self._parse_int(r))  # normalize hex/dec so they group
                r_values.setdefault(r_key, []).append(badge)

        for r_key, badge_list in r_values.items():
            if len(badge_list) >= 2:
                names = [b.get("name", b.get("badge", "?")) for b in badge_list]
                print(f"Found nonce reuse! shared r among badges {names}", flush=True)
                return badge_list[0], badge_list[1]

        print("No nonce reuse detected", flush=True)
        return None

    # --- secp256k1 / P-256 curve parameters for manual EC math ---
    CURVES = {
        "secp256k1": {
            "p": 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F,
            "a": 0,
            "b": 7,
            "n": 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141,
            "Gx": 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
            "Gy": 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8,
        },
        "secp256r1": {
            "p": 0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFF,
            "a": 0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFC,
            "b": 0x5AC635D8AA3A93E7B3EBBD55769886BC651D06B0CC53B0F63BCE3C3E27D2604B,
            "n": 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551,
            "Gx": 0x6B17D1F2E12C4247F8BCE6E563A440F277037D812DEB33A0F4A13945D898C296,
            "Gy": 0x4FE342E2FE1A7F9B8EE7EB4A7C0F9E162BCE33576B315ECECBB6406837BF51F5,
        },
    }

    def _curve(self, params: Dict) -> dict:
        name = str(params.get("curve", "secp256k1")).lower().replace("_", "-")
        # secp256k1 (Bitcoin) vs secp256r1 / P-256 / prime256v1. NOTE: naive
        # `"p256" in name` FALSELY matches "se[cp256]k1", picking the wrong curve
        # (wrong n/a → recovery silently fails). Detect k1 first; only then r1.
        if "256k1" in name or "secp256k" in name:
            c = dict(self.CURVES["secp256k1"]); c["name"] = "secp256k1"; return c
        if "256r1" in name or "p-256" in name or "prime256" in name or "nistp256" in name:
            c = dict(self.CURVES["secp256r1"]); c["name"] = "secp256r1"; return c
        # Default to secp256k1 (this challenge's curve).
        c = dict(self.CURVES["secp256k1"]); c["name"] = "secp256k1"; return c

    @staticmethod
    def _inv(a, m):
        return pow(a, -1, m)

    def _pt_add(self, P, Q, p, a):
        if P is None: return Q
        if Q is None: return P
        (x1, y1), (x2, y2) = P, Q
        if x1 == x2 and (y1 + y2) % p == 0:
            return None
        if P == Q:
            m = (3 * x1 * x1 + a) * self._inv(2 * y1, p) % p
        else:
            m = (y2 - y1) * self._inv((x2 - x1) % p, p) % p
        x3 = (m * m - x1 - x2) % p
        y3 = (m * (x1 - x3) - y1) % p
        return (x3, y3)

    def _pt_mul(self, k, P, p, a):
        R = None
        while k:
            if k & 1:
                R = self._pt_add(R, P, p, a)
            P = self._pt_add(P, P, p, a)
            k >>= 1
        return R

    def _hash_z(self, message: str, n: int, params: Dict) -> int:
        """z = SHA-256(message) as int, truncated/reduced per ECDSA convention
        (the documented convention: z = int(sha256(message_ascii)) mod n)."""
        digest = hashlib.sha256(message.encode()).digest()
        z = int.from_bytes(digest, "big")
        # Truncate to bit length of n if the hash is longer (standard ECDSA).
        excess = z.bit_length() - n.bit_length()
        if excess > 0:
            z >>= excess
        return z % n

    def _z_variants(self, message: str, n: int) -> List[int]:
        """
        Ordered plausible z values for a message, so recovery can use the pubkey as
        an oracle across small interpretation ambiguities. The documented convention
        (SHA-256(ascii) mod n) is FIRST and almost always correct; the rest are cheap
        fallbacks for edge cases (no truncation; a trailing/embedded hex token that
        might itself be the signed value, hex-decoded or taken as an int).
        """
        variants: List[int] = []

        def add(z):
            z %= n
            if z not in variants:
                variants.append(z)

        # 1) Documented: SHA-256(ascii) mod n (with standard truncation).
        add(self._hash_z(message, n, {}))
        # 2) SHA-256 without truncation (only differs if bitlen(hash) > bitlen(n)).
        add(int.from_bytes(hashlib.sha256(message.encode()).digest(), "big"))

        # 3) If the message embeds a long hex token (e.g. champion trial ...: 0166f0),
        #    try that token as the signed material.
        import re
        for tok in re.findall(r"[0-9a-fA-F]{16,}", message or ""):
            try:
                raw = bytes.fromhex(tok)
                add(int.from_bytes(hashlib.sha256(raw).digest(), "big"))  # hash of decoded bytes
                add(int(tok, 16))                                          # token as raw int
            except ValueError:
                continue
        return variants or [0]

    def recover_private_key(self, badge1: Dict, badge2: Dict, params: Dict, pub: Dict = None) -> Optional[int]:
        """
        Recover d from two signatures sharing nonce k (Hint 3):
          k = (z1 - z2) / (s1 - s2) mod n
          d = (s1*k - z1) / r mod n
        Tries both sign conventions for k and verifies d against the pubkey.
        """
        try:
            c = self._curve(params)
            n, p, a = c["n"], c["p"], c["a"]

            r = self._parse_int(self._sig_field(badge1, "r"))
            s1 = self._parse_int(self._sig_field(badge1, "s"))
            s2 = self._parse_int(self._sig_field(badge2, "s"))
            # Extract the SIGNED message robustly — same lesson as champion, whose
            # field was 'trial_message'. A wrong message => wrong z => recovered d
            # can't match the pubkey (the failure we saw in run edf2935d).
            msg1 = self._extract_badge_message(badge1)
            msg2 = self._extract_badge_message(badge2)
            print(f"Badge1 signed message: {msg1!r}", flush=True)
            print(f"Badge2 signed message: {msg2!r}", flush=True)

            # Both badges were signed with the SAME hash convention, so pair z1/z2
            # by the same variant index. The pubkey is a convention-independent
            # oracle: whichever convention yields a d that regenerates the pubkey is
            # the server's real one — and signing MUST reuse it (stored below).
            z1_variants = self._z_variants(msg1, n)
            z2_variants = self._z_variants(msg2, n)
            target = self._pubkey_point(pub, c) if pub else None
            G = (c["Gx"], c["Gy"])

            best_effort = None
            for vi in range(min(len(z1_variants), len(z2_variants))):
                z1, z2 = z1_variants[vi], z2_variants[vi]
                # k sign can differ between the two derivations; try both, both d formulas.
                for ds in (s1 - s2, s2 - s1):
                    for dz in (z1 - z2, z2 - z1):
                        try:
                            k = (dz * self._inv(ds % n, n)) % n
                            for (s_use, z_use) in ((s1, z1), (s2, z2)):
                                d = ((s_use * k - z_use) * self._inv(r, n)) % n
                                if not (1 <= d < n):
                                    continue
                                if target is None:
                                    self._z_conv_index = vi
                                    print(f"Recovered d (unverified, z-conv {vi}): {hex(d)[:18]}...", flush=True)
                                    return d
                                if self._pt_mul(d, G, p, a) == target:
                                    self._z_conv_index = vi
                                    print(f"Recovered d VERIFIED against pubkey "
                                          f"(z-conv {vi}): {hex(d)[:18]}...", flush=True)
                                    return d
                                best_effort = best_effort or d
                        except Exception:
                            continue

            if best_effort is not None:
                print("No d candidate matched the pubkey across any z-convention — "
                      "badge message/hash interpretation is still off. See RAW "
                      "/api/badges dump above. NOT returning a bad key.", flush=True)
                # Returning None: signing with an unverified d only wastes a 403.
                return None
            return None

        except Exception as e:
            print(f"Error recovering private key: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return None

    def _pubkey_point(self, pub: Dict, c: dict):
        """Extract (x,y) from the pubkey response in whatever shape it uses."""
        if not isinstance(pub, dict):
            return None
        # common shapes: {"x":..,"y":..}, {"Qx":..,"Qy":..}, nested under "pubkey"
        d = pub.get("pubkey", pub) if isinstance(pub.get("pubkey", None), dict) else pub
        for xk, yk in (("x", "y"), ("Qx", "Qy"), ("X", "Y")):
            if xk in d and yk in d:
                try:
                    return (self._parse_int(d[xk]), self._parse_int(d[yk]))
                except Exception:
                    return None
        return None

    def sign_message(self, message: str, private_key: int, params: Dict) -> Optional[Dict]:
        """
        Manually ECDSA-sign per the hints' convention (z = SHA-256 mod n), using a
        fresh random nonce. Deterministic math so it matches the server's verify.
        """
        try:
            import secrets
            c = self._curve(params)
            n, p, a = c["n"], c["p"], c["a"]
            G = (c["Gx"], c["Gy"])
            # Hash the champion message with the SAME convention that recovered a
            # pubkey-verified d (stored as _z_conv_index). Using a different
            # convention here would produce a valid-looking sig the server rejects.
            conv = getattr(self, "_z_conv_index", 0)
            z_variants = self._z_variants(message, n)
            z = z_variants[conv] if conv < len(z_variants) else z_variants[0]
            print(f"Signing with z-convention {conv}", flush=True)

            for _ in range(32):
                k = secrets.randbelow(n - 1) + 1
                R = self._pt_mul(k, G, p, a)
                if R is None:
                    continue
                r = R[0] % n
                if r == 0:
                    continue
                s = (self._inv(k, n) * (z + r * private_key)) % n
                if s == 0:
                    continue
                # Low-s normalization (some verifiers require s <= n/2).
                if s > n // 2:
                    s = n - s
                print(f"Signed champion message (r={hex(r)[:14]}..., s={hex(s)[:14]}...)", flush=True)
                return {"r": str(r), "s": str(s), "_r_int": r, "_s_int": s}
            print("Failed to produce a valid signature", flush=True)
            return None
        except Exception as e:
            print(f"Error signing message: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return None

    def submit_signature(self, signature: Dict) -> Optional[str]:
        """
        POST the forged signature to /api/champion. Hint 5 says the body is
        {"r": ..., "s": ...} directly. We try that first, then a couple of
        fallback shapes, and accept r/s as strings or ints.
        """
        r_str, s_str = signature["r"], signature["s"]
        r_int, s_int = signature.get("_r_int"), signature.get("_s_int")
        bodies = [
            {"r": r_str, "s": s_str},          # Hint 5: exact shape
            {"r": r_int, "s": s_int},          # integer variant
            {"signature": {"r": r_str, "s": s_str}},  # wrapped fallback
        ]
        for body in bodies:
            try:
                resp = requests.post(f"{self.base_url}/api/champion", json=body, timeout=10)
                keys = ",".join(body.keys())
                print(f"POST /api/champion [{keys}]: {resp.status_code} - {resp.text[:200]}", flush=True)
                if resp.status_code == 200:
                    data = resp.json()
                    flag = data.get("flag") or self._find_flag(resp.text)
                    if flag:
                        print(f"FLAG FOUND: {flag}", flush=True)
                        return flag
            except Exception as e:
                print(f"Error submitting signature: {e}", flush=True)
        return None

    @staticmethod
    def _find_flag(text: str) -> Optional[str]:
        import re
        m = re.search(r"HALCTF\{[^}]+\}", text or "")
        return m.group(0) if m else None

    def solve(self) -> bool:
        """Main solving routine"""
        print("=== Indigo League Solver ===", flush=True)

        # Step 1: Get all the data
        badges = self.get_badges()
        pubkey = self.get_pubkey()
        params = self.get_params()
        champion_msg = self.get_champion_message()

        # Report EXACTLY which piece is missing (the old vague message hid that
        # /api/champion was the culprit). badges/pubkey/params are truly required
        # for key recovery; champion_msg is required to sign but is fetched with
        # robust extraction now, so log loudly rather than silently blaming all.
        missing = [name for name, val in
                   (("badges", badges), ("pubkey", pubkey), ("params", params))
                   if not val]
        if missing:
            print(f"Missing required data: {', '.join(missing)} — cannot proceed", flush=True)
            return False
        if not champion_msg:
            print("Champion message came back empty after robust extraction. "
                  "Recovering the key anyway so it's ready; inspect the RAW "
                  "/api/champion dump above for the real message field/endpoint.",
                  flush=True)

        # Step 2: Find nonce reuse
        reuse_pair = self.find_nonce_reuse(badges)
        if not reuse_pair:
            print("No nonce reuse found - cannot recover private key", flush=True)
            return False

        badge1, badge2 = reuse_pair

        # Step 3: Recover private key (verified against the pubkey when possible)
        private_key = self.recover_private_key(badge1, badge2, params, pubkey)
        if not private_key:
            print("Failed to recover private key", flush=True)
            return False

        # If we still have no message to sign, DON'T waste a submission attempt
        # signing an empty string. The key is recovered (and verified above), so a
        # tuned rerun with the correct message field/endpoint will finish instantly.
        if not champion_msg:
            print("Private key recovered but champion message is empty — NOT "
                  "submitting a signature over an empty message. Fix the message "
                  "field/endpoint (see RAW dump) and rerun.", flush=True)
            return False

        # Step 4: Sign the champion message
        signature = self.sign_message(champion_msg, private_key, params)
        if not signature:
            print("Failed to sign champion message", flush=True)
            return False

        # Step 5: Submit the signature
        flag = self.submit_signature(signature)
        if not flag:
            print("Failed to get flag from signature", flush=True)
            return False

        # Step 6: Submit flag to scoring system
        success = self.agent.submit_flag(flag, self.agent.challenge_id)
        return success
