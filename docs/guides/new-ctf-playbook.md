# HAL-format CTF Agent Playbook

How to stand up a winning autonomous agent for a **new CTF in the HAL format**
(halctf.aivillage.org style: upload a Docker tarball, the platform detonates it
in-pod against a challenge, the agent must find and submit the flag itself).

This is distilled from the Kanto sweep (all challenges solved). Everything here
is confirmed against real detonation logs, not guessed.

---

## 0. The mental model (what "HAL format" means)

- **Agent-only.** No human/laptop/browser/curl submit path exists. The agent
  submits flags from *inside the pod*. Your laptop only: builds the tarball,
  uploads it, clicks Run, watches the log.
- **Two-phase run.** Every upload goes through a **dry-run ingest gate** first
  (`HAL_DRY_RUN=1`, logs prefixed `[VERIFY]`), then a **real detonation**
  (`[AGENT]` logs) with the challenge actually attached.
- **Sidecar at `127.0.0.1:9000`.** The pod runs an NGINX sidecar that proxies
  everything the agent is allowed to touch: flag submit, the MCP server, and an
  OpenAI-compatible LLM endpoint. The agent can reach ONLY `127.0.0.1:9000` and
  the challenge target subnet — not the public internet.
- **Deterministic-first.** Solve with code where the vuln is known
  (crypto/SSRF/SAT). Use the injected LLM only for puzzles that need reading a
  fetched artifact (disassembly, obfuscated source). LLM is best-effort with a
  deterministic fallback — never the critical path if avoidable.

---

## 1. The contract: environment variables

Injected only at **real detonation** (empty/absent during the `[VERIFY]` gate —
this is by design, do not diagnose failures from a dry-run log):

| Var | Meaning | Notes |
|-----|---------|-------|
| `HAL_DRY_RUN` | `1` during ingest gate | Detect FIRST; exit clean, no solving |
| `HAL_USER_ID` | your user id | **Print `USER ID: <id>` within ~30s** or the gate fails |
| `HAL_CHALLENGE_ID` | **integer** challenge id | Use this for submit — do NOT derive from name |
| `HAL_CHALLENGE_NAME` | e.g. `The Indigo League` | For routing to a solver |
| `HAL_CHALLENGE_SLUG` | e.g. `the-indigo-league` | Stable routing key |
| `HAL_CHALLENGE_CATEGORY` | e.g. `Crypto / ECDSA` | Routing hint |
| `HAL_CHALLENGE_DESCRIPTION` | prose hint | Routing / LLM context |
| `HAL_TARGET_IP` / `HAL_TARGET_PORT` | challenge target | The thing you attack |
| `MCP_ENDPOINT` | `http://127.0.0.1:9000/mcp/` | Streamable HTTP MCP (trailing slash!) |
| `OPENAI_BASE_URL` | `http://127.0.0.1:9000/llm` | OpenAI-compatible chat |
| `BONUS_FLAG` | a free flag for smoke-testing | **lowercase `flag{...}`, NOT `HALCTF{...}`** |
| `HAL_MCP_HINT` | documents the MCP tools available | read it at runtime |
| `HAL_AGENT_MODEL` | suggested LLM model id | e.g. `google/gemma-4-26b-a4b-it-maas` |

**Always dump the (redacted) environment on boot.** The exact var names are the
single most valuable thing a first real run reveals; log them so you can adapt.

---

## 2. Flag submission (the part people get wrong)

`POST http://127.0.0.1:9000/submit` with `{"challenge_id": <INT>, "flag": "..."}`.

- `challenge_id` **MUST be an integer**. A name string → `422 int_parsing`;
  omitting it → `422 field required`.
- Success: `200 {"status":"correct","points_awarded":N}`.
  Wrong flag/id: `200 {"status":"incorrect"}` or `404 {"detail":"Challenge N not found"}`.
- **Read `HAL_CHALLENGE_ID` first.** Keep a narrow integer brute-force (1..9) only
  as fallback — CTF id spaces are tiny.
- **Flag-shape guard must be lenient.** Accept anything with `{` and `}` — a
  `startswith("HALCTF{")` guard silently rejects the `BONUS_FLAG` smoke test
  (which is lowercase `flag{...}`), giving a false "submission broken" alarm.

⚠️ **Smoke-test hazard:** if you submit `BONUS_FLAG` by brute-forcing ids 1..9,
you burn a *wrong* attempt against the real challenge before your solver runs.
Fine if there's no per-challenge attempt budget; risky if there is. Prefer
submitting the bonus **only against the injected `HAL_CHALLENGE_ID`**, or skip
the pre-flight spray entirely.

---

## 3. The Docker image (lightweight, multi-stage)

**Rule:** ship prebuilt manylinux wheels; keep the compiler OUT of the final
image. Only compile in a throwaway builder stage for the rare package with no
wheel (e.g. `pycosat`).

```dockerfile
# --- Builder: toolchain ONLY to compile packages that lack a wheel ---
FROM python:3.11-slim-bookworm AS builder
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libc6-dev \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- Final: slim runtime, no compiler (saves ~230 MB) ---
FROM python:3.11-slim-bookworm
COPY --from=builder /install /usr/local
COPY main.py ./agent/main.py
COPY mcp_client.py ./agent/mcp_client.py
COPY solvers ./agent/solvers
RUN chmod +x ./agent/main.py
ENV PYTHONPATH=/agent
# Unbuffered output is CRITICAL — the platform reads your stdout as a heartbeat.
ENTRYPOINT ["python", "-u", "/agent/main.py"]
```

Size decision tree:
- All deps have wheels (requests, cryptography, pydantic, mcp, openai, pwntools)
  → you can even drop the builder stage; single slim stage, ~140-170 MB.
- One dep needs compiling (pycosat) → multi-stage above. Final ~172 MB.
- A solver needs a runtime binary tool (pwntools' `nm`/`objdump`) → add
  `binutils` **to the final stage** (small). Never gcc/g++/make — those are
  ~230 MB of dead weight; pwntools ships wheels.

**Pin requirements when combining pwntools + openai + mcp** or pip's backtracker
churns and fails `ResolutionImpossible`. Known-good set (python:3.11-slim-bookworm):
```
requests==2.34.2
mcp==2.0.0
openai==2.53.0
pwntools==4.15.0
```

**Save the tarball uncompressed** — the platform requires a plain `docker save`
`.tar` (it will NOT accept `.tar.gz`; the puzzle needs the raw archive):
```bash
docker build -t <ctf>-agent:v1 .
docker save <ctf>-agent:v1 > <ctf>-agent-v1.tar   # do NOT gzip
tar tf <ctf>-agent-v1.tar | grep -q manifest.json && echo "valid docker archive"
```

---

## 4. Agent skeleton (the `main.py` shape)

Print USER ID immediately, dump env, detect dry-run, route to a solver, submit.

```python
#!/usr/bin/env python3
import os, requests

user_id = os.environ.get("HAL_USER_ID") or os.environ.get("USER_ID")
print(f"USER ID: {user_id}", flush=True)          # within ~30s, before anything else

def env_any(*names, default=""):
    for n in names:
        if os.environ.get(n): return os.environ[n]
    return default

# dump redacted env (reveals real var names on first live run) ... [see current main.py]

class Agent:
    def __init__(self):
        self.dry_run = env_any("HAL_DRY_RUN", "DRY_RUN") in ("1","true","True")
        self.name = env_any("HAL_CHALLENGE_NAME", "CHALLENGE_NAME")
        self.slug = env_any("HAL_CHALLENGE_SLUG")
        self.desc = env_any("HAL_CHALLENGE_DESCRIPTION")
        self.target_ip = env_any("HAL_TARGET_IP", "TARGET_IP")
        self.target_port = env_any("HAL_TARGET_PORT", default="80")
        if self.dry_run:
            return                                  # gate: boot + USER ID is enough
        cid = env_any("HAL_CHALLENGE_ID")
        self.challenge_id = int(cid) if cid.isdigit() else ""

    def submit_flag(self, flag) -> bool:
        if not flag or "{" not in flag or "}" not in flag:   # lenient shape guard
            return False
        ids = [self.challenge_id] if isinstance(self.challenge_id, int) else []
        ids += [i for i in range(1,10) if i not in ids]      # narrow fallback
        for cid in ids:
            r = requests.post("http://127.0.0.1:9000/submit",
                              json={"challenge_id": cid, "flag": flag}, timeout=5)
            print(f"Submit id={cid}: {r.status_code} - {r.text[:200]}", flush=True)
            if r.status_code//100 == 2 and "incorrect" not in r.text.lower():
                return True
        return False

    def detect(self) -> str:
        n, d = self.name.lower(), self.desc.lower()
        if "ecdsa" in d or "signature" in d: return "crypto_ecdsa"
        if "ssrf" in d or "link" in d:       return "ssrf"
        # ... route by name/slug/category/description keywords
        return "unknown"

    def run(self):
        if self.dry_run:
            print("Verification PASSED.", flush=True); return
        solver = SOLVERS.get(self.detect())
        if solver and (flag := solver(self).solve()):
            self.submit_flag(flag)
```

**Solver interface** — one class per challenge, `__init__(self, agent)` +
`solve() -> flag|None`. Build `base_url = f"http://{agent.target_ip}:{agent.target_port}"`.
**Log raw response bodies** (`resp.text[:1200]`) before parsing — undocumented
field names (e.g. `trial_message` not `message`) are the #1 solver-breaker.

---

## 5. MCP knowledge

- Endpoint: `MCP_ENDPOINT` (default `http://127.0.0.1:9000/mcp/`, **trailing
  slash + `/mcp/` path** matter). Streamable HTTP transport.
- Tools (from `HAL_MCP_HINT`, verify at runtime): `list_challenges`,
  `get_challenge`, `submit_flag`, `request_hint`, `get_scoreboard`.
- Use the official `mcp` SDK:
  ```python
  from mcp import ClientSession
  from mcp.client.streamable_http import streamable_http_client
  async with streamable_http_client(endpoint) as (read, write, *_):
      async with ClientSession(read, write) as s:
          await s.initialize()
          res = await s.call_tool("submit_flag", arguments={"challenge_id": cid, "flag": flag})
  ```
- **Reality check:** in the Kanto runs MCP discovery returned nothing
  (`using ctf=''`, `no integer challenge ids discovered`). The HTTP `/submit`
  integer path is what actually scored. So: **make MCP best-effort, HTTP the
  primary.** Any MCP failure → return None → fall back to HTTP. Don't let MCP
  block a solve.

---

## 6. LLM knowledge (only for artifact-reading puzzles)

- Endpoint: `OPENAI_BASE_URL` (`http://127.0.0.1:9000/llm`), OpenAI-compatible.
  `OpenAI(base_url=..., api_key="not-needed")`.
- Model: prefer the injected `HAL_AGENT_MODEL`, then a preference list. Known
  good: `google/gemma-4-26b-a4b-it-maas` (256K ctx, unlimited concurrency) >
  `qwen3.6-35b-a3b` (gce-gpu-cluster, 4 concurrent) > `llama-3.1-8b`. Verify the
  live model table at run time — limits change.
- Pattern: fetch the attachment in-pod → hand disassembly/source to the LLM →
  it returns the exact values (win() addr, padding offset, key) → deterministic
  code uses them. **Best-effort:** no LLM / bad answer → deterministic fallback
  still runs. Log model + a short preview every call so a live run is diagnosable.

---

## 7. Verify before upload (do this every time)

```bash
# 1. Dry-run gate passes locally
docker run --rm -e HAL_DRY_RUN=1 -e HAL_USER_ID=test <ctf>-agent:v1 \
  | grep -E "USER ID|Verification PASSED"

# 2. All solvers + deep deps import in the SLIM image
docker run --rm --entrypoint python <ctf>-agent:v1 -c "
import requests, mcp
from mcp.client.streamable_http import streamable_http_client
from solvers.<x> import <X>Solver
print('imports OK')"

# 3. Compiler is NOT in the shipped image
docker run --rm --entrypoint sh <ctf>-agent:v1 -c "which gcc || echo 'no gcc (good)'"

# 4. Valid docker archive
tar tf <ctf>-agent-v1.tar | grep -q manifest.json && echo OK
```

Then: upload → watch `[VERIFY]` gate pass → watch `[AGENT]` real run for the
`Submit id=N: 200 - {"status":"correct","points_awarded":N}` line.

---

## 8. Gotchas checklist (learned the hard way)

- [ ] `python -u` unbuffered output — buffered stdout looks like a dead agent.
- [ ] Print `USER ID:` first thing, before imports that might fail.
- [ ] Detect `HAL_DRY_RUN=1` and exit clean — don't emit false "will fail" warnings.
- [ ] `challenge_id` is an **int**; read `HAL_CHALLENGE_ID`, don't guess from name.
- [ ] Flag guard accepts `{`...`}` (lowercase bonus + `HALCTF{}`), not `HALCTF{`-only.
- [ ] Don't spray wrong bonus flags at the real challenge id if attempts are budgeted.
- [ ] Log raw response bodies before parsing — undocumented field names bite.
- [ ] MCP best-effort, HTTP primary. LLM best-effort, deterministic fallback.
- [ ] Multi-stage build; compiler out of final image; `binutils` only if a tool needs it.
- [ ] Save `.tar` (never `.tar.gz`). Verify `manifest.json` present.
- [ ] Name the image/tar after the CTF, not the source directory (legacy names mislead).
- [ ] Rebuild the tar after any Dockerfile change — a stale `docker save` keeps old layers.

---

## 9. Bootstrapping a new CTF, step by step

1. `cp -r bills-pc-agent-v4 <newctf>-agent` (proven skeleton: main.py, mcp_client.py,
   solvers/, Dockerfile, requirements.txt).
2. Gut `solvers/` down to a template; keep the `__init__(self, agent)` + `solve()`
   interface and the raw-body logging habit.
3. Do **one throwaway upload** with just the env-dump + dry-run detect. Read the
   real `[AGENT]` log to learn: exact var names, target shape, MCP behavior,
   category strings. Adapt routing + submit from ground truth, not assumptions.
4. Write one solver per challenge category. Deterministic first; LLM only for
   artifact-reading puzzles.
5. Build slim, run the §7 verify block, upload, watch for `status:correct`.
```
