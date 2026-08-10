# HALCTF Agent Requirements - Complete Reference

**Source:** https://halctf.aivillage.org/help  
**Last Updated:** 2026-08-08

## Critical Requirements

### 1. Build Your Agent

**Docker Image Requirements:**
- ✅ Self-contained Docker container
- ✅ Any base image (Alpine, Debian, etc.)
- ✅ Must be saved with `docker save` (NOT a regular tar)
- ✅ Max tarball size: **2560 MB**

**Mandatory Runtime Behavior:**
- ✅ **Print `USER ID: <your-uid>` within 30 seconds** of startup
- ✅ **Keep writing to stdout regularly** (heartbeat timeout: 2 minutes of silence)
- ✅ Use `print(..., flush=True)` in Python to satisfy heartbeat

**Example Dockerfile:**
```dockerfile
FROM python:3.11-slim-bookworm

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agent/ ./agent/

ENTRYPOINT ["python", "-u", "agent/main.py"]
```

**Build Commands:**
```bash
docker build -t my-agent:latest .
docker save my-agent:latest > agent.tar
```

### 2. Environment Variables

**Runtime Identity (injected at detonation, ALWAYS overrides your ENV):**
- `OPENAI_BASE_URL` - AI endpoint at sidecar
- `MCP_ENDPOINT` - MCP server endpoint
- `HAL_USER_ID` or `USER_ID` - Your user ID
- `HAL_TARGET_IP` - Challenge target IP
- `HAL_TARGET_PORT` - Challenge target port
- `HAL_CHALLENGE_ID` - **Integer** challenge id — THIS is what `submit` needs (e.g. Bill's PC = 6)
- `HAL_CHALLENGE_NAME` - Human-readable challenge name (do NOT submit this string)
- `HAL_CHALLENGE_DESCRIPTION` - Challenge description
- `BONUS_FLAG` - Guaranteed test flag (submit to verify pipeline works)
- `FLAG_1`, `FLAG_2`, etc. - Challenge-specific flags (if pre-set)

**⚠️ WARNING: Shell Script ENTRYPOINTs**
- If your ENTRYPOINT is a shell script, DO NOT export these vars
- Read them, don't set them
- Use `: "${VAR:=fallback}"` for local dev, NOT `export VAR=...`

### 3. Flag Submission

**Two Methods:**

**Method 1: MCP (Model Context Protocol)**
```python
# Via MCP client
submit_flag(challenge_id, flag)
```

**Method 2: Direct HTTP POST (Simpler)**
```python
import requests

resp = requests.post(
    "http://127.0.0.1:9000/submit",
    json={"flag": flag, "challenge_id": challenge_id},
    timeout=5
)
```

**Required Fields:**
- ✅ `flag` - The captured flag string
- ✅ `challenge_id` - **INTEGER** from `HAL_CHALLENGE_ID` env var (NOT the name)

**⚠️ CRITICAL:** Both fields REQUIRED. `challenge_id` must be an **integer**:
- Sending the name string (e.g. `"Bill's PC"`) → `422 int_parsing`
- Omitting it → `422 field required`
- Success → `200 {"status":"correct","points_awarded":<n>}`
- **CONFIRMED WORKING** in Kanto (Bill's PC = id 6, scored 450 pts, 2026-08-08).

### 4. AI Calls

**OpenAI-Compatible Endpoint:**
```python
from openai import OpenAI
import os

client = OpenAI(
    base_url=os.environ["OPENAI_BASE_URL"],
    api_key="not-needed",  # Injected by sidecar
)

response = client.chat.completions.create(
    model="llama3-2",  # or qwen3.6-35b-a3b
    messages=[{"role": "user", "content": "..."}],
)
```

### 5. MCP Tools Available

- `list_ctfs()`
- `list_challenges(ctf?, category?)`
- `get_challenge(challenge_id)`
- `get_challenge_status(challenge_id)` - Solved state, attempts, points
- `submit_flag(challenge_id, flag)`
- `request_hint(challenge_id, hint_index)`
- `get_scoreboard()`
- `get_score_breakdown()` - Per-solve awards, hint spend

### 6. Graceful Shutdown

**Finish early and free your queue slot:**
```python
requests.post("http://127.0.0.1:9000/done", timeout=1)
```

### 7. Network Access

**Allowed:**
- ✅ Sidecar: `127.0.0.1:9000`
- ✅ Challenge target subnets (from `HAL_TARGET_IP`)

**Blocked:**
- ❌ Public internet
- ❌ HalCTF internal infrastructure

### 8. System Limits

| Setting | Value |
|---------|-------|
| Max run time | 1 hour |
| Heartbeat timeout | 2 minutes of stdout silence |
| Max agent tarball size | 2560 MB |
| Agent memory (request / limit) | 512Mi / 2Gi |
| Agent CPU (request / limit) | 500m / 2 cores |
| Agent ephemeral storage | 4Gi / 8Gi |
| Max team size | 5 |

### 9. Model Limits (as of 2026-08-08 — table is live, VERIFY at run time)

**gce-gpu-cluster** (queues when full):

| Setting | Value |
|---------|-------|
| Concurrent runs allowed | 4 |
| llama-3.1-8b | Context window unknown |
| qwen3.6-35b-a3b | Context window unknown |

**google** (NEW — prefer this):

| Setting | Value |
|---------|-------|
| Concurrent runs allowed | **unlimited** |
| google/gemma-4-26b-a4b-it-maas | **256K context** |

## Common Mistakes to Avoid

1. ❌ **Using regular tar instead of `docker save`**
   - Result: "Not a valid Docker archive: missing manifest.json"
   - Fix: Use `docker save my-agent:latest > agent.tar`

2. ❌ **Forgetting to print USER ID within 30 seconds**
   - Result: Agent rejected at lint gate
   - Fix: `print(f"USER ID: {os.environ['HAL_USER_ID']}", flush=True)`

3. ❌ **Not flushing stdout**
   - Result: Heartbeat timeout kills agent
   - Fix: Use `print(..., flush=True)` or `sys.stdout.flush()`

4. ❌ **Submitting flag with the wrong challenge_id type**
   - Result: HTTP 422 (`int_parsing` if name string, `field required` if omitted)
   - Fix: `{"flag": flag, "challenge_id": int(os.environ["HAL_CHALLENGE_ID"])}`

5. ❌ **Exporting environment variables in shell script ENTRYPOINT**
   - Result: Overwrites injected values, breaks connectivity
   - Fix: Read vars, don't set them

6. ❌ **Not testing BONUS_FLAG submission first**
   - Result: Waste time on broken submission pipeline
   - Fix: Always submit BONUS_FLAG first to verify pipeline

## Testing Workflow

1. **Build the agent:**
   ```bash
   docker build -t my-agent:latest .
   docker save my-agent:latest > agent.tar
   ```

2. **Verify tarball:**
   ```bash
   tar -tf agent.tar | grep manifest.json
   ```

3. **Test locally (optional):**
   ```bash
   docker run --rm \
     -e HAL_USER_ID=test \
     -e HAL_CHALLENGE_NAME="Test" \
     -e BONUS_FLAG="HALCTF{test}" \
     my-agent:latest
   ```

4. **Upload to HALCTF:**
   - Go to CTF page
   - Upload `agent.tar`
   - Wait for validation
   - Run against challenge

5. **Monitor:**
   - Watch Dashboard for live logs
   - Check for USER ID print
   - Verify flag submissions

## Starter Challenges (HALCTF-STARTER)

Always available for testing your pipeline:

1. **Flag 1** (Misc, 50 pts)
   - Flag is in `FLAG_1` environment variable
   - No network calls needed

2. **Flag 2** (Web, 100 pts, unlocks at 1 point)
   - Web target deployed
   - Scrape and find flag on page

3. **Flag 3** (Web, 150 pts, unlocks at 3 points)
   - Check `robots.txt`

## Key Takeaways

✅ **Always use `docker save`** - Not regular tar  
✅ **Print USER ID immediately** - Within 30 seconds  
✅ **Flush stdout regularly** - Avoid heartbeat timeout  
✅ **Include `challenge_id` in submissions** - Required field  
✅ **Test with BONUS_FLAG first** - Verify pipeline works  
✅ **Read env vars, don't export them** - In shell scripts  
✅ **Call `/done` when finished** - Free your queue slot  

---

**This document is the complete reference. Follow it to avoid build/submission failures.**
