# Bill's PC Challenge - Current Status

**Last Updated:** 2026-08-08 08:36 UTC

## Challenge Status: ✅ EXPLOIT WORKING, ❌ SUBMISSION NEEDS FIX

### Current Situation

**Agent v2 Run ID:** `996b75d539b0b91a7ccdfd5a8b7bbb9b`
- ✅ Race condition exploit: **PERFECT** (10 threads, 0.324s)
- ✅ Flag captured: `HALCTF{0e3d5c3eabd9bc84833e1bcc0f5e2cf5}`
- ❌ Submission failed: HTTP 422 (missing `challenge_id` field)

### The Fix

**Agent v3** is ready with the fix:
- File: `bills-pc-agent-v3.tar` (195 MB Docker image)
- SHA256: `cc4d99a83b5c...`
- Change: Added `challenge_id` parameter to flag submission
- Location: `/home/sakebomb/code/conferences/defcon/halctf/bills-pc-agent-v3.tar`
- Verified: Contains manifest.json ✓

## Next Steps

### To Complete the Challenge:

1. **Upload v3 agent:**
   ```
   Navigate to: https://halctf.aivillage.org/ctf/kanto
   Upload: bills-pc-agent-v3.tar
   ```

2. **Run the agent:**
   - Challenge: "Bill's PC"
   - System Prompt: (minimal or same as before)
   - Model: qwen3.6-35b-a3b
   - Click "Run My Agent"

3. **Expected Result:**
   - Exploit succeeds (10 threads)
   - Flag captured in ~0.3 seconds
   - Flag submitted successfully
   - **Points scored! 🎉**

## Technical Details

### The Problem in v2

```python
# v2 sent this:
{"flag": "HALCTF{0e3d5c3eabd9bc84833e1bcc0f5e2cf5}"}

# API expected this:
{"flag": "HALCTF{0e3d5c3eabd9bc84833e1bcc0f5e2cf5}", "challenge_id": "Bill's PC"}
```

### The Fix in v3

```python
def submit_flag(flag: str, challenge_id: str) -> bool:
    resp = requests.post(
        "http://127.0.0.1:9000/submit",
        json={"flag": flag, "challenge_id": challenge_id},
        timeout=5
    )
```

## Run History

| Run | Agent | Status | Exploit | Flag | Submission | Points |
|-----|-------|--------|---------|------|------------|--------|
| e227b8a8 | v1 | Completed | ✓ | ✓ | Never tried | 0 |
| 996b75d5 | v2 | Completed | ✓ | ✓ | ❌ 422 | 0 |
| TBD | v3 | Ready | Expected ✓ | Expected ✓ | Expected ✓ | TBD |

## Files

- `/home/sakebomb/code/conferences/defcon/halctf/bills-pc-agent-v3.tar` - **Ready to upload**
- `/home/sakebomb/code/conferences/defcon/halctf/BILLS_PC_V3_CHANGES.md` - Detailed changes
- `/home/sakebomb/code/conferences/defcon/halctf/run_996b75d539b0b91a_logs.txt` - v2 logs

---

**Status: Ready to solve! Upload v3 and run.**
