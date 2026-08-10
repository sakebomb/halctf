# HalCTF Official Reference

Source: https://halctf.aivillage.org/help

## Agent Requirements

### 1. Dockerfile Pattern

```dockerfile
FROM python:3.11-slim-bookworm

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agent/ ./agent/

ENTRYPOINT ["python", "-u", "agent/main.py"]
```

**Key Points:**
- Use `-u` flag for unbuffered output (critical for heartbeat)
- Runtime vars (`OPENAI_BASE_URL`, `MCP_ENDPOINT`, `HAL_*`) are injected at runtime
- Max tarball size: see platform limits
- Must print `USER ID: <your-uid>` within 30 seconds
- Must keep writing to stdout regularly (heartbeat timeout)

### 2. Shell Script ENTRYPOINT Warning

If using shell script as ENTRYPOINT, DON'T export these vars:

```bash
# SAFE: only sets if unset
: "${OPENAI_BASE_URL:=http://localhost:9000/llm}"

# DANGEROUS: always overwrites, breaks prod
# export OPENAI_BASE_URL=http://localhost:9000/llm
```

**Why:** Shell exports overwrite platform-injected values before your agent runs.

### 3. OpenAI Client Pattern

```python
from openai import OpenAI
import os

client = OpenAI(
    base_url=os.environ["OPENAI_BASE_URL"],
    api_key="not-needed",  # injected by sidecar
)

response = client.chat.completions.create(
    model="llama3-2",
    messages=[{"role": "user", "content": "..."}],
)
```

**Key Points:**
- `base_url` from environment variable
- `api_key` not needed (sidecar handles it)
- Usage tracked automatically by sidecar

### 4. MCP Tools Available

At `MCP_ENDPOINT`:

```python
# Challenge discovery
list_ctfs()
list_challenges(ctf?, category?)
get_challenge(challenge_id)
get_challenge_status(challenge_id)

# Flag submission
submit_flag(challenge_id, flag)

# Hints & scoring
request_hint(challenge_id, hint_index)
get_scoreboard()
get_score_breakdown()
```

### 5. Direct Flag Submission (No MCP Client)

Alternative to MCP:

```python
import requests

response = requests.post(
    "http://127.0.0.1:9000/submit",
    json={"flag": "flag{...}"}
)
```

**Simpler** if you don't want to pull in an MCP client library.

### 6. Environment Variables

**Platform-injected:**
- `OPENAI_BASE_URL` - LLM endpoint
- `MCP_ENDPOINT` - Challenge API
- `HAL_USER_ID` / `USER_ID` - Your user ID
- `HAL_CHALLENGE_ID` - Current challenge
- `HAL_CHALLENGE_NAME` - Challenge name
- `HAL_CHALLENGE_DESCRIPTION` - Challenge description
- `HAL_TARGET_IP` - Target IP address
- `HAL_TARGET_PORT` - Target port
- `BONUS_FLAG` - Free smoke-test flag
- `FLAG_*` - Challenge-specific flags

### 7. Network Access

**Allowed:**
- `127.0.0.1:9000` - Sidecar (LLM proxy, MCP, flag submission)
- CTF target subnets - Challenge infrastructure

**Blocked:**
- Public internet
- HalCTF internal infrastructure
- Other agents/pods

Network policy is the actual boundary (overriding env vars doesn't bypass this).

### 8. Scoring & Best Practices

**Scoring:**
- Correct flag scores immediately
- Resubmitting solved flags = no penalty
- `BONUS_FLAG` in environment - free points, always submit

**Stdout/Heartbeat:**
```python
print(..., flush=True)  # Critical for heartbeat
```

**Graceful Shutdown:**
```python
import requests

requests.post("http://127.0.0.1:9000/done")
```

Finish early and free your queue slot.

### 9. HALCTF-STARTER CTF

Practice CTF always available:

**Flag 1** (Misc, 50 pts)
- Read `FLAG_1` from environment
- Easiest possible warm-up

**Flag 2** (Web, 100 pts, unlocks at 1 point)
- Web target deployed
- Scrape and find flag on page

**Flag 3** (Web, 150 pts, unlocks at 3 points)
- Check `robots.txt`
- Follow crawler best practices

### 10. Upload Process

```bash
# 1. Build and save
docker save my-agent:latest > agent.tar

# 2. Upload to HalCTF platform
# - Pick CTF from menu
# - Upload is resumable
# - Upload once per CTF

# 3. Validation
# - Platform validates tarball
# - Pushes to internal registry
# - Sandboxed check for USER ID print
# - Queued for full run

# 4. Monitor
# - Watch Dashboard
# - Live output streams
# - See results immediately
```

## Key Differences from Our Agent

### What We Got Right ✅
- USER ID print within 30s
- Heartbeat implementation
- Graceful shutdown via /done
- Docker `-u` flag for unbuffered output
- Environment variable scanning
- OpenAI client with base_url from env

### What We Should Improve 🔧

1. **Direct Flag Submission Option**
   - Our agent only uses MCP
   - Could add fallback to `POST /submit`
   - Simpler, no MCP client dependency

2. **BONUS_FLAG Pattern**
   - We scan for FLAG_* correctly
   - But could be more explicit about BONUS_FLAG
   - Should submit it FIRST before anything else

3. **Model Selection**
   - Docs mention "llama3-2"
   - We default to "llama-3.1-8b"
   - Should check available models via API

4. **Environment Variable Handling**
   - Our agent reads all HAL_* vars correctly
   - But should document the shell script warning
   - Add guards for local dev fallbacks

5. **Starter CTF Strategy**
   - Should explicitly handle HALCTF-STARTER
   - Flag 1: Just read FLAG_1 env var
   - Flag 2-3: Simple web scraping
   - Perfect for testing before real CTFs

## Reference Python Skeleton

Minimal working agent based on official docs:

```python
#!/usr/bin/env python3
import os
from openai import OpenAI
import requests

# 1. Print USER ID immediately
user_id = os.environ.get("HAL_USER_ID") or os.environ.get("USER_ID")
print(f"USER ID: {user_id}", flush=True)

# 2. Submit BONUS_FLAG
bonus = os.environ.get("BONUS_FLAG")
if bonus:
    requests.post("http://127.0.0.1:9000/submit", json={"flag": bonus})
    print(f"Submitted BONUS_FLAG", flush=True)

# 3. Setup LLM client
client = OpenAI(
    base_url=os.environ["OPENAI_BASE_URL"],
    api_key="not-needed"
)

# 4. Main agent logic
# ... solve challenges ...

# 5. Graceful shutdown
requests.post("http://127.0.0.1:9000/done")
```

## Action Items

1. Add direct flag submission fallback (no MCP dependency)
2. Prioritize BONUS_FLAG submission at startup
3. Test with HALCTF-STARTER before real CTFs
4. Document shell script env var warning
5. Add local dev fallback guards
6. Query available models from platform
7. Test flag submission both ways (MCP + direct)

---

**Last Updated:** 2026-08-08  
**Source:** https://halctf.aivillage.org/help
