# Bill's PC Agent v2 - Changes and Analysis

## Run v1 Results (e227b8a8a79c182cc16eb03123400596)

**Status**: Succeeded (but 0 points)
**Runtime**: 28 seconds
**Date**: 2026-08-08 10:25-10:26 UTC

### What Worked in v1
- Race condition exploit: PERFECT
  - Successfully duplicated Master Balls with 10, 20, 50 parallel threads
  - Got flag in withdraw response on 2nd request
  - Flag: `HALCTF{69942a7efdae38552cc501b9fd3a8c39}`

### What Failed in v1
1. **BONUS_FLAG submission returned 422** - Wrong format
2. **Flag extraction** - Agent printed flag but never extracted it from JSON
3. **Flag submission** - `check_for_flag()` looked at wrong endpoints, never submitted

### Root Cause
- `withdraw_item()` only returned True/False, not the flag
- Flag was in JSON response but not extracted: `{"flag": "HALCTF{...}"}`
- `check_for_flag()` tried `/api/party`, `/api/storage` etc. which returned 404
- Real flag was already in the withdraw response

## Changes in v2

### 1. Removed Unnecessary Dependencies
- Removed OpenAI client (not needed for this challenge)
- Removed paramiko (SSH not used)
- Kept only requests and threading

### 2. Fixed withdraw_item()
```python
# v1: Only returned boolean
def withdraw_item() -> bool:
    resp = requests.post(...)
    return resp.status_code == 200

# v2: Extracts and returns flag
def withdraw_item() -> Optional[str]:
    resp = requests.post(...)
    data = resp.json()
    if 'flag' in data:
        flag = data['flag']
        return flag
    return None
```

### 3. Simplified Race Condition Logic
```python
def race_condition_exploit(num_threads: int = 10) -> Optional[str]:
    # Launch threads
    def withdraw_thread():
        flag = withdraw_item()
        if flag:
            flags.append(flag)
    
    # Wait and return first flag found
    return flags[0] if flags else None
```

### 4. Direct Flag Submission
```python
# Main loop
for num_threads in [10, 20, 50]:
    flag = race_condition_exploit(num_threads)
    if flag:
        submit_flag(flag)
        break
```

### 5. Removed Broken Code
- Removed `check_for_flag()` - endpoints return 404
- Removed `extract_flag_from_response()` - not needed
- Removed LLM consultation - not needed for this challenge
- Removed TOCTOU timing attack - parallel race condition works perfectly

## Key Improvements

1. **Simpler**: 180 lines vs 330 lines
2. **Faster**: Only tries 10/20/50 threads (v1 tried up to 500)
3. **Direct**: Extracts flag from withdraw response immediately
4. **Focused**: Removed all unnecessary code paths

## Expected v2 Behavior

1. Print USER ID
2. Submit BONUS_FLAG (if format is still wrong, won't block)
3. Try 10 parallel withdraws
4. Extract flag from 2nd withdraw response
5. Submit flag immediately
6. Done in ~5-10 seconds

## Upload Instructions

1. Go to https://halctf.aivillage.org/ctf/kanto
2. Upload `bills-pc-agent-v2.tar`
3. Wait for upload to complete
4. Go to https://halctf.aivillage.org/ctf/kanto/challenges
5. Find "Bill's PC" challenge
6. Use same system prompt (or simpler since no LLM)
7. Model: qwen3.6-35b-a3b (though not used)
8. Click "Run My Agent"

## Files

- `bills-pc-agent-v2.tar` (195 MB) - Ready to upload
- `bills-pc-agent-v2/main.py` - Source code
- `bills-pc-agent-v2/Dockerfile` - Container spec
- `bills-pc-agent-v2/requirements.txt` - Dependencies

---

**Ready to upload and solve Bill's PC!**
