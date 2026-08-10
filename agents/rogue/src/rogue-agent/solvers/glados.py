"""
GLaDOS — AI / Data Analysis (250)

Puzzle shape (from hints):
  - You submit input; the response has short honest fields (input length, a
    verbatim preview) AND one LARGE field.
  - Inside that large field, ONE position never changes no matter what you send.
    Everything else is randomised per response. Find the invariant position.
  - Proving you found it earns a taunt + ONE small piece of the flag, then it
    resets and makes you find the NEXT invariant/piece from scratch.

Strategy (deterministic; no LLM needed):
  1. Recon to learn the submit endpoint + the field names (LOG RAW BODIES).
  2. Submit N (>=8) varied inputs, collect the large field each time.
  3. Diff them position-by-position: a position is invariant iff its byte is
     identical across ALL samples. Random noise collapses those to a tiny set.
  4. Report the invariant position (and/or its value) back the way the server
     wants; capture the flag piece it returns.
  5. Loop: after each piece, the field re-randomises with a new invariant — keep
     diffing and reporting until a full HALCTF{...} is assembled or it says done.

WATCH ON FIRST DETONATION:
  - The submit endpoint + JSON field names are guessed. The recon dump reveals
    the real ones — adjust SUBMIT_PATHS / _large_field() / _report_position().
  - "How to report the answer" is the fuzziest part. We try several encodings
    (index, index+value, value) and log every attempt + reply so you can see
    which shape it accepts.
  - If pieces arrive but never assemble into a flag, check whether it wants the
    pieces concatenated by us vs. returned whole at the end.
"""
from collections import Counter
from typing import Any, Dict, List, Optional

from ._common import find_flag, http_get, http_post, log, parse_json, recon

# CONFIRMED (run 09a3b2e9): the root banner says "Submit your test material to
# POST /api/test". That path is tried FIRST; the rest are fallbacks.
SUBMIT_PATHS = ["/api/test", "/submit", "/analyze", "/test", "/api/submit",
                "/api/analyze", "/"]
# Field names the large "analysis" blob might live under.
LARGE_FIELD_KEYS = ["analysis", "result", "data", "report", "output", "trace",
                    "buffer", "payload", "sample", "haystack", "body"]
PREVIEW_KEYS = ["preview", "echo", "input", "received", "your_input"]

SAMPLES = 12  # how many probes to diff (more = fewer false-invariants)


class GLaDOSSolver:
    def __init__(self, agent):
        self.agent = agent
        self.base_url = agent.base_url

    # --- response shape helpers -------------------------------------------------
    def _large_field(self, obj: Any) -> Optional[str]:
        """Extract the big randomised field. Tries known keys, else the longest
        string value in the payload."""
        if isinstance(obj, str):
            return obj
        if not isinstance(obj, dict):
            return None
        for k in LARGE_FIELD_KEYS:
            v = obj.get(k)
            if isinstance(v, str) and len(v) > 16:
                return v
        # Fallback: longest string value anywhere in the dict.
        longest, best = None, 0
        for v in _iter_strings(obj):
            if len(v) > best:
                longest, best = v, len(v)
        return longest if best > 16 else None

    def _submit(self, path: str, payload: str) -> Optional[Any]:
        url = self.base_url.rstrip("/") + path
        # Try JSON first (most likely), then form, then query. Require a 2xx —
        # a 404 is a WRONG path, not a valid empty response (run 09a3b2e9 mistook
        # a 404 on /submit for a working endpoint and diffed 0 samples).
        for kw in ({"json": {"input": payload, "data": payload, "text": payload}},
                   {"data": {"input": payload}},
                   {"params": {"input": payload}}):
            r = http_post(url, **kw)
            if r is not None and 200 <= r.status_code < 300:
                return parse_json(r) or r.text
        return None

    def _find_submit_path(self) -> Optional[str]:
        for p in SUBMIT_PATHS:
            obj = self._submit(p, "AAAAAAAA")
            if obj is not None and self._large_field(obj) is not None:
                log(f"[glados] using submit path {p}")
                return p
        log("[glados] no submit path produced a large field; check recon dump")
        return None

    # --- the core diff ----------------------------------------------------------
    def _collect(self, path: str, n: int) -> List[str]:
        fields: List[str] = []
        for i in range(n):
            # Vary the input each time so only true invariants survive the diff.
            probe = f"PROBE{i:03d}" + ("X" * (i % 7))
            obj = self._submit(path, probe)
            f = self._large_field(obj) if obj is not None else None
            if f:
                fields.append(f)
        log(f"[glados] collected {len(fields)} large-field samples "
            f"(lens={[len(f) for f in fields][:8]}...)")
        return fields

    def _invariant_positions(self, fields: List[str]) -> List[int]:
        """A position is invariant iff its char is identical across every sample.
        Only compare up to the shortest sample to stay in-bounds."""
        if len(fields) < 3:
            return []
        n = min(len(f) for f in fields)
        inv = [i for i in range(n) if len({f[i] for f in fields}) == 1]
        log(f"[glados] invariant positions ({len(inv)}): {inv[:40]}"
            f"{'...' if len(inv) > 40 else ''}")
        return inv

    def _report_position(self, path: str, idx: int, value: str) -> Optional[Any]:
        """Tell GLaDOS the invariant we found. The accepted shape is unknown, so
        try several and log each reply — the winning one shows in the live log."""
        url = self.base_url.rstrip("/") + path
        attempts = [
            {"json": {"position": idx, "index": idx, "value": value}},
            {"json": {"answer": idx}},
            {"json": {"position": idx}},
            {"json": {"value": value}},
            {"json": {"input": str(idx)}},
            {"params": {"position": idx}},
        ]
        for kw in attempts:
            r = http_post(url, **kw)
            if r is None:
                continue
            body = parse_json(r) or r.text
            fl = find_flag(r.text)
            if fl:
                log(f"[glados] flag piece / flag in reply: {fl}")
            # Heuristic: a reply that changes tone / mentions correct is a hit.
            low = r.text.lower()
            if fl or any(w in low for w in ("correct", "piece", "next", "well done",
                                            "impressive", "proceed")):
                return body
        return None

    # --- main -------------------------------------------------------------------
    def solve(self) -> Optional[str]:
        recon(self.base_url)
        path = self._find_submit_path()
        if not path:
            return None

        pieces: List[str] = []
        # Up to ~12 rounds: each round finds a fresh invariant and extracts a
        # piece. Stop as soon as a full flag appears anywhere.
        for rnd in range(12):
            log(f"=== GLaDOS round {rnd} ===")
            fields = self._collect(path, SAMPLES)
            if len(fields) < 3:
                log("[glados] too few samples to diff; aborting round")
                break

            inv = self._invariant_positions(fields)
            if not inv:
                log("[glados] no invariant position found — maybe the whole large "
                    "field is stable this round; check sample diffs above")
                # As a fallback, treat the single most-common char position as candidate.
                inv = self._fallback_candidates(fields)

            sample = fields[0]
            got_piece = False
            for idx in inv[:20]:  # cap reporting attempts per round
                reply = self._report_position(path, idx, sample[idx])
                if reply is None:
                    continue
                text = reply if isinstance(reply, str) else str(reply)
                fl = find_flag(text)
                if fl and fl.upper().startswith("HALCTF{") and fl.endswith("}"):
                    log(f"[glados] complete flag: {fl}")
                    return fl
                if fl:
                    pieces.append(fl)
                    got_piece = True
                    log(f"[glados] accumulated pieces: {pieces}")
                    break
                # Piece might be a bare fragment, not flag-shaped.
                frag = _extract_fragment(text)
                if frag:
                    pieces.append(frag)
                    got_piece = True
                    log(f"[glados] fragment '{frag}'; pieces so far: {pieces}")
                    break
            if not got_piece:
                log("[glados] round produced no accepted report; stopping")
                break

            assembled = _assemble(pieces)
            if assembled:
                log(f"[glados] assembled candidate: {assembled}")
                return assembled

        assembled = _assemble(pieces)
        if assembled:
            return assembled
        log(f"[glados] ran out of rounds; pieces collected: {pieces}")
        return None

    def _fallback_candidates(self, fields: List[str]) -> List[int]:
        """If nothing is perfectly invariant, rank positions by how dominant a
        single char is — the intended invariant may have rare noise."""
        n = min(len(f) for f in fields)
        scored = []
        for i in range(n):
            c = Counter(f[i] for f in fields)
            top = c.most_common(1)[0][1]
            scored.append((top, i))
        scored.sort(reverse=True)
        cands = [i for _, i in scored[:10]]
        log(f"[glados] fallback candidate positions: {cands}")
        return cands


# --- module-level utilities ----------------------------------------------------
def _iter_strings(obj: Any):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _iter_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _iter_strings(v)


def _extract_fragment(text: str) -> Optional[str]:
    """Pull a plausible flag fragment out of a reply (e.g. a quoted token or a
    piece like 'HALCTF{' or '_part_2_'). Best-effort — logged, never trusted
    silently."""
    import re
    # quoted token
    m = re.search(r'["\']([A-Za-z0-9_}{]{2,})["\']', text)
    if m:
        return m.group(1)
    return None


def _assemble(pieces: List[str]) -> Optional[str]:
    """If concatenating collected pieces yields a full HALCTF{...}, return it."""
    if not pieces:
        return None
    joined = "".join(pieces)
    fl = find_flag(joined)
    if fl and fl.upper().startswith("HALCTF{") and fl.endswith("}"):
        return fl
    return None
