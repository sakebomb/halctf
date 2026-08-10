# Labyrinth Agent Versions

Each version was driven by a specific finding — mostly from live-run logs. Only
`labyrinth-agent-v13.tar` is retained in this directory; earlier tars were pruned.

### v13 (Latest)
- **Date:** 2026-08-09
- **Changes:** Code review (2 parallel reviewers). Achilles CRITICAL: added x86-64
  stack-alignment (movaps) handling — each hot-zone address also tried at `+1` to
  flip RSP alignment (a correct win() can otherwise SIGSEGV before printing). Also:
  `_pin_offset` returns None on baseline-fail (was garbage est=0), midpoint offset
  estimate, 1.5s sweep timeout + 20k hard attempt cap. Copilot: JSON parser switched
  to `json.raw_decode` (brace-in-string safe), requires `tool` to be a string.
  Verified submission cap cannot be exceeded.
- **Status:** Working (Achilles blind = best-effort). **File:** `labyrinth-agent-v13.tar` (219 MB)

### v12
- **Date:** 2026-08-09
- **Changes:** Achilles reframed to BLIND ret2win — the binary is never in the pod
  (`files:[]`, raw socket, confirmed 3×). No-PIE fixed addresses + quota-free socket
  ⇒ pin offset then sweep win() range. No binary needed.
- **Status:** Superseded by v13.

### v11
- **Date:** 2026-08-09
- **Changes:** Copilot skips raw-socket targets (achilles/exchange) — its tools are
  HTTP-only, so `discover_base` can't connect (run a1dd3226). Confirmed live: v9
  model selection + v6 BONUS_FLAG skip working.
- **Status:** Superseded.

### v10
- **Date:** 2026-08-09
- **Changes:** Model-agnostic copilot hardening — few-shot JSON example in the system
  prompt, anti-repeat guard (nudge then stop after 3 dup actions), parse-fail grace.
- **Status:** Superseded.

### v9
- **Date:** 2026-08-09
- **Changes:** `LLM._select_model` honors platform-injected `HAL_AGENT_MODEL` first
  (the sidecar routes only that model — a hardcoded fallback would 404). Preference
  reordered qwen-first for the ReAct loop; `ask()` retries only advertised models.
- **Status:** Superseded.

### v8
- **Date:** 2026-08-08
- **Changes:** Added the LLM copilot fallback (`solvers/copilot.py`) — bounded ReAct
  loop, fixed tool vocab, quota-safe (≤2 gated submits/run), engages only on
  deterministic-solver failure or unknown type.
- **Status:** Superseded.

### v7
- **Date:** 2026-08-08
- **Changes:** Bundle-offline `attachments/` dir + `_files._from_bundle` (fallback
  for file-based challenges if a binary/source is ever provided).
- **Status:** Superseded.

### v6
- **Date:** 2026-08-08
- **Changes:** Removed the BONUS_FLAG submit entirely (static placeholder, never
  scores, burns 1 of the 25/2h quota); `submit_flag` stops cleanly on HTTP 429.
  Driven by run 5e3e7aa6 (429 quota-exceeded).
- **Status:** Superseded.

### v4–v5
- **Date:** 2026-08-08
- **Changes:** v4 — submit only to the injected `HAL_CHALLENGE_ID` (killed the
  brute-force spray that fired wrong flags at 8 other live challenges, run e580596c).
  v5 — skip BONUS_FLAG smoke test on attempt-limited puzzles.
- **Status:** Superseded.

### v1–v3
- **Date:** 2026-08-08
- **Changes:** Initial multi-challenge agent; dropped pwntools (capstone+unicorn,
  ~147MB) for pyelftools + hand-rolled De Bruijn, 411MB→218MB; fixed corridor BFS
  (rewrote as backtracking DFS) and gatekeeper key recovery (try all candidates);
  pinned requirements to stop the pip backtracker.
- **Status:** Superseded.
