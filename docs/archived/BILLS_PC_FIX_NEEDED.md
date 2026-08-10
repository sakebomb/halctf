# Bill's PC Agent - Flag Submission Bug

## Issue

The agent **successfully obtains the flag** but **fails to submit it** to the scoring system.

### Error from Logs
```
[NGINX-SIDECAR] POST /submit → 422
[AGENT] Flag submission: 422 - {
  "detail":[{
    "type":"int_parsing",
    "loc":["body","challenge_id"],
    "msg":"Input should be a valid integer, unable to parse string as an integer",
    "input":"Bill's PC"
  }]
}
```

## Root Cause

The `/submit` API expects `challenge_id` to be an **integer**, but we're sending the string `"Bill's PC"` (from `HAL_CHALLENGE_NAME` environment variable).

## Current Code (v2, v3, v4)

```python
challenge_name = os.environ.get("HAL_CHALLENGE_NAME", "")  # "Bill's PC"

# Later...
requests.post("http://127.0.0.1:9000/submit", 
              json={"flag": flag, "challenge_id": challenge_name})
              #                                  ^^^^^^^^^^^^^ STRING, needs to be INT
```

## Solutions

### Option 1: Check for HAL_CHALLENGE_ID environment variable

Maybe there's a `HAL_CHALLENGE_ID` env var with the numeric ID?

```python
challenge_id = os.environ.get("HAL_CHALLENGE_ID")
if challenge_id:
    challenge_id = int(challenge_id)
else:
    # Fallback to challenge_name
    challenge_id = challenge_name
```

### Option 2: Lookup challenge ID via API

Query the challenges list to find the numeric ID:

```python
def get_challenge_id(challenge_name: str) -> Optional[int]:
    """Look up numeric challenge ID from name"""
    try:
        # Try to use MCP protocol if available
        import socket
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect("/var/run/halctf-mcp.sock")
        
        # Send list_challenges request
        # ... MCP protocol details ...
        
        # Parse response to find challenge ID
        return challenge_id
    except:
        return None
```

### Option 3: Try numeric extraction from name

Some CTFs use numeric IDs that appear in the challenge slug:

```python
# Extract any numbers from challenge name/slug
import re
challenge_slug = challenge_name.lower().replace(" ", "-")  # "bills-pc"

# If the platform has numeric IDs in URLs, they might be in environment
# Check for patterns like: /challenge/123, /ctf/kanto/456, etc.
```

### Option 4: Hardcode known challenge IDs (TEMPORARY)

As a quick fix for testing:

```python
CHALLENGE_IDS = {
    "Bill's PC": 1,  # Replace with actual ID
    "Cerulean Cave": 2,
    "Silph Co.": 3,
    "The Indigo League": 4,
}

challenge_id = CHALLENGE_IDS.get(challenge_name, challenge_name)
```

## Recommended Fix

**Step 1**: Test if `HAL_CHALLENGE_ID` exists

Upload a simple test agent that prints all environment variables starting with `HAL_`:

```python
import os
for key, value in sorted(os.environ.items()):
    if key.startswith("HAL_"):
        print(f"{key}={value}", flush=True)
```

**Step 2**: If no numeric ID in environment, query the MCP socket

The agent runs with MCP protocol available at `/var/run/halctf-mcp.sock` (or similar). We can query it for the challenge list.

**Step 3**: Update all versions (v2, v3, v4) with the fix

## Test Plan

1. Create minimal test agent that just prints all `HAL_*` environment variables
2. Upload and run it on "Bill's PC" challenge
3. Check logs for `HAL_CHALLENGE_ID` or similar
4. Update agent code with correct approach
5. Re-test flag submission

## Impact

- ✅ Agent successfully exploits the race condition
- ✅ Agent successfully obtains the flag
- ❌ Agent fails to submit the flag for points
- Result: **0 points despite solving the challenge**

## Priority

**HIGH** - This is a blocking bug that prevents scoring despite successful challenge completion.
