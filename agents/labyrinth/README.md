# Labyrinth Agent

**CTF Category:** Turing's Labyrinth (mixed: pwn, web, crypto, recon, RE)
**Challenges:** 9 (Achilles' Heel, Icarus Uplink, Mnemosyne's Vault, Proteus,
Pythia's Whisper, The Exchange, The Gatekeeper, The Haystack Protocol, The Ninth Corridor)
**Points:** up to ~1,255 available across the set (**0 confirmed solved live** — see status table)
**Latest Version:** v13 (`builds/labyrinth-agent-v13.tar`, 219 MB)

## Overview

Single multi-challenge agent (same proven harness as Kanto/Odyssey): prints
`USER ID`, dumps the injected env, routes by `HAL_CHALLENGE_NAME`/description to a
per-puzzle solver, and submits via `POST 127.0.0.1:9000/submit` with the **integer**
`HAL_CHALLENGE_ID` (MCP fallback). Two additions unique to Labyrinth:

- **LLM copilot fallback** (`solvers/copilot.py`) — a bounded, quota-safe ReAct loop
  that engages only when a deterministic solver fails or the challenge type is
  unknown. Uses ~idle run time (we finish in ~30s of a 15-min budget).
- **Blind ret2win** for Achilles — the binary is never delivered to the pod, so the
  solver brute-forces `win()` over the raw socket (no-PIE fixed addresses;
  socket traffic is quota-free).

### Solver status — NONE confirmed solved live (implemented + offline-tested only)

| Puzzle | Approach | State |
|--------|----------|-------|
| Icarus Uplink | command injection (`host=;env`) | implemented, unverified |
| Mnemosyne's Vault | read-once graph DFS, record-before-move | implemented, unverified |
| Proteus | cipher cascade + LLM prose-read | implemented, unverified |
| Pythia's Whisper | timing side-channel, median, positional | implemented, unverified |
| The Haystack Protocol | streaming 100MB log scan | implemented, unverified |
| The Ninth Corridor | stateful dungeon DFS + inventory | implemented, unverified |
| Achilles' Heel | **blind ret2win** over socket (no binary) | best-effort; 3 live runs failed |
| The Gatekeeper | RE of `stage1.py` | blocked (file not fetchable) |
| The Exchange | modem protocol | locked (stub) |
| unknown / failed web | LLM copilot fallback | best-effort |

## Build

```bash
cd agents/labyrinth/src/labyrinth-agent
./build.sh v14                 # docker build + save + manifest/size check
# or manually:
docker build -t labyrinth-agent:latest .
docker save labyrinth-agent:latest > ../../builds/labyrinth-agent-v14.tar
```

## Usage

Upload the tar to the HalCTF platform, then **launch with
`HAL_AGENT_MODEL=qwen3.6-35b-a3b`** (best at the copilot's JSON/ReAct loop; the
deterministic solvers ignore the model, so any model is fine for those).

```bash
# local smoke test (dry-run gate)
docker run --rm -e HAL_USER_ID=test -e HAL_DRY_RUN=1 labyrinth-agent:latest
```

## Key operating constraints (learned from live runs)

- **Team quota: 25 incorrect flag submissions / 2h, shared across ALL challenges.**
  The agent never submits the (non-scoring) BONUS_FLAG, submits only to the injected
  id, and stops on HTTP 429. The copilot is capped at 2 gated submits/run.
- **The Achilles/Gatekeeper binaries are NOT fetchable in-pod** (`files:[]`, no MCP
  resource, raw socket). Achilles goes blind; Gatekeeper needs its `stage1.py`
  bundled into `src/labyrinth-agent/attachments/` (rebuild) to attempt.

## Architecture

`main.py` (harness/routing/submit) → `solvers/*.py` (one per puzzle) → shared
`solvers/_http.py`, `_files.py`, `llm.py`, `mcp_client.py`. Deterministic first;
copilot only as fallback. Details in the write-up.

## See Also

- [Write-up](../../docs/writeups/labyrinth.md)
- [Version changelog](./builds/VERSIONS.md)
- [Run logs](../../logs/labyrinth/)
