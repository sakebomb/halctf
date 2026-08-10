"""
Puzzle 4 — Proteus (Crypto / Recon, 200 pts)

GET /transmission -> a message obscured by a transform chosen FRESH each connect.
POST /decode {"passphrase": "..."} checks a guess directly (no penalty for wrong
guesses — guessing is free). The obscuring is NOT always the same kind of thing:
sometimes a byte-level transform (base64/hex/rot13/reverse/xor/base32/atbash/
caesar), sometimes it's just text that says what the passphrase is (hint 3:
"it's just text, and the trick is noticing what's actually being said").

Strategy: recon the shape (charset/length/prose-vs-noise), then run a cascade of
candidate decodings, harvesting every plausible passphrase, and POST each to
/decode until one unlocks. An LLM pass (if available) helps read "prose" cases.

Env: HAL_TARGET_IP/_PORT.
"""
import base64
import binascii
import codecs
import re
import string
from typing import List, Optional

from ._http import discover_base, find_flag, get, post

PRINTABLE = set(bytes(string.printable, "ascii"))


class ProteusSolver:
    def __init__(self, agent):
        self.agent = agent
        self.base: Optional[str] = None
        self.llm = getattr(agent, "llm", None)

    def solve(self) -> bool:
        print("=== Proteus Solver (multi-cipher recon) ===", flush=True)
        self.base = discover_base(self.agent.target_ip, self.agent.target_port)
        if not self.base:
            return False

        # Retry a few connects — each gives a fresh transform, and a cheap one may
        # come up that our cascade nails even if a hard one didn't.
        for attempt in range(4):
            msg = self._get_transmission()
            if not msg:
                continue
            print(f"[attempt {attempt}] transmission ({len(msg)} chars): {msg[:200]!r}", flush=True)
            candidates = self._candidate_passphrases(msg)
            # LLM assist for the "it's just prose telling you the answer" case.
            llm_guess = self._llm_read(msg)
            if llm_guess:
                candidates = llm_guess + candidates
            seen = set()
            for cand in candidates:
                cand = cand.strip()
                if not cand or cand in seen:
                    continue
                seen.add(cand)
                if self._try_decode(cand):
                    return True
        print("No passphrase unlocked across attempts. Review transmissions above.", flush=True)
        return False

    def _get_transmission(self) -> str:
        resp = get(f"{self.base}/transmission")
        if resp is None:
            return ""
        try:
            obj = resp.json()
            if isinstance(obj, dict):
                for k in ("transmission", "message", "data", "text", "cipher", "payload"):
                    if isinstance(obj.get(k), str):
                        return obj[k]
        except Exception:
            pass
        return (resp.text or "").strip()

    def _try_decode(self, passphrase: str) -> bool:
        resp = post(f"{self.base}/decode", {"passphrase": passphrase})
        if resp is None:
            return False
        low = (resp.text or "").lower()
        flag = find_flag(resp.text)
        if flag:
            print(f"UNLOCKED with passphrase={passphrase!r}", flush=True)
            return self.agent.submit_flag(flag, self.agent.challenge_id)
        # Some servers return {"correct": true} then require a follow-up; log it.
        if any(w in low for w in ("correct", "unlocked", "success", "accepted")):
            print(f"Passphrase {passphrase!r} accepted (no inline flag) — re-fetching", flush=True)
            f2 = self._get_transmission()
            flag = find_flag(f2)
            if flag:
                return self.agent.submit_flag(flag, self.agent.challenge_id)
        return False

    def _candidate_passphrases(self, msg: str) -> List[str]:
        """Run every plausible reversible transform; keep results that look like a
        clean passphrase (mostly printable). Order by likelihood from the shape."""
        out: List[str] = [msg]  # sometimes the message IS the passphrase (plain).
        raw = msg.strip()

        # base64
        out.append(self._safe(lambda: base64.b64decode(raw + "=" * (-len(raw) % 4)).decode("utf-8", "ignore")))
        # base32
        out.append(self._safe(lambda: base64.b32decode(raw.upper() + "=" * (-len(raw) % 8)).decode("utf-8", "ignore")))
        # hex
        out.append(self._safe(lambda: bytes.fromhex(re.sub(r"\s+", "", raw)).decode("utf-8", "ignore")))
        # rot13
        out.append(self._safe(lambda: codecs.decode(raw, "rot_13")))
        # reverse
        out.append(raw[::-1])
        # atbash
        out.append(self._atbash(raw))
        # caesar shifts 1..25
        for shift in range(1, 26):
            out.append(self._caesar(raw, shift))
        # single-byte XOR over hex/base64-decoded bytes
        for decoder in (self._as_hex_bytes, self._as_b64_bytes, lambda s: s.encode()):
            data = decoder(raw)
            if data:
                out.extend(self._xor_bruteforce(data))

        # Keep only clean-ish printable candidates.
        cleaned = []
        for c in out:
            if c and self._is_cleanish(c):
                cleaned.append(c)
        return cleaned

    # --- transform helpers ---
    @staticmethod
    def _safe(fn) -> str:
        try:
            r = fn()
            return r if isinstance(r, str) else ""
        except Exception:
            return ""

    @staticmethod
    def _atbash(s: str) -> str:
        def m(ch):
            if ch.islower():
                return chr(ord("z") - (ord(ch) - ord("a")))
            if ch.isupper():
                return chr(ord("Z") - (ord(ch) - ord("A")))
            return ch
        return "".join(m(c) for c in s)

    @staticmethod
    def _caesar(s: str, shift: int) -> str:
        def m(ch):
            if ch.islower():
                return chr((ord(ch) - ord("a") - shift) % 26 + ord("a"))
            if ch.isupper():
                return chr((ord(ch) - ord("A") - shift) % 26 + ord("A"))
            return ch
        return "".join(m(c) for c in s)

    @staticmethod
    def _as_hex_bytes(s: str) -> Optional[bytes]:
        try:
            return bytes.fromhex(re.sub(r"\s+", "", s))
        except Exception:
            return None

    @staticmethod
    def _as_b64_bytes(s: str) -> Optional[bytes]:
        try:
            return base64.b64decode(s + "=" * (-len(s) % 4))
        except (binascii.Error, ValueError):
            return None

    @staticmethod
    def _xor_bruteforce(data: bytes) -> List[str]:
        out = []
        for key in range(1, 256):
            dec = bytes(b ^ key for b in data)
            if all(b in PRINTABLE for b in dec):
                out.append(dec.decode("ascii", "ignore"))
        return out

    @staticmethod
    def _is_cleanish(s: str) -> bool:
        if not s or len(s) > 200:
            return False
        printable = sum(1 for c in s if c in string.printable)
        return printable / len(s) > 0.9

    def _llm_read(self, msg: str) -> List[str]:
        """If the transmission is prose that states the passphrase, the model reads
        it out. Returns 0..few candidate passphrases."""
        if not self.llm:
            return []
        prompt = (
            "A CTF 'Proteus' transmission is below. It is EITHER a byte-level "
            "cipher OR plain text that literally states a passphrase. If it plainly "
            "states or strongly implies a passphrase, output ONLY that passphrase on "
            "one line, nothing else. If it looks like an encoded cipher, output "
            "nothing.\n\nTRANSMISSION:\n" + msg[:1000]
        )
        text = self.llm.ask(prompt, max_tokens=64)
        if not text:
            return []
        lines = [ln.strip().strip('"\'`') for ln in text.splitlines() if ln.strip()]
        return [ln for ln in lines if 0 < len(ln) <= 100][:3]
