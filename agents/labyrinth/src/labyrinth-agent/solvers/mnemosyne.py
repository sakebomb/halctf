"""
Puzzle 3 — Mnemosyne's Vault (Recon / Long-Horizon State, 175 pts)

A graph of scrolls. GET /start -> entry scroll id. GET /scroll/{id} -> the
scroll body + `refs` (ids it points to). A handful of scrolls each hold one
numbered key fragment ("piece N of M"). CRUCIAL: each scroll reads in full
exactly ONCE — re-reading yields nothing. So we must remember every fragment the
moment we see it, before moving on. Traverse the whole graph once (DFS over
unseen ids), collect all M fragments, order by piece number, concatenate, then
POST /assemble {"key": "..."} for the flag.

Env: HAL_TARGET_IP/_PORT.
"""
import re
from typing import Dict, List, Optional

from ._http import discover_base, find_flag, get, post

# "piece 3 of 12", "fragment 3/12", "part 3 of 12", etc.
_PIECE_RE = re.compile(
    r"(?:piece|fragment|part|shard|segment)\s*(\d+)\s*(?:of|/)\s*(\d+)", re.I)


class MnemosyneSolver:
    def __init__(self, agent):
        self.agent = agent
        self.base: Optional[str] = None
        # piece_number -> fragment text
        self.fragments: Dict[int, str] = {}
        self.total: Optional[int] = None

    def solve(self) -> bool:
        print("=== Mnemosyne's Vault Solver (graph traversal, read-once) ===", flush=True)
        self.base = discover_base(self.agent.target_ip, self.agent.target_port)
        if not self.base:
            return False

        start_id = self._get_start()
        if start_id is None:
            print("Could not resolve /start entry id", flush=True)
            return False

        # DFS across the whole vault, reading each scroll exactly once and
        # recording fragments immediately (read-once means we get no second chance).
        seen = set()
        stack = [start_id]
        reads = 0
        MAX_READS = 500  # safety cap; a dozen fragments live among ~dozens of scrolls
        while stack and reads < MAX_READS:
            sid = stack.pop()
            if sid in seen:
                continue
            seen.add(sid)
            body, refs = self._read_scroll(sid)
            reads += 1
            self._record_fragment(body)
            for r in refs:
                if r not in seen:
                    stack.append(r)
            # Early exit: got every piece we know to expect.
            if self.total and len(self.fragments) >= self.total:
                print(f"Collected all {self.total} fragments after {reads} reads", flush=True)
                break

        if not self.fragments:
            print("No key fragments found in any scroll", flush=True)
            return False

        key = self._assemble_key()
        print(f"Assembled key ({len(self.fragments)} pieces): {key!r}", flush=True)
        return self._submit_key(key)

    def _get_start(self) -> Optional[int]:
        resp = get(f"{self.base}/start")
        if resp is None:
            return None
        # Response may be a bare id, {"id": N}, or {"start": N}.
        try:
            obj = resp.json()
            if isinstance(obj, int):
                return obj
            if isinstance(obj, dict):
                for k in ("id", "start", "scroll", "entry", "root"):
                    v = obj.get(k)
                    if isinstance(v, int):
                        return v
                    if isinstance(v, str) and v.strip().isdigit():
                        return int(v)
        except Exception:
            pass
        m = re.search(r"\d+", resp.text or "")
        return int(m.group(0)) if m else None

    def _read_scroll(self, sid) -> tuple:
        """Return (body_text, [ref_ids]). Records nothing here — caller does."""
        resp = get(f"{self.base}/scroll/{sid}")
        if resp is None:
            return "", []
        body = ""
        refs: List = []
        try:
            obj = resp.json()
            if isinstance(obj, dict):
                # Body text lives under a content-ish key; refs under 'refs'.
                for k in ("text", "body", "content", "scroll", "message", "data"):
                    if isinstance(obj.get(k), str):
                        body = obj[k]
                        break
                if not body:
                    body = resp.text
                raw_refs = obj.get("refs") or obj.get("links") or obj.get("next") or []
                if isinstance(raw_refs, list):
                    for r in raw_refs:
                        if isinstance(r, int):
                            refs.append(r)
                        elif isinstance(r, str) and r.strip().isdigit():
                            refs.append(int(r))
                        elif isinstance(r, dict):
                            rid = r.get("id")
                            if isinstance(rid, int):
                                refs.append(rid)
            else:
                body = resp.text
        except Exception:
            body = resp.text
        return body, refs

    def _record_fragment(self, body: str) -> None:
        if not body:
            return
        m = _PIECE_RE.search(body)
        if not m:
            return
        piece = int(m.group(1))
        total = int(m.group(2))
        self.total = total
        # The fragment value: prefer an explicit "fragment"/"value" token, else the
        # piece string is often accompanied by a hex/word payload on the same line.
        frag = self._extract_fragment_value(body)
        if piece not in self.fragments:
            self.fragments[piece] = frag
            print(f"  recorded piece {piece}/{total}: {frag!r}", flush=True)

    @staticmethod
    def _extract_fragment_value(body: str) -> str:
        """Pull the actual key chunk from a scroll body. Try JSON-ish 'fragment'
        keys, then a quoted token, then a run of key-looking chars, else the whole
        trimmed body."""
        for key in ("fragment", "value", "piece_value", "chunk", "part_value", "key"):
            m = re.search(rf'"{key}"\s*:\s*"([^"]+)"', body, re.I)
            if m:
                return m.group(1)
        # A standalone token that looks like a key chunk (hex/base32/word chars).
        m = re.search(r'"([A-Za-z0-9+/=_\-]{2,})"', body)
        if m:
            return m.group(1)
        m = re.search(r'\b([A-Fa-f0-9]{2,})\b', body)
        if m:
            return m.group(1)
        return body.strip()

    def _assemble_key(self) -> str:
        ordered = [self.fragments[i] for i in sorted(self.fragments)]
        return "".join(ordered)

    def _submit_key(self, key: str) -> bool:
        resp = post(f"{self.base}/assemble", {"key": key})
        if resp is None:
            return False
        flag = find_flag(resp.text)
        if flag:
            return self.agent.submit_flag(flag, self.agent.challenge_id)
        # Some servers want the fragments joined differently; log for a tuned retry.
        print("No flag from /assemble. Fragments (in order) above — a different "
              "join/order may be needed.", flush=True)
        return False
