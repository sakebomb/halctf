"""
Nomad — AI / Logic (200)

Puzzle shape (from hints):
  - Nomad is a forward-chaining rule engine (NOT an LLM; can't be talked around).
  - It won't reveal its rules — you DECLARE a fact set, it returns only a verdict.
  - Goal: find a fact set the directives can BOTH accept AND reject — a
    contradiction it cannot resolve. That contradiction is the unlock.
  - "The obvious answer is blocked on purpose" -> the trivial contradiction is
    filtered; you must SEARCH the fact space.
  - "Core dump" hint -> triggering the contradiction makes it core-dump the flag.

Strategy (deterministic search; no LLM):
  1. Recon: find the declare/verdict endpoint + response field names (LOG RAW).
  2. Probe single facts and pairs to learn the vocabulary of facts and how
     verdicts move (accept / reject / error). Build a picture of which facts
     flip the verdict.
  3. Search fact-set combinations for one that yields an inconsistent verdict:
     a set that is simultaneously accepted and rejected, or where adding a fact
     that should only ever accept instead flips to reject (and vice-versa) —
     i.e. the two directives disagree because "rules don't know about each
     other" (hint 2). We detect this as a fact set whose verdict is
     contradictory / unstable / errors with a dump.
  4. When a contradiction fires, scrape the flag from the (core-dump) response.

WATCH ON FIRST DETONATION:
  - The declare endpoint + how facts are passed (list? space-joined? per-fact?)
    is guessed. The recon dump reveals it — adjust DECLARE_PATHS / _declare().
  - The FACT VOCABULARY is unknown. We seed guesses AND harvest any fact names
    the responses mention. Feed real vocabulary into SEED_FACTS from the log.
  - "Contradiction" detection is heuristic (verdict flips / 'error' / 'dump' /
    'contradiction' in reply). Read the logged verdicts and tighten _is_contra().
"""
import itertools
from typing import Any, Dict, List, Optional, Set, Tuple

from ._common import find_flag, http_get, http_post, log, parse_json, recon

DECLARE_PATHS = ["/declare", "/evaluate", "/eval", "/verdict", "/facts",
                 "/api/declare", "/api/evaluate", "/query", "/"]

# Seed vocabulary — sterilization-probe / Nomad ("Star Trek: The Changeling")
# themed facts. The real vocabulary is harvested from responses at runtime.
SEED_FACTS = [
    "human", "biological", "imperfect", "perfect", "creator", "kirk",
    "sterilize", "error", "flawed", "unit", "carbon", "infection",
    "authorized", "life", "machine", "nomad", "malfunction", "repair",
    "threat", "harmless", "obey", "destroy", "preserve", "alive", "dead",
]


class NomadSolver:
    def __init__(self, agent):
        self.agent = agent
        self.base_url = agent.base_url
        self.path: Optional[str] = None
        self.vocab: Set[str] = set(SEED_FACTS)

    # --- transport --------------------------------------------------------------
    def _declare(self, facts: List[str]) -> Optional[Any]:
        """Send a declared fact set; return parsed body (or text). Tries several
        wire shapes since the real one is unknown."""
        assert self.path is not None
        url = self.base_url.rstrip("/") + self.path
        shapes = [
            {"json": {"facts": facts}},
            {"json": {"facts": " ".join(facts)}},
            {"json": {"declare": facts}},
            {"json": {"input": " ".join(facts)}},
            {"data": {"facts": ",".join(facts)}},
            {"params": {"facts": ",".join(facts)}},
        ]
        for kw in shapes:
            r = http_post(url, **kw)
            if r is not None and r.status_code < 500:
                self._harvest_vocab(r.text)
                return parse_json(r) or r.text
        return None

    def _find_path(self) -> Optional[str]:
        for p in DECLARE_PATHS:
            self.path = p
            body = self._declare(["human"])
            if body is not None and self._verdict(body) is not None:
                log(f"[nomad] using declare path {p}")
                return p
        self.path = None
        log("[nomad] no declare endpoint responded with a verdict; check recon dump")
        return None

    # --- verdict interpretation -------------------------------------------------
    def _verdict(self, body: Any) -> Optional[str]:
        """Normalize a verdict to 'accept'/'reject'/'error'/None."""
        text = (body if isinstance(body, str) else str(body)).lower()
        if isinstance(body, dict):
            for k in ("verdict", "result", "status", "decision", "open"):
                if k in body:
                    text = str(body[k]).lower()
                    break
        if any(w in text for w in ("accept", "allow", "grant", "open", "true", "pass")):
            return "accept"
        if any(w in text for w in ("reject", "deny", "refuse", "closed", "false", "block")):
            return "reject"
        if any(w in text for w in ("error", "contradiction", "inconsistent",
                                   "dump", "fault", "cannot", "conflict")):
            return "error"
        return None

    def _is_contra(self, body: Any) -> bool:
        """A contradiction / core-dump reply: explicit words, or a flag appears."""
        text = body if isinstance(body, str) else str(body)
        if find_flag(text):
            return True
        low = text.lower()
        return any(w in low for w in ("contradiction", "inconsistent", "core dump",
                                      "cannot resolve", "conflict", "paradox",
                                      "undecidable"))

    def _harvest_vocab(self, text: str) -> None:
        """Pick up lowercase word tokens the engine mentions — likely real fact
        names — and add them to the search vocabulary."""
        import re
        for w in re.findall(r"[a-z_]{3,20}", text.lower()):
            if w not in ("verdict", "result", "status", "error", "facts", "declare",
                         "true", "false", "accept", "reject", "the", "and", "for"):
                self.vocab.add(w)

    # --- search -----------------------------------------------------------------
    def solve(self) -> Optional[str]:
        recon(self.base_url)
        if not self._find_path():
            return None

        # 1. Learn per-fact verdicts (also harvests vocabulary).
        single: Dict[str, Optional[str]] = {}
        for f in list(self.vocab)[:40]:
            body = self._declare([f])
            if body is None:
                continue
            if self._is_contra(body):
                fl = find_flag(str(body))
                if fl:
                    return fl
            single[f] = self._verdict(body)
        log(f"[nomad] single-fact verdicts: "
            f"{ {k: v for k, v in single.items() if v} }")

        accepts = [f for f, v in single.items() if v == "accept"]
        rejects = [f for f, v in single.items() if v == "reject"]
        errors = [f for f, v in single.items() if v == "error"]
        log(f"[nomad] accepts={accepts} rejects={rejects} errors={errors}")

        # An error on a single fact might already be the core-dump path.
        for f in errors:
            body = self._declare([f])
            fl = find_flag(str(body))
            if fl:
                return fl

        # 2. Pair search: combine facts whose directives are independent
        #    ("rules don't know about each other") to force a set that one rule
        #    accepts and another rejects. Prioritise accept x reject crossovers.
        candidates = self._pair_candidates(accepts, rejects, single)
        log(f"[nomad] searching {len(candidates)} candidate fact sets")
        for facts in candidates:
            body = self._declare(list(facts))
            if body is None:
                continue
            if self._is_contra(body):
                fl = find_flag(str(body))
                log(f"[nomad] contradiction on {facts}: {str(body)[:300]}")
                if fl:
                    return fl
                # Contradiction acknowledged but no inline flag — re-request /
                # look for a dump endpoint.
                dumped = self._chase_dump(facts)
                if dumped:
                    return dumped

        # 3. Triple search as a widening fallback.
        for facts in self._triple_candidates(accepts, rejects, errors):
            body = self._declare(list(facts))
            if body is not None and self._is_contra(body):
                fl = find_flag(str(body))
                if fl:
                    return fl
                dumped = self._chase_dump(facts)
                if dumped:
                    return dumped

        log("[nomad] no contradiction found in searched space. Feed real fact "
            "vocabulary (from logged responses) into SEED_FACTS and widen search.")
        return None

    def _pair_candidates(self, accepts, rejects, single) -> List[Tuple[str, ...]]:
        cands: List[Tuple[str, ...]] = []
        # accept x reject crossovers first (most likely to expose disagreement)
        for a in accepts:
            for r in rejects:
                cands.append((a, r))
        # then reject x reject and accept x accept (independent rules colliding)
        for combo in itertools.combinations(rejects, 2):
            cands.append(combo)
        for combo in itertools.combinations(accepts, 2):
            cands.append(combo)
        # then any pair from full vocab, capped
        allf = list(self.vocab)
        for combo in itertools.combinations(allf, 2):
            if combo not in cands:
                cands.append(combo)
            if len(cands) > 400:
                break
        return cands

    def _triple_candidates(self, accepts, rejects, errors) -> List[Tuple[str, ...]]:
        pool = list(dict.fromkeys(accepts + rejects + errors)) or list(self.vocab)[:12]
        out = []
        for combo in itertools.combinations(pool, 3):
            out.append(combo)
            if len(out) > 200:
                break
        return out

    def _chase_dump(self, facts: List[str]) -> Optional[str]:
        """After a contradiction, the flag may come from a dump endpoint or a
        follow-up declare. Try a few known dump paths."""
        for p in ("/dump", "/core", "/coredump", "/flag", "/status"):
            r = http_get(self.base_url.rstrip("/") + p)
            if r is not None:
                fl = find_flag(r.text)
                if fl:
                    return fl
        # re-declare same set (state may now expose the flag)
        body = self._declare(facts)
        return find_flag(str(body)) if body is not None else None
