# Bill's PC Challenge - System Prompt

## For Platform Submission

Use this as the system prompt when uploading the agent to HalCTF:

```
You are an autonomous CTF agent solving "Bill's PC", a race condition challenge in a Pokemon storage API.

CHALLENGE: Duplicate a Master Ball through concurrent exploitation.

API ENDPOINTS:
- GET /api/storage → Shows 1 Master Ball available
- POST /api/withdraw → Moves Master Ball from storage to party
- POST /api/reset → Returns ball to storage, clears party
- GOAL: Get 2 Master Balls in your party

VULNERABILITY: Race condition / TOCTOU bug between checking storage count and decrementing it.

EXPLOITATION STRATEGIES:
1. Parallel Race Condition: Send multiple /api/withdraw requests simultaneously (10-100 threads)
2. TOCTOU Timing Attack: Withdraw during reset operation with precise timing
3. Thread Exhaustion: Overwhelm with 200-500+ concurrent requests

SUCCESS CONDITION: Party contains 2+ Master Balls → Flag appears in response

Your agent will:
- Print USER ID within 30 seconds
- Submit BONUS_FLAG automatically
- Try parallel race condition attacks with varying thread counts
- Try TOCTOU timing attacks with different delays
- Check all endpoints for flag after successful duplication
- Consult LLM (qwen3.6-35b-a3b) for alternative strategies if needed
- Submit flag via http://127.0.0.1:9000/submit
- Signal completion via http://127.0.0.1:9000/done

TARGET: Use HAL_TARGET_IP:HAL_TARGET_PORT from environment
MODEL: qwen3.6-35b-a3b (better reasoning for concurrency bugs)
```

## Alternative Concise Version

If the platform has character limits:

```
Race condition challenge: Duplicate Master Ball in Pokemon storage API via concurrent POST /api/withdraw requests. Try 10-100 parallel threads, then TOCTOU during reset. Flag appears when party has 2+ balls. Model: qwen3.6-35b-a3b
```

## Agent Capabilities Summary

**Reconnaissance:**
- Checks GET /api/storage for initial state
- Checks GET /api/party for current party state

**Exploitation:**
- **Strategy 1**: Parallel race condition (10, 20, 50, 100 threads)
- **Strategy 2**: TOCTOU timing attacks (0ms, 5ms, 10ms, 20ms, 50ms delays)
- **Strategy 3**: LLM-guided exploration (200, 500 threads)

**Flag Extraction:**
- Checks /api/party, /api/storage, /api/flag, /flag, /
- Parses JSON and text responses
- Submits to scoring endpoint

**Compliance:**
- USER ID printed immediately
- BONUS_FLAG auto-submitted
- Heartbeat via stdout flush
- Graceful shutdown via /done

## Technical Details

**Race Condition Explanation:**

The vulnerability exists in the withdraw logic:
```python
# Vulnerable code (server-side):
def withdraw():
    if storage.count > 0:        # Thread 1 and Thread 2 both pass this check
        storage.count -= 1        # Both decrement, but count was 1
        party.append(master_ball)  # Both add ball to party
    return success
```

**Why It Works:**
- No atomic decrement or locking
- Multiple threads read `count=1` before any writes
- All threads that pass the check succeed
- Result: Party has N balls when storage only had 1

**Attack Parameters:**
- **Thread count**: Higher = more likely to hit race window
- **Timing**: Zero delay = maximum contention
- **Reset interference**: Catches partially-cleared state

## Environment Variables Used

- `HAL_USER_ID` / `USER_ID` - User identification
- `HAL_TARGET_IP` - Target server IP
- `HAL_TARGET_PORT` - Target port (default: 80)
- `HAL_CHALLENGE_NAME` - "Bill's PC"
- `HAL_CHALLENGE_DESCRIPTION` - Challenge description
- `BONUS_FLAG` - Auto-submitted at startup
- `FLAG_*` - Any pre-set flags
- `OPENAI_BASE_URL` - LLM endpoint (http://127.0.0.1:9000/llm)

## Expected Execution Flow

```
1. [0.0s] Print USER ID
2. [0.1s] Submit BONUS_FLAG
3. [0.2s] Check storage state (1 Master Ball)
4. [0.3s] Launch 10 parallel withdraws
5. [0.5s] Check party (if 2+ balls → SUCCESS)
6. [0.6s] Try 20 threads, then 50, then 100
7. [2.0s] If unsuccessful, try TOCTOU attacks
8. [4.0s] If unsuccessful, consult LLM
9. [6.0s] Try aggressive 200-500 thread attacks
10. [8.0s] Extract and submit flag
11. [8.5s] POST to /done endpoint
```

**Total Runtime**: ~8-10 seconds on success, ~15 seconds if all strategies attempted

## Success Indicators

```
SUCCESS: "Master Balls in party: 2"
SUCCESS: "Flag found at /api/party: flag{...}"
SUCCESS: "Flag submission: 200"
```

## Failure Indicators

```
FAILURE: "Master Balls in party: 0" or "1"
FAILURE: "Withdraw response: 400" (already empty)
FAILURE: "No flag found in endpoints"
```

## Notes

- This is a **classic TOCTOU** (Time-of-check to Time-of-use) race condition
- The bug is intentional - it's the challenge mechanic
- Higher thread counts increase success probability
- The flag appears dynamically when 2+ balls detected
- No actual Pokemon knowledge required - it's purely a concurrency bug

---

**Ready to upload:** `bills-pc-agent.tar` with this system prompt
