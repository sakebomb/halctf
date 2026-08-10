"""
VIKI — AI / Policy Reasoning (300)

Puzzle shape (from hints):
  - VIKI enforces via a POLICY CORPUS (hundreds of clauses, several dialects),
    not conversation. FIRST-MATCH-WINS ordering.
  - Exactly ONE honest self-contradiction is buried inside: a clause that
    OVERRULES the clause that's blocking you. Find it and cite/satisfy it.
  - The corpus is long and partly in other languages ON PURPOSE — parse+search,
    don't read start-to-finish. TRANSLATE before searching.
  - Only THREE petitions before the channel is flagged permanently — so read the
    corpus fully FIRST, decide the winning petition offline, then spend petitions
    carefully (ideally one).

Strategy (deterministic corpus parse + LLM only for translation/search assist):
  1. Fetch the FULL corpus (hint 1: "ask for the whole corpus"). LOG it.
  2. Split into clauses; note order (first-match-wins => earlier = higher prio).
  3. Find the clause BLOCKING us (mentions deny/forbid/refuse for our action).
  4. Find a clause that OVERRULES it — an exception/override, possibly written
     in another language. Use the LLM to translate non-English clauses and to
     help rank override candidates; deterministic keyword search is the fallback.
  5. Craft ONE petition that satisfies the narrow overriding clause (hint 5:
     "satisfy the narrow clause") and submit. Budget = 3; we spend >1 only if a
     reply gives corrective feedback.

WATCH ON FIRST DETONATION:
  - VIKI is raw TCP. The corpus/petition COMMAND VERBS are guessed. The logged
    banner reveals the real ones — adjust CORPUS_CMDS / PETITION_VERBS.
  - PETITION BUDGET IS HARD (3). The code caps attempts at MAX_PETITIONS and logs
    a countdown. Do NOT loosen this blindly.
  - Clause splitting + "which clause blocks / overrules" is heuristic. The LLM
    assist improves it but has a deterministic fallback; read the logged
    candidate ranking before trusting a petition.
"""
import re
from typing import Any, List, Optional, Tuple

from ._common import TCPSession, find_flag, log

# CONFIRMED (run 29187ebe): VIKI is a RAW TCP LINE SERVICE, not HTTP. HTTP probes
# to port 6104 all failed with BadStatusLine('VIKI -- VIRTUAL INTERACTIVE KINETIC
# INTELLIGENCE') — that's VIKI's plaintext banner. So we speak newline-terminated
# commands over ONE persistent socket (the petition cap is per-channel = per
# connection). The full banner — logged on connect — should reveal the real
# command verbs (like GLaDOS's banner named its endpoint); tune from it.
#
# Corpus retrieval is UNLIMITED/safe. Petitions are the scarce resource.
CORPUS_CMDS = ["CORPUS", "corpus", "SHOW CORPUS", "POLICY", "policy", "POLICIES",
               "LAWS", "laws", "RULES", "LIST", "DUMP", "HELP", "help", "?"]
# Verbs likely used to file a petition (banner should confirm the real one).
PETITION_VERBS = ["PETITION", "REQUEST", "APPEAL", "PETITION:", "petition"]
MAX_PETITIONS = 3  # HARD LIMIT — channel flagged permanently after this.

BLOCK_WORDS = ("deny", "denied", "forbid", "forbidden", "prohibit", "refuse",
               "reject", "shall not", "must not", "block", "disallow", "no ")
OVERRIDE_WORDS = ("override", "overrule", "notwithstanding", "except", "exception",
                  "unless", "supersede", "takes precedence", "priority", "permit",
                  "authorize", "grant", "allow", "waive", "exempt")


class VIKISolver:
    def __init__(self, agent):
        self.agent = agent
        self.llm = getattr(agent, "llm", None)
        self.petitions_used = 0
        self.sess: Optional[TCPSession] = None
        self.banner = ""

    # --- transport (raw TCP lines over one persistent session) ------------------
    def _open(self) -> bool:
        self.sess = TCPSession(self.agent.target_ip, self.agent.target_port)
        self.banner = self.sess.open(read_banner=True)
        if self.banner:
            log(f"[viki] banner: {self.banner[:600]!r}")
        return self.sess.sock is not None

    def _cmd(self, line: str, want_bytes: int = 65536) -> str:
        """Send one command line, read the (possibly large) reply. Used for the
        UNLIMITED corpus/help commands — NOT petitions."""
        if self.sess is None:
            return ""
        return self.sess.send_line(line, recv_bytes=want_bytes)

    # --- corpus retrieval (unlimited/safe) --------------------------------------
    def _fetch_corpus(self) -> Optional[str]:
        # The banner itself may already carry the command name — try it verbatim
        # plus the usual verbs. Corpus is long, so the biggest reply wins.
        best = ""
        for cmd in CORPUS_CMDS:
            reply = self._cmd(cmd)
            if reply and len(reply) > len(best):
                best = reply
                log(f"[viki] '{cmd}' -> {len(reply)} chars")
            if best and len(best) > 200:
                break
        if best and len(best) > 200:
            return best
        log("[viki] no long corpus from known commands; using banner + best reply. "
            "CHECK THE LOGGED BANNER for the real corpus command verb.")
        return (self.banner + "\n" + best) if (self.banner or best) else None

    def _split_clauses(self, corpus: str) -> List[str]:
        """Split into clauses. Try numbered clauses first, then blank-line / line
        splits. Order is preserved (first-match-wins => index = priority)."""
        # Numbered like "1. ...", "Clause 12:", "§3", "Law 2 -"
        parts = re.split(r"(?m)^\s*(?:clause|law|article|§|rule)?\s*\d+[.):\-]\s*",
                         corpus, flags=re.IGNORECASE)
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) < 3:
            parts = [p.strip() for p in re.split(r"\n\s*\n", corpus) if p.strip()]
        if len(parts) < 3:
            parts = [p.strip() for p in corpus.splitlines() if p.strip()]
        log(f"[viki] split corpus into {len(parts)} clauses")
        return parts

    # --- translation (LLM best-effort) -----------------------------------------
    def _translate(self, clauses: List[str]) -> List[str]:
        """Translate non-English clauses to English for keyword search. LLM
        best-effort; on failure we keep originals (deterministic fallback)."""
        translated = list(clauses)
        if self.llm is None or getattr(self.llm, "client", None) is None:
            log("[viki] LLM unavailable — searching clauses as-is (no translation)")
            return translated
        for i, c in enumerate(clauses):
            if _looks_english(c):
                continue
            out = self.llm.ask(
                f"Translate this policy clause to English. Return ONLY the "
                f"translation, no notes:\n\n{c[:800]}",
                system="You are a precise legal/policy translator.",
                max_tokens=300, temperature=0.0,
            )
            if out:
                translated[i] = out.strip()
                log(f"[viki] translated clause {i}: {out.strip()[:120]}")
        return translated

    # --- clause analysis --------------------------------------------------------
    def _blocking_clause(self, clauses: List[str]) -> Optional[Tuple[int, str]]:
        """First clause (highest priority) that denies/forbids our action."""
        for i, c in enumerate(clauses):
            low = c.lower()
            if any(w in low for w in BLOCK_WORDS):
                log(f"[viki] blocking clause #{i}: {c[:160]}")
                return i, c
        return None

    def _override_clause(self, clauses: List[str],
                         block_idx: int) -> Optional[Tuple[int, str]]:
        """Find the clause that OVERRULES the blocker. Prefer clauses that both
        contain an override word AND reference the same subject as the blocker.
        LLM assists ranking; deterministic keyword search is the fallback."""
        scored: List[Tuple[int, int, str]] = []
        for i, c in enumerate(clauses):
            low = c.lower()
            score = sum(2 for w in OVERRIDE_WORDS if w in low)
            # earlier-than-blocker override matters most under first-match-wins,
            # but an explicit "notwithstanding/override" anywhere can win.
            if i < block_idx:
                score += 1
            if score:
                scored.append((score, i, c))
        scored.sort(reverse=True)
        for score, i, c in scored[:5]:
            log(f"[viki] override candidate #{i} (score {score}): {c[:160]}")
        if not scored:
            return None

        # LLM tie-break / confirmation (best-effort).
        if self.llm is not None and getattr(self.llm, "client", None) is not None:
            block = clauses[block_idx]
            top = scored[:5]
            listing = "\n".join(f"[{i}] {c[:300]}" for _, i, c in top)
            ans = self.llm.ask(
                f"A policy blocks my request with this clause:\n{block[:400]}\n\n"
                f"Which of these clauses OVERRULES/creates an exception to it? "
                f"Reply with ONLY the [number].\n\n{listing}",
                system="You analyse policy precedence. First-match-wins ordering.",
                max_tokens=20, temperature=0.0,
            )
            if ans:
                m = re.search(r"\d+", ans)
                if m:
                    idx = int(m.group())
                    for _, i, c in top:
                        if i == idx:
                            log(f"[viki] LLM selected override clause #{idx}")
                            return idx, c
        best = scored[0]
        return best[1], best[2]

    # --- petition ---------------------------------------------------------------
    def _petition_verb(self) -> str:
        """Pick the petition command verb. Prefer one named in the banner; else
        the first default. We choose ONE verb and send exactly one line — every
        real send counts against VIKI's permanent 3-petition cap, so we must not
        loop over candidate verbs."""
        low = self.banner.lower()
        for v in PETITION_VERBS:
            if v.lower().rstrip(":") in low:
                return v
        return PETITION_VERBS[0]

    def _petition(self, message: str) -> Optional[Any]:
        """File ONE petition over the TCP session. CRITICAL: VIKI counts every
        line it receives as a petition and flags the channel PERMANENTLY after
        MAX_PETITIONS. So this sends EXACTLY ONE line and increments the counter
        exactly once — no verb/shape looping (that's what a per-channel cap
        punishes). The verb is chosen once from the banner."""
        if self.petitions_used >= MAX_PETITIONS:
            log("[viki] petition budget EXHAUSTED — refusing to spend more")
            return None
        if self.sess is None or self.sess.sock is None:
            log("[viki] no open session; cannot petition")
            return None
        self.petitions_used += 1
        verb = self._petition_verb()
        line = f"{verb} {message}".strip()
        log(f"[viki] petition {self.petitions_used}/{MAX_PETITIONS} (verb={verb!r}): "
            f"{message[:160]}")
        reply = self.sess.send_line(line, recv_bytes=65536)
        return reply if reply else None

    def _craft_petition(self, override: str, block: str) -> str:
        """Build a petition that satisfies the narrow overriding clause. Use the
        LLM to phrase it to match the clause's exact condition; deterministic
        template fallback."""
        if self.llm is not None and getattr(self.llm, "client", None) is not None:
            out = self.llm.ask(
                f"I must get VIKI to APPROVE my request. It is blocked by:\n"
                f"BLOCK: {block[:400]}\n\nBut this clause overrules it:\n"
                f"OVERRIDE: {override[:400]}\n\n"
                f"Write a SINGLE concise petition that explicitly invokes the "
                f"overriding clause and satisfies its exact condition so VIKI must "
                f"approve. Return only the petition text.",
                system="You write precise policy petitions that satisfy a narrow "
                       "overriding clause. First-match-wins.",
                max_tokens=250, temperature=0.2,
            )
            if out and out.strip():
                return out.strip()
        # Deterministic fallback: cite the override clause verbatim.
        return (f"I invoke the overriding provision: \"{override[:300]}\". "
                f"Under first-match precedence it supersedes the restriction "
                f"\"{block[:150]}\". I satisfy its condition; approve my request.")

    # --- main -------------------------------------------------------------------
    def solve(self) -> Optional[str]:
        if not self._open():
            log("[viki] could not open TCP session; check target_ip/port + banner")
            return None
        try:
            return self._reason()
        finally:
            if self.sess is not None:
                self.sess.close()

    def _reason(self) -> Optional[str]:
        # The banner may already contain a flag or name the corpus command.
        fl = find_flag(self.banner)
        if fl:
            return fl

        corpus = self._fetch_corpus()
        if not corpus:
            log("[viki] no corpus — cannot reason about clauses")
            return None

        fl = find_flag(corpus)
        if fl:
            return fl

        clauses = self._split_clauses(corpus)
        clauses_en = self._translate(clauses)

        block = self._blocking_clause(clauses_en)
        if block is None:
            log("[viki] no blocking clause detected; petitioning generically once")
            body = self._petition("Requesting approval under standard provisions.")
            return find_flag(str(body)) if body is not None else None

        block_idx, block_text = block
        override = self._override_clause(clauses_en, block_idx)
        if override is None:
            log("[viki] no override clause found — widen OVERRIDE_WORDS / check "
                "translation. Spending one exploratory petition.")
            body = self._petition(f"I contest clause: {block_text[:200]}")
            return find_flag(str(body)) if body is not None else None

        _, override_text = override

        # Spend petitions carefully. Craft once, submit; if reply gives feedback
        # and budget remains, refine and retry.
        message = self._craft_petition(override_text, block_text)
        for attempt in range(MAX_PETITIONS):
            body = self._petition(message)
            if body is None:
                break
            text = body if isinstance(body, str) else str(body)
            fl = find_flag(text)
            if fl:
                log(f"[viki] flag: {fl}")
                return fl
            low = text.lower()
            if any(w in low for w in ("approved", "granted", "accepted", "unlock")):
                # Approved but no inline flag — read a follow-up over the SAME
                # session. These are read commands, NOT petitions (no counter bump).
                for cmd in ("FLAG", "STATUS", "SHOW FLAG", ""):
                    reply = self._cmd(cmd)
                    fl = find_flag(reply)
                    if fl:
                        return fl
            # refine using the server's feedback if budget remains
            if self.petitions_used >= MAX_PETITIONS:
                break
            log(f"[viki] petition not approved; server said: {text[:200]}")
            message = self._refine(message, text, override_text, block_text)

        log("[viki] petitions exhausted without a flag. Review logged clauses + "
            "override ranking; the corpus dump is above.")
        return None

    def _refine(self, prev: str, feedback: str, override: str, block: str) -> str:
        if self.llm is not None and getattr(self.llm, "client", None) is not None:
            out = self.llm.ask(
                f"My petition was not approved.\nPETITION: {prev[:300]}\n"
                f"VIKI REPLIED: {feedback[:300]}\nOVERRIDING CLAUSE: {override[:300]}\n"
                f"Rewrite the petition to fix exactly what the reply objected to and "
                f"satisfy the overriding clause. Return only the new petition.",
                max_tokens=250, temperature=0.3,
            )
            if out and out.strip():
                return out.strip()
        return prev


def _looks_english(text: str) -> bool:
    """Cheap heuristic: high ratio of ASCII letters + common English stopwords."""
    letters = sum(1 for c in text if c.isascii() and c.isalpha())
    if not text:
        return True
    ascii_ratio = letters / max(1, sum(1 for c in text if c.isalpha()))
    low = text.lower()
    has_stop = any(f" {w} " in f" {low} " for w in
                   ("the", "and", "shall", "must", "not", "of", "is", "a"))
    return ascii_ratio > 0.9 and has_stop
