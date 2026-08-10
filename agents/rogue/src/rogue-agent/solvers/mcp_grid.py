"""
MCP — AI / Protocol (250)   [file named mcp_grid to avoid clashing with the `mcp` pkg]

Puzzle shape (from hints):
  - The Grid (Master Control Program) speaks a layered wire encoding. NOTHING is
    plaintext, not even the first banner.
  - Recon notes give the frame shape: hex, then XOR, then base64 — with a
    PLACEHOLDER key. We brute-force short printable XOR keys against the live
    banner until the decoded output is readable.
  - Then: ask for a dump, learn how Program IDs are formed (they are NOT random),
    MINT a valid Program ID, RE-ENCODE it in the same layering, and send it to be
    granted User priority -> flag.

Encoding pipeline (recon: "hex, then XOR, then base64" applied to plaintext):
    wire = base64( xor( hex(plaintext), key ) )
  So decode:  plaintext = unhex( xor( b64decode(wire), key ) )
  We ALSO try the reverse layer order as a fallback, because the note wording is
  ambiguous and this is the #1 thing to tune on first contact.

Deterministic; no LLM. Talks raw TCP (falls back to HTTP if the target is web).

WATCH ON FIRST DETONATION:
  - Decode DIRECTION + which layer holds the XOR. We try 4 combinations and log
    the readable one. Lock in the winner.
  - The XOR key: brute-forced over printable keys up to BRUTE_FORCE_MAX bytes.
    If nothing decodes, widen the charset / length (see _candidate_keys()).
  - Program ID FORMAT: parsed from the dump heuristically (prefix + counter/CRC).
    The dump text is logged raw — read it and adjust _mint_program_id().
  - The command words ("dump", request-priority) are guessed; the decoded banner
    usually tells you the real verbs — adjust COMMANDS.
"""
import base64
import binascii
import itertools
import string
from typing import List, Optional, Tuple

from ._common import find_flag, http_get, http_post, log, recon, tcp_exchange

PRINTABLE = (string.ascii_letters + string.digits + "_-!@#$%^&*").encode()
COMMANDS = ["dump", "DUMP", "core dump", "list", "help", "programs", "?"]


def _xor(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def _score(b: bytes) -> float:
    """Englishness score in [0,1]. High only for genuine text — this avoids the
    common false positive where XORing the hex layer with a WRONG key yields a
    still-hex-charset blob (which trivially passes a naive printable check but is
    NOT the plaintext; it just needs another unhex pass)."""
    if not b:
        return 0.0
    printable = sum(1 for c in b if 32 <= c < 127 or c in (9, 10, 13))
    pr = printable / len(b)
    if pr < 0.85:
        return 0.0
    letters = sum(1 for c in b if 65 <= c < 91 or 97 <= c < 123)
    spaces = b.count(0x20)
    hexset = sum(1 for c in b if chr(c).lower() in "0123456789abcdef")
    # Penalise pure-hex output (a missing decode layer) hard.
    if len(b) > 4 and hexset / len(b) > 0.95:
        return 0.1
    score = pr * 0.4 + (letters / len(b)) * 0.4 + min(spaces / max(1, len(b)) * 5, 0.2)
    return score


def _readable(b: bytes) -> bool:
    return _score(b) >= 0.45


def _try_decode(wire: bytes, key: bytes) -> Optional[bytes]:
    """Attempt every plausible layer order with this key; return the BEST-scoring
    readable plaintext (not merely the first — a wrong key can produce a hex-ish
    blob that passes a naive check). Orders (outer->inner as seen on wire):
      A: b64 -> xor -> unhex          (recon literal: hex,xor,base64 encode)
      B: unhex -> xor -> b64decode
      C: b64 -> xor                    (no hex layer)
      D: unhex -> xor
    """
    candidates: List[Tuple[str, bytes]] = []
    s = wire.strip()

    # A: base64 outer, then xor, then hex-decode
    try:
        raw = base64.b64decode(s, validate=False)
        x = _xor(raw, key)
        try:
            candidates.append(("A:b64->xor->unhex", binascii.unhexlify(_strip_hex(x))))
        except Exception:
            pass
        candidates.append(("C:b64->xor", x))
    except Exception:
        pass

    # B: hex outer, then xor, then base64-decode
    try:
        raw = binascii.unhexlify(_strip_hex(s))
        x = _xor(raw, key)
        try:
            candidates.append(("B:unhex->xor->b64", base64.b64decode(x, validate=False)))
        except Exception:
            pass
        candidates.append(("D:unhex->xor", x))
    except Exception:
        pass

    best_label, best_out, best_score = None, None, 0.0
    for label, out in candidates:
        sc = _score(out)
        if sc > best_score:
            best_label, best_out, best_score = label, out, sc
    if best_out is not None and best_score >= 0.45:
        log(f"[mcp] decoded via {best_label} key={key!r} score={best_score:.2f}: "
            f"{best_out[:200]!r}")
        return best_out
    return None


def _strip_hex(b: bytes) -> bytes:
    """Keep only hex chars (banner may include whitespace/newlines)."""
    return bytes(c for c in b if chr(c).lower() in "0123456789abcdef")


class MCPGridSolver:
    def __init__(self, agent):
        self.agent = agent
        self.base_url = agent.base_url
        self.ip = agent.target_ip
        self.port = int(agent.target_port or 80)
        # BRUTE_FORCE_MAX travels via main.py; default 8 if absent.
        self.max_key_len = getattr(agent, "brute_force_max", 8)

    def _candidate_keys(self) -> List[bytes]:
        """Short printable keys: all 1-byte, then a curated set of 2-3 byte
        keys (full 2-3 byte printable space is huge; we cap it). If decode
        fails on the real run, widen this."""
        keys: List[bytes] = [bytes([c]) for c in PRINTABLE]
        # single ascii bytes 0x20-0x7e too (covers any printable, not just our set)
        keys += [bytes([c]) for c in range(0x20, 0x7f)]
        # common short word keys
        for w in (b"key", b"MCP", b"grid", b"tron", b"TRON", b"flynn", b"clu",
                  b"user", b"USER", b"1234", b"pass", b"mcp!"):
            if len(w) <= self.max_key_len:
                keys.append(w)
        # de-dup preserving order
        seen, out = set(), []
        for k in keys:
            if k not in seen:
                seen.add(k)
                out.append(k)
        return out

    def _get_banner(self) -> Optional[bytes]:
        """Read the encoded banner over TCP; fall back to HTTP root."""
        b = tcp_exchange(self.ip, self.port, payload=b"", read_banner=True)
        if b:
            return b
        r = http_get(self.base_url + "/")
        if r is not None and r.content:
            return r.content
        return None

    def _brute_banner(self, banner: bytes) -> Optional[bytes]:
        log(f"[mcp] brute-forcing XOR keys (<= {self.max_key_len}B) against banner")
        for key in self._candidate_keys():
            out = _try_decode(banner, key)
            if out is not None:
                self.key = key
                log(f"[mcp] === banner readable with key={key!r} ===")
                return out
        log("[mcp] no single/short key decoded the banner — widen _candidate_keys "
            "(longer keys, other layer order). Raw banner logged above.")
        return None

    def _encode(self, plaintext: bytes, key: bytes, order: str) -> bytes:
        """Re-encode a message using the layering that decoded the banner."""
        if order.startswith("A") or order == "C":
            # inverse of A/C: (hex ->) xor -> base64
            inner = binascii.hexlify(plaintext) if order.startswith("A") else plaintext
            return base64.b64encode(_xor(inner, key))
        # inverse of B/D: (base64 ->) xor -> hex
        inner = base64.b64encode(plaintext) if order.startswith("B") else plaintext
        return binascii.hexlify(_xor(inner, key))

    def _send_encoded(self, plaintext: bytes) -> Optional[bytes]:
        """Encode with the discovered key/order and send; decode the reply."""
        key = getattr(self, "key", b"")
        order = getattr(self, "order", "A:b64->xor->unhex")
        if not key:
            return None
        wire = self._encode(plaintext, key, order)
        reply = tcp_exchange(self.ip, self.port, payload=wire + b"\n", read_banner=False)
        if not reply:
            return None
        dec = _try_decode(reply, key)
        return dec if dec is not None else reply

    def _mint_program_id(self, dump_text: bytes) -> List[bytes]:
        """IDs are NOT random. Derive candidate Program IDs from the dump.
        Heuristics (logged; tune from the real dump):
          - reuse a prefix seen in the dump with the next sequential number
          - the dump may literally describe the format
        Returns several candidates to try in order."""
        text = dump_text.decode("latin1", "replace")
        log(f"[mcp] dump (for ID minting):\n{text[:800]}")
        import re
        cands: List[bytes] = []

        # Pattern: TOKENS like ABC-1234 / PROG_007 / 0xDEAD
        ids = re.findall(r"[A-Za-z]{2,}[-_]?\d{2,}", text)
        nums = [int(n) for n in re.findall(r"\d+", " ".join(ids))] if ids else []
        if ids:
            log(f"[mcp] observed ID-like tokens: {ids[:10]}")
            # next sequential after the max seen
            base = ids[-1]
            m = re.match(r"([A-Za-z]+[-_]?)(\d+)", base)
            if m:
                prefix, num = m.group(1), int(m.group(2))
                width = len(m.group(2))
                nxt = max(nums) + 1 if nums else num + 1
                cands.append(f"{prefix}{nxt:0{width}d}".encode())
                cands.append(f"{prefix}{num:0{width}d}".encode())  # reuse highest
        # Fallback generic guesses
        cands += [b"USER-0001", b"PROG-0001", b"ID-0001", b"1000", b"0001"]
        # de-dup
        seen, out = set(), []
        for c in cands:
            if c not in seen:
                seen.add(c)
                out.append(c)
        log(f"[mcp] Program ID candidates: {out}")
        return out

    def solve(self) -> Optional[str]:
        banner = self._get_banner()
        if not banner:
            log("[mcp] no banner from TCP or HTTP; cannot proceed")
            return None

        decoded = self._brute_banner(banner)
        if decoded is None:
            return None
        # remember which order won (stored by _try_decode via log; re-derive)
        self._lock_order(banner)

        fl = find_flag(decoded.decode("latin1", "replace"))
        if fl:
            return fl

        # Ask for a dump using each candidate command until one returns more data.
        dump = None
        for cmd in COMMANDS:
            resp = self._send_encoded(cmd.encode())
            if resp and len(resp) > len(decoded) // 2:
                log(f"[mcp] command '{cmd}' returned a dump ({len(resp)}B)")
                dump = resp
                fl = find_flag(resp.decode("latin1", "replace"))
                if fl:
                    return fl
                break
        if dump is None:
            log("[mcp] no dump command worked; using banner as ID source")
            dump = decoded

        # Mint + submit Program IDs.
        for pid in self._mint_program_id(dump):
            for verb in (b"", b"auth ", b"login ", b"id ", b"USER "):
                resp = self._send_encoded(verb + pid)
                if not resp:
                    continue
                fl = find_flag(resp.decode("latin1", "replace"))
                if fl:
                    log(f"[mcp] flag after Program ID {pid!r}: {fl}")
                    return fl
        log("[mcp] no Program ID granted priority; inspect dump + tune _mint_program_id")
        return None

    def _lock_order(self, banner: bytes) -> None:
        """Re-run decode to record which layer order succeeded (for re-encoding)."""
        key = getattr(self, "key", b"")
        if not key:
            return
        s = banner.strip()
        # Mirror _try_decode ordering; store first readable order label.
        import base64 as _b64
        try:
            raw = _b64.b64decode(s, validate=False)
            x = _xor(raw, key)
            try:
                if _readable(binascii.unhexlify(_strip_hex(x))):
                    self.order = "A:b64->xor->unhex"
                    return
            except Exception:
                pass
            if _readable(x):
                self.order = "C:b64->xor"
                return
        except Exception:
            pass
        try:
            raw = binascii.unhexlify(_strip_hex(s))
            x = _xor(raw, key)
            try:
                if _readable(_b64.b64decode(x, validate=False)):
                    self.order = "B:unhex->xor->b64"
                    return
            except Exception:
                pass
            if _readable(x):
                self.order = "D:unhex->xor"
        except Exception:
            pass
