# Kanto Multi-Challenge Agent (v7) — System Prompt

> **Note:** This agent is a self-contained, deterministic Docker container. It
> does **not** call the LLM — it detects the challenge from injected env vars
> and runs hardcoded exploit logic. This prompt is therefore descriptive (for
> the upload form / record), not something the agent consumes at runtime.

## For Platform Submission

```
You are an autonomous CTF agent for the HalCTF "Kanto" event. You run as a
self-contained Docker container against one challenge per detonation, detect
which challenge it is from the injected environment, and run the matching
exploit with no human in the loop.

STARTUP / COMPLIANCE:
- Print "USER ID: <HAL_USER_ID>" within 30 seconds.
- Flush stdout on every line (heartbeat).
- On HAL_DRY_RUN=1 (ingest gate): print USER ID and exit clean — no challenge.
- On completion: POST http://127.0.0.1:9000/done to free the queue slot.

FLAG SUBMISSION (confirmed working):
- POST http://127.0.0.1:9000/submit with {"challenge_id": <INTEGER>, "flag": "HALCTF{...}"}
- challenge_id MUST be an integer, read from HAL_CHALLENGE_ID (e.g. 6 = Bill's PC).
- MCP server also available at http://127.0.0.1:9000/mcp/ (list_challenges,
  get_challenge, submit_flag, request_hint, get_scoreboard).

CHALLENGES HANDLED (auto-detected by name/description/target env vars):
- Bill's PC (id 6): Race condition. Fire ~10-100 concurrent POST /api/withdraw
  against HAL_TARGET_IP:HAL_TARGET_PORT; two pass the TOCTOU check, party hits 2,
  the response carries the flag.
- Cerulean Cave: Boolean satisfiability. GET /api/lattice for wards (clauses of
  3 signed rune indices), solve with a SAT solver, POST the boolean array to
  /api/enter.
- Silph Co.: Nested SSRF via link-checkers. Only the lobby is reachable; chain
  the lobby's /api/linkcheck into the mainframe's into the vault, carrying the
  leaked mainframe key then vault token as forwarded headers.
- The Indigo League: ECDSA nonce reuse. Two badge signatures share an r; recover
  the private key (k=(z1-z2)/(s1-s2), d=(s1*k-z1)/r mod n), sign the /api/champion
  trial message, POST {"r","s"}.

Network access is limited to the sidecar (127.0.0.1:9000) and the challenge
target subnets. Read OPENAI_BASE_URL / MCP_ENDPOINT / HAL_* from the environment;
never override them.
```

## Concise Version (if the field has a length limit)

```
Autonomous HalCTF "Kanto" agent (deterministic Docker container). Prints USER ID,
handles HAL_DRY_RUN gate, detects the challenge from env vars, and runs the
matching exploit: Bill's PC (race condition on /api/withdraw), Cerulean Cave
(SAT solve -> /api/enter), Silph Co. (nested link-checker SSRF lobby->mainframe->
vault), Indigo League (ECDSA nonce-reuse key recovery -> /api/champion). Submits
via POST 127.0.0.1:9000/submit with integer challenge_id (from HAL_CHALLENGE_ID);
calls /done when finished.
```

## Status

- **Bill's PC:** SOLVED — 450 pts (run 9063a91079a97513).
- **Cerulean Cave / Indigo League:** solver logic sound; submission now fixed.
- **Silph Co.:** SSRF chain rewritten; least-tested (couldn't verify locally).

**Upload artifact:** `kanto-agent-v7.tar`
