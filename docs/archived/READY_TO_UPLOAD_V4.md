# Bills PC Agent v4 - Ready to Upload

## Status: ✅ READY

**Date:** 2026-08-08  
**File:** `bills-pc-agent-v4.tar`  
**Size:** 400 MB (well under 2560 MB limit)

## Critical Fix Applied

### Problem
The agent was trying to use numeric `challenge_id` values, but HALCTF expects **string challenge names** from `HAL_CHALLENGE_NAME`.

### Solution
- Removed integer parsing logic
- Agent now uses `HAL_CHALLENGE_NAME` string directly as `challenge_id`
- Removed brute-force fallback logic
- Clean, simple submission flow

### Code Changes
```python
# Before: Tried to parse as int, had complex fallback
# After: Simple string extraction
def _get_challenge_id(self):
    challenge_id = self.challenge_name or ""  # HAL_CHALLENGE_NAME
    print(f"Using challenge_id (from HAL_CHALLENGE_NAME): {challenge_id}", flush=True)
    return challenge_id
```

## Agent Capabilities

✅ **Multi-challenge support:**
- Bill's PC (race condition)
- Cerulean Cave (3-SAT solving)
- Silph Co. (lateral movement)
- Indigo League (ECDSA nonce reuse)

✅ **HALCTF compliant:**
- Prints `USER ID` within 30 seconds
- Regular stdout flushing (heartbeat)
- Graceful shutdown via `/done`
- BONUS_FLAG auto-submission
- Environment flag detection (`FLAG_*`)

✅ **Submission pipeline:**
- Correct challenge_id format (string from HAL_CHALLENGE_NAME)
- HTTP POST to `127.0.0.1:9000/submit`
- Clear logging for debugging

## Upload Instructions

1. **Go to:** https://halctf.aivillage.org/ctf/kanto
2. **Select CTF:** "Kanto" (or appropriate CTF)
3. **Upload:** `bills-pc-agent-v4.tar`
4. **Wait for validation**
5. **Run against challenges**

## Expected Behavior

When agent runs:
```
USER ID: sakebomb
Using challenge_id (from HAL_CHALLENGE_NAME): bills-pc
Challenge: bills-pc
Target: <IP>:80
Description: <challenge description>
=== Multi-Challenge Agent v4 Starting ===
Detected challenge type: bills_pc
[... solver runs ...]
Flag submission (challenge_id='bills-pc'): 200 - {"success": true}
=== Challenge Solved! ===
=== Agent Complete ===
```

## What Changed from v3

| Aspect | v3 | v4 |
|--------|----|----|
| Challenge ID | Numeric (wrong) | String from HAL_CHALLENGE_NAME ✅ |
| Submission | Had brute-force fallback | Direct submission ✅ |
| Error handling | Complex retry logic | Simple, clear errors ✅ |
| Logging | Mixed formats | Consistent, debuggable ✅ |

## Testing Checklist

- [x] Docker image builds successfully
- [x] Tarball created with `docker save`
- [x] Tarball < 2560 MB (400 MB ✅)
- [x] Valid Docker archive (has manifest.json ✅)
- [x] USER ID prints immediately
- [x] Challenge ID uses string format
- [x] Flag submission uses correct API

## Next Step

**Upload `bills-pc-agent-v4.tar` to HALCTF and run it!** 🚀

The challenge_id fix should resolve the HTTP 422 errors you were seeing in the logs.
