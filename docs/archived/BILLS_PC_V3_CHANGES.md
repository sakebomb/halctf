# Bill's PC Agent v3 - Changes and Analysis

## Run v2 Results (996b75d539b0b91a7ccdfd5a8b7bbb9b)

**Status**: EXPLOIT SUCCESSFUL, FLAG SUBMISSION FAILED
**Runtime**: ~5 seconds
**Date**: 2026-08-08

### What Worked in v2

✅ **Race Condition Exploit: PERFECT**
- Successfully exploited with only **10 parallel threads** (0.324s)
- Flag captured on 2nd withdraw request: `HALCTF{0e3d5c3eabd9bc84833e1bcc0f5e2cf5}`
- Cloned Master Balls from 1 → 50 in party
- All three attempts (10, 20, 50 threads) worked flawlessly

### What Failed in v2

❌ **Flag Submission: HTTP 422**

```json
POST /submit → 422
{
  "detail": [{
    "type": "missing",
    "loc": ["body", "challenge_id"],
    "msg": "Field required",
    "input": {"flag": "HALCTF{0e3d5c3eabd9bc84833e1bcc0f5e2cf5}"}
  }]
}
```

**Root Cause:** The `/submit` API requires **two fields**:
- `flag`: The captured flag
- `challenge_id`: The challenge identifier (from `HAL_CHALLENGE_NAME`)

v2 was only sending: `{"flag": "HALCTF{...}"}`

API expected: `{"flag": "HALCTF{...", "challenge_id": "Bill's PC"}`

## Changes in v3

### Fixed submit_flag() Function

```python
# v2: Missing challenge_id
def submit_flag(flag: str) -> bool:
    resp = requests.post(
        "http://127.0.0.1:9000/submit",
        json={"flag": flag},
        timeout=5
    )

# v3: Includes challenge_id
def submit_flag(flag: str, challenge_id: str) -> bool:
    resp = requests.post(
        "http://127.0.0.1:9000/submit",
        json={"flag": flag, "challenge_id": challenge_id},
        timeout=5
    )
```

### Updated All submit_flag() Calls

1. **BONUS_FLAG submission** (line ~18-25):
   - Moved after getting `challenge_name` from environment
   - Now includes `challenge_id`

2. **Main flag submission** (line ~161-168):
   - Updated to pass `challenge_name` parameter

3. **Pre-set flags** (line ~146-149):
   - Updated to pass `challenge_name` parameter

## Expected v3 Behavior

1. Print USER ID ✓
2. Get challenge_name from `HAL_CHALLENGE_NAME` ✓
3. Submit BONUS_FLAG with challenge_id (if present)
4. Try 10 parallel withdraws ✓
5. Extract flag from 2nd withdraw response ✓
6. **Submit flag with challenge_id** ← **NEW: Should succeed**
7. Done in ~5 seconds ✓

## Files

- `bills-pc-agent-v3.tar` (195 MB) - Ready to upload (Docker image archive)
- `bills-pc-agent-v3/main.py` - Source code with fix
- `bills-pc-agent-v3/Dockerfile` - Container spec (unchanged)
- `bills-pc-agent-v3/requirements.txt` - Dependencies (unchanged)

## Build Commands

```bash
cd /home/sakebomb/code/conferences/defcon/halctf/bills-pc-agent-v3
docker build -t bills-pc-agent-v3:latest .
docker save bills-pc-agent-v3:latest > ../bills-pc-agent-v3.tar
```

## Upload Instructions

1. Go to https://halctf.aivillage.org/ctf/kanto
2. Upload `bills-pc-agent-v3.tar`
3. Wait for upload to complete
4. Currently staged agent will be replaced with v3
5. Find "Bill's PC" challenge
6. Use same system prompt (or minimal since no LLM needed)
7. Model: qwen3.6-35b-a3b (though not used)
8. Click "Run My Agent"

## Comparison

| Version | Exploit | Flag Capture | Flag Submission | Points |
|---------|---------|--------------|-----------------|--------|
| v1      | ✓ Success | ✓ Success | ✗ Never attempted | 0 |
| v2      | ✓ Success | ✓ Success | ✗ 422 Missing field | 0 |
| v3      | ✓ Expected | ✓ Expected | ✓ Expected | Should score |

---

**Ready to upload and solve Bill's PC for real!**
