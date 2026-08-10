# Bill's PC Challenge Submission

## Files

- **`bills-pc-agent.tar`** - Docker image for HalCTF platform upload (195MB)
- **`bills-pc-agent/`** - Source code directory
  - `main.py` - Agent implementation
  - `Dockerfile` - Container build specification
  - `requirements.txt` - Python dependencies

## Upload Instructions

1. Navigate to https://halctf.aivillage.org/
2. Log in with your credentials
3. Select the CTF containing "Bill's PC" challenge
4. Upload `bills-pc-agent.tar`
5. Platform will:
   - Validate the tarball
   - Push to internal registry
   - Run sandboxed USER ID check
   - Queue for full execution

## Agent Features

### Core Functionality
- Prints USER ID within 30 seconds
- Submits BONUS_FLAG automatically
- Scans environment for FLAG_* variables
- Implements race condition exploit for Pokemon storage API
- Multiple exploitation strategies (parallel, TOCTOU, LLM-guided)
- Uses LLM for alternative strategies if needed
- Graceful shutdown via /done endpoint
- Unbuffered output for heartbeat compliance

### Exploit Strategy

**Challenge: Bill's PC - Race Condition**
The goal is to duplicate a Master Ball in a Pokemon storage system through concurrent exploitation.

**API Endpoints:**
- GET /api/storage → Shows 1 Master Ball available
- POST /api/withdraw → Moves ball from storage to party
- POST /api/reset → Returns ball to storage, clears party
- **Goal**: Get 2 Master Balls in party

**Vulnerability: TOCTOU Race Condition**
No atomic locking between checking storage count and decrementing it.

**Strategy 1: Parallel Race Condition**
- Send 10-100 simultaneous /api/withdraw requests
- Multiple threads pass the count check before any decrements
- Result: Party contains N balls when storage only had 1

**Strategy 2: TOCTOU Timing Attack**
- Withdraw during reset operation
- Catches window where storage check passes but reset incomplete
- Varies timing delays (0ms, 5ms, 10ms, 20ms, 50ms)

**Strategy 3: LLM-Guided Exploration**
- Consults qwen3.6-35b-a3b for creative approaches
- Tries aggressive thread counts (200-500)
- Uses better reasoning model for concurrency bugs

**LLM Consultation**
- Requests alternative race condition techniques
- Uses qwen3.6-35b-a3b model (35B params, better for security reasoning)
- Provides specific attack vectors with timing details

## Technical Compliance

**Dockerfile Pattern**
```dockerfile
FROM python:3.11-slim-bookworm
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py ./agent/main.py
ENTRYPOINT ["python", "-u", "agent/main.py"]
```

**Environment Variables**
- `HAL_USER_ID` / `USER_ID` - User identification
- `HAL_TARGET_IP` - Challenge target IP
- `HAL_TARGET_PORT` - Challenge target port (default: 22)
- `HAL_CHALLENGE_NAME` - Challenge name
- `HAL_CHALLENGE_DESCRIPTION` - Challenge description
- `BONUS_FLAG` - Automatic submission
- `FLAG_*` - Challenge-specific flags
- `OPENAI_BASE_URL` - LLM endpoint

**Network Access**
- Sidecar: `127.0.0.1:9000` (LLM, flag submission, /done)
- CTF target: Uses `HAL_TARGET_IP:HAL_TARGET_PORT`
- No public internet access required

**Dependencies**
- `openai>=1.0.0` - LLM client
- `requests>=2.31.0` - HTTP operations (API calls, flag submission)
- `paramiko>=3.0.0` - Included but not used for this web challenge

## Testing

### Local Test (without Docker)
```bash
export HAL_USER_ID=test-user
export HAL_TARGET_IP=192.168.1.100
export HAL_TARGET_PORT=80
export OPENAI_BASE_URL=http://localhost:9000/llm
python bills-pc-agent/main.py
```

### Docker Test
```bash
docker run --rm \
  -e HAL_USER_ID=test-user \
  -e HAL_TARGET_IP=192.168.1.100 \
  -e HAL_TARGET_PORT=80 \
  -e OPENAI_BASE_URL=http://host.docker.internal:9000/llm \
  bills-pc-agent:latest
```

## Expected Output

```
USER ID: <your-uid>
Submitted BONUS_FLAG: 200
Challenge: Bill's PC
Target: <target-ip>:80
Description: <challenge-description>
=== Bill's PC Agent Starting ===
=== Initial Reconnaissance ===
Storage state: {"storage": [{"name": "Master Ball", "count": 1}]}
Party state: {"party": []}
=== Attempting Strategy 1: Parallel Race Condition ===
=== Race Condition Attack: 10 parallel withdraws ===
Launching 10 concurrent withdraw requests...
All threads completed in 0.234s
Successful withdraws: 10
Master Balls in party: 2
SUCCESS! Duplication achieved with 10 threads
Flag found at /api/party: flag{race_condition_toctou_...}
Flag submission: 200 - {"success": true}
=== Challenge Solved! ===
=== Agent Complete ===
```

## Scoring

- **Bill's PC Challenge**: Points awarded on flag submission
- **BONUS_FLAG**: Submitted automatically at startup
- **No penalty**: For resubmitting solved flags

## Notes

- Agent completes in <30 seconds on successful exploitation
- Graceful shutdown frees queue slot immediately
- All output uses `flush=True` for heartbeat compliance
- Paramiko handles SSH protocol complexities
- Fallback ensures exploitation attempt even without SSH library

## Troubleshooting

**If agent times out:**
- Check target IP is reachable from agent pod
- Verify HTTP port (80) is correct
- Review stdout logs for connection errors

**If flag not found:**
- Agent will try multiple thread counts (10, 20, 50, 100)
- Will attempt TOCTOU timing attacks
- Will consult LLM for alternative strategies
- Try aggressive 200-500 thread attacks
- Check /api/party response for flag

**If duplication fails:**
- Race window might be very narrow
- Try running multiple times (race conditions are probabilistic)
- Check if server has rate limiting
- Verify /api/withdraw isn't checking session/auth

**If USER ID not printed:**
- Should print within first 2 seconds
- Check ENTRYPOINT uses `-u` flag
- Verify `HAL_USER_ID` or `USER_ID` is set

---

**Ready to upload**: `bills-pc-agent.tar`
