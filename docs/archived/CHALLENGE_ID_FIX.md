# Challenge ID Fix - v4 Agent

## Problem Identified

The agent was trying to use numeric `challenge_id` values (integers), but the HALCTF API expects the **challenge name string** from `HAL_CHALLENGE_NAME`.

### Evidence from Logs
```
[VERIFY] No numeric challenge_id found, using name: 
[VERIFY] WARNING: This may cause HTTP 422 errors if API expects integer
[VERIFY] Challenge: 
```

The challenge name was **empty** in the logs, causing submission failures.

### Evidence from Documentation

From `HALCTF_REQUIREMENTS.md` line 81:
```
- ✅ `challenge_id` - From `HAL_CHALLENGE_NAME` environment variable
```

From the help HTML:
```javascript
// URL pattern for challenges
shortcut.href = '/ctf/' + encodeURIComponent(sel.slug) + '/challenges';
```

The API uses **string slugs/names**, not numeric IDs.

## Changes Made

### 1. Simplified `_get_challenge_id()` method
**Before:** Tried to parse as integer, had fallback logic  
**After:** Simply returns `HAL_CHALLENGE_NAME` as a string

```python
def _get_challenge_id(self):
    """
    Get challenge_id - MUST be the challenge name string from HAL_CHALLENGE_NAME.
    Per HALCTF docs: challenge_id is from HAL_CHALLENGE_NAME environment variable.
    """
    # Use HAL_CHALLENGE_NAME directly (string, not integer)
    challenge_id = self.challenge_name or ""
    print(f"Using challenge_id (from HAL_CHALLENGE_NAME): {challenge_id}", flush=True)

    if not challenge_id:
        print("WARNING: HAL_CHALLENGE_NAME is empty - flag submission will fail", flush=True)

    return challenge_id
```

### 2. Simplified `submit_flag()` method
**Before:** Had brute-force fallback logic trying multiple numeric IDs  
**After:** Directly submits with the string challenge_id

```python
def submit_flag(self, flag: str, challenge_id) -> bool:
    """Submit flag to scoring system using challenge_id (string from HAL_CHALLENGE_NAME)"""
    if not flag or not flag.startswith("HALCTF{"):
        print(f"Invalid flag format: {flag}", flush=True)
        return False

    if not challenge_id:
        print("ERROR: challenge_id is empty - cannot submit flag", flush=True)
        return False

    try:
        resp = requests.post(
            "http://127.0.0.1:9000/submit",
            json={"flag": flag, "challenge_id": challenge_id},
            timeout=5
        )
        print(f"Flag submission (challenge_id='{challenge_id}'): {resp.status_code} - {resp.text}", flush=True)
        return resp.status_code == 200
    except Exception as e:
        print(f"Flag submission failed: {e}", flush=True)
        return False
```

### 3. Removed brute-force method
**Removed:** `submit_flag_brute()` - No longer needed since we use the correct string format

## Expected Behavior

When the agent runs:
1. ✅ Reads `HAL_CHALLENGE_NAME` (e.g., "bills-pc", "cerulean-cave", etc.)
2. ✅ Uses that string directly as `challenge_id` in submissions
3. ✅ No more HTTP 422 errors from wrong challenge_id format
4. ✅ Clear logging shows which challenge_id is being used

## Next Steps

1. **Rebuild the agent:**
   ```bash
   cd bills-pc-agent-v4
   docker build -t bills-pc-agent-v4:latest .
   docker save bills-pc-agent-v4:latest > ../bills-pc-agent-v4.tar
   ```

2. **Upload to HALCTF and test** against any challenge to verify flag submission works

## Files Modified

- `bills-pc-agent-v4/main.py` - Simplified challenge_id handling
