# HAL-format CTF agent template

A clean, proven skeleton for building an autonomous agent for a HAL-format CTF
(halctf.aivillage.org style). Distilled from the Kanto sweep + Labyrinth build.
Read `../NEW_CTF_PLAYBOOK.md` for the full process and gotchas.

## Files
- `main.py`        — generic harness: USER ID, env dump, dry-run gate, submit
                     pipeline (HTTP primary + MCP fallback + narrow brute-force),
                     data-driven solver registry + keyword routing.
- `llm.py`         — LLM wrapper for `OPENAI_BASE_URL`. `ask()` single-shot,
                     `chat()` multi-turn. Best-effort; degrades to deterministic.
- `mcp_client.py`  — MCP submit + generic tool call. Best-effort fallback.
- `solvers/`       — one module per challenge. `example.py` shows the contract.
- `requirements.txt` / `Dockerfile` / `build.sh` — lightweight image + upload.

## Adapt for a new CTF
1. `cp -r ctf-agent-template <ctf>-agent`
2. For each challenge, copy `solvers/example.py` -> `solvers/<name>.py`, implement
   `solve()`. Deterministic first; use `self.agent.llm` only for reasoning puzzles.
3. In `main.py`: import your solvers, fill `SOLVERS = {name: Class}`, and add
   routing keywords to `detect_challenge()`. Set `BRUTE_FORCE_MAX` = #challenges+margin.
4. Build + verify:
   ```bash
   ./build.sh <ctf>-agent v1
   # then the §7 checks in the playbook (imports, no gcc, manifest.json)
   ```
5. Upload the `.tar`, watch the `[VERIFY]` gate pass, then the `[AGENT]` run for
   `Submit ...: 200 - {"status":"correct","points_awarded":N}`.

## The rules that matter (see playbook for why)
- Print `USER ID:` first; run with `python -u` (heartbeat).
- Detect `HAL_DRY_RUN=1` and exit clean — don't emit false warnings.
- `challenge_id` is an **integer** from `HAL_CHALLENGE_ID`.
- Flag guard is lenient (`{` and `}`) so the lowercase `BONUS_FLAG` passes.
- Don't spray wrong bonus flags at the real challenge id.
- Log raw response bodies before parsing.
- MCP best-effort, HTTP primary. LLM best-effort, deterministic fallback.
- Ship a slim image (no compiler); save an uncompressed `.tar`.
