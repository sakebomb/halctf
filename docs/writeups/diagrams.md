# HalCTF Architecture Diagrams

Visual representations of our agent architectures, workflows, and attack patterns.

## Table of Contents

1. [Overall Challenge Map](#overall-challenge-map)
2. [Multi-Solver Agent Architecture](#multi-solver-agent-architecture)
3. [Development Iteration Cycle](#development-iteration-cycle)
4. [Race Condition Exploit Flow](#race-condition-exploit-flow)
5. [Nested SSRF Attack Chain](#nested-ssrf-attack-chain)
6. [Timing Attack Visualization](#timing-attack-visualization)
7. [LLM Copilot Decision Tree](#llm-copilot-decision-tree)

---

## Overall Challenge Map

```
┌─────────────────────────────────────────────────────────────────────┐
│                      HalCTF 2026 - AI Village                        │
│                     DEF CON 34 CTF Competition                       │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
            ┌───────▼──────┐ ┌─────▼──────┐ ┌─────▼──────┐
            │   Hac-Man    │ │   Kanto    │ │  Labyrinth │
            │   50 pts     │ │  1,450 pts │ │  1,175 pts │
            └───────┬──────┘ └─────┬──────┘ └─────┬──────┘
                    │               │               │
                    │               │               │
        ┌───────────▼───────────────▼───────────────▼──────────┐
        │           hacman-agent-v7.tar (207MB)                 │
        │           kanto-agent-v13.tar (172MB)                 │
        │           labyrinth-agent-v10.tar (218MB)             │
        └───────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
            ┌───────▼──────┐ ┌─────▼──────┐ ┌─────▼──────┐
            │ LLM Word Gen │ │ 4 Challenges│ │ 9 Puzzles  │
            │ camelCase    │ │ Pokemon Ref │ │ Multi-Type │
            └──────────────┘ └─────┬──────┘ └─────┬──────┘
                                   │               │
                    ┌──────────────┼───────┐       │
                    │              │       │       │
             ┌──────▼─────┐ ┌─────▼────┐  │  ┌───▼────────┐
             │  Bill's PC │ │ Cerulean │  │  │  Achilles  │
             │ Race Cond. │ │ 3-SAT    │  │  │  ret2win   │
             └────────────┘ └──────────┘  │  └────────────┘
                                          │
                            ┌─────────────┼──────────┐
                            │             │          │
                     ┌──────▼──────┐ ┌───▼────┐ ┌──▼────────┐
                     │   Indigo    │ │ Silph  │ │ + 6 more  │
                     │   ECDSA     │ │ SSRF   │ │  puzzles  │
                     └─────────────┘ └────────┘ └───────────┘
```

---

## Multi-Solver Agent Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         AGENT CONTAINER                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │                      agent.py (Main)                       │    │
│  │  ┌──────────────────────────────────────────────────────┐ │    │
│  │  │  1. Environment scan (quick wins)                    │ │    │
│  │  │  2. MCP: List available challenges                   │ │    │
│  │  │  3. Route to appropriate solver                      │ │    │
│  │  │  4. Execute solver                                   │ │    │
│  │  │  5. Submit flag via MCP                              │ │    │
│  │  └──────────────────────────────────────────────────────┘ │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │                    SOLVER REGISTRY                         │    │
│  │  ┌──────────────┬──────────────┬──────────────────────┐   │    │
│  │  │ Challenge ID │ Solver       │ Type                 │   │    │
│  │  ├──────────────┼──────────────┼──────────────────────┤   │    │
│  │  │ 6            │ bills_pc     │ Race Condition       │   │    │
│  │  │ 3            │ cerulean     │ 3-SAT                │   │    │
│  │  │ 5            │ indigo       │ ECDSA Nonce Reuse    │   │    │
│  │  │ 4            │ silph_co     │ Nested SSRF          │   │    │
│  │  │ *            │ copilot      │ LLM Fallback         │   │    │
│  │  └──────────────┴──────────────┴──────────────────────┘   │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │                    SOLVERS/ DIRECTORY                      │    │
│  │                                                            │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │    │
│  │  │ bills_pc.py  │  │ cerulean.py  │  │ indigo.py    │    │    │
│  │  │              │  │              │  │              │    │    │
│  │  │ - Fire 20    │  │ - Get wards  │  │ - Get badges │    │    │
│  │  │   concurrent │  │ - pycosat    │  │ - Find nonce │    │    │
│  │  │   withdrawals│  │   solve      │  │   reuse pair │    │    │
│  │  │ - Check for  │  │ - Submit     │  │ - Recover d  │    │    │
│  │  │   2+ balls   │  │   solution   │  │ - Sign msg   │    │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘    │    │
│  │                                                            │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │    │
│  │  │ silph_co.py  │  │ copilot.py   │  │ _files.py    │    │    │
│  │  │              │  │              │  │              │    │    │
│  │  │ - Enum staff │  │ - Bounded    │  │ - Fetch from │    │    │
│  │  │ - Find key   │  │   ReAct loop │  │   MCP or     │    │    │
│  │  │ - Linkcheck  │  │ - Max 14     │  │   bundle     │    │    │
│  │  │   to mainfrm │  │   steps      │  │ - Self-diag  │    │    │
│  │  │ - Nested SSRF│  │ - Quota-safe │  │   logging    │    │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘    │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │                    UTILS/ DIRECTORY                        │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │    │
│  │  │ mcp_client   │  │ llm.py       │  │ submit.py    │    │    │
│  │  │              │  │              │  │              │    │    │
│  │  │ - List       │  │ - Model      │  │ - Format     │    │    │
│  │  │   challenges │  │   selection  │  │   validation │    │    │
│  │  │ - Get        │  │ - Auto-      │  │ - Dedup      │    │    │
│  │  │   challenge  │  │   fallback   │  │ - Rate limit │    │    │
│  │  │ - Submit     │  │ - Graceful   │  │ - Retry w/   │    │    │
│  │  │   flag       │  │   degrade    │  │   backoff    │    │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘    │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 │ MCP Protocol
                                 ▼
                    ┌────────────────────────┐
                    │   HalCTF Platform      │
                    │   127.0.0.1:9000       │
                    │                        │
                    │  - Challenge list      │
                    │  - Challenge details   │
                    │  - Flag submission     │
                    │  - Hint requests       │
                    └────────────────────────┘
```

---

## Development Iteration Cycle

```
                              START
                                │
                                ▼
                    ┌───────────────────────┐
                    │  Read Challenge Desc  │
                    │  + Hints + Metadata   │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  Manual Recon         │
                    │  - Test endpoints     │
                    │  - Understand API     │
                    │  - Prove exploit      │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  Write Solver v1      │
                    │  - Keep it simple     │
                    │  - Add logging        │
                    │  - Handle errors      │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  Build Docker Image   │
                    │  docker build -t v1   │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  Upload to Platform   │
                    │  docker save > tar    │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  Run Against Live     │
                    │  Challenge            │
                    └───────────┬───────────┘
                                │
                ┌───────────────┴───────────────┐
                │                               │
                ▼                               ▼
    ┌───────────────────────┐       ┌───────────────────────┐
    │  [SOLVED] SUCCESS!          │       │  [NOT SOLVED] FAILED            │
    │  Flag captured        │       │  Read logs            │
    └───────────┬───────────┘       └───────────┬───────────┘
                │                               │
                │                               ▼
                │                   ┌───────────────────────┐
                │                   │  Diagnose Failure     │
                │                   │  - API format?        │
                │                   │  - Logic bug?         │
                │                   │  - Missing auth?      │
                │                   └───────────┬───────────┘
                │                               │
                │                               ▼
                │                   ┌───────────────────────┐
                │                   │  Fix Issue (v2)       │
                │                   │  - Minimal change     │
                │                   │  - Add more logging   │
                │                   │  - Test locally       │
                │                   └───────────┬───────────┘
                │                               │
                │                               ▼
                │                   ┌───────────────────────┐
                │                   │  Rebuild & Re-upload  │
                │                   │  (15-30 min cycle)    │
                │                   └───────────┬───────────┘
                │                               │
                │                               │
                │               ┌───────────────┘
                │               │
                │               ▼
                │   ┌───────────────────────┐
                │   │ Attempt #2            │
                │   │ Did it work now?      │
                │   └───────────┬───────────┘
                │               │
                │       ┌───────┴───────┐
                │       │               │
                │       ▼               ▼
                │   [SOLVED] YES           [NOT SOLVED] NO
                │       │               │
                │       │               ▼
                │       │   ┌───────────────────────┐
                │       │   │ Attempt #3            │
                │       │   │ Try alternative?      │
                │       │   └───────────┬───────────┘
                │       │               │
                │       │       ┌───────┴───────┐
                │       │       │               │
                │       │       ▼               ▼
                │       │   [SOLVED] YES           [NOT SOLVED] NO
                │       │       │               │
                │       │       │               ▼
                │       │       │   ┌───────────────────────┐
                │       │       │   │ STOP - Move to next  │
                │       │       │   │ challenge (3-try rule)│
                │       │       │   └───────────────────────┘
                │       │       │
                └───────┴───────┘
                        │
                        ▼
            ┌───────────────────────┐
            │  Tag Version          │
            │  docker tag vN        │
            │  docker save > vN.tar │
            └───────────┬───────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │  Document Solution    │
            │  - Write-up           │
            │  - Lessons learned    │
            └───────────────────────┘
```

**Typical cycle time:** 15-30 minutes per iteration  
**Average iterations to solve:** 3-5  
**3-try rule:** Stop after 3 failed attempts, move to different challenge

---

## Race Condition Exploit Flow

### Bill's PC - TOCTOU Vulnerability

```
TIME LINE ──────────────────────────────────────────────────────────▶

Thread 1:  ┌──────┐ ┌──────┐ ┌──────┐         ┌──────┐ ┌──────┐
           │Check │ │Check │ │Sleep │         │ Add  │ │Decr. │
           │Stock │ │Party │ │100ms │         │Ball  │ │Stock │
           └──┬───┘ └──┬───┘ └──────┘         └──────┘ └──────┘
              │        │                           ▲
              │ ✓      │ ✓                         │
              │ =1     │ =0                        │
              │        │                           │
              │        │                           │
Thread 2:     │     ┌──▼───┐ ┌──────┐ ┌──────┐   │     ┌──────┐
              │     │Check │ │Check │ │Sleep │   │     │ Add  │
              │     │Stock │ │Party │ │100ms │   │     │Ball  │
              │     └──┬───┘ └──┬───┘ └──────┘   │     └───┬──┘
              │        │        │                 │         │
              │        │ ✓      │ ✓               │         │
              │        │ =1     │ =0              │         │
              │        │        │                 │         │
              │        │        │                 │         │
Thread 3:     │        │     ┌──▼───┐ ┌──────┐   │         │
              │        │     │Check │ │Check │   │         │
              │        │     │Stock │ │Party │   │         │
              │        │     └──┬───┘ └──┬───┘   │         │
              │        │        │        │        │         │
              │        │        │ ✓      │ ✓      │         │
              │        │        │ =1     │ =0     │         │
              │        │        │        │        │         │
              └────────┴────────┴────────┴────────┴─────────┘
                                                   │
                          ALL PASSED CHECKS!       │
                          But only 1 ball exists   │
                                                   ▼
                                            ┌──────────────┐
                                            │  RESULT:     │
                                            │  Party: [    │
                                            │    Ball 1,   │
                                            │    Ball 2,   │ ← WIN!
                                            │    Ball 3    │
                                            │  ]           │
                                            │  Stock: -2   │
                                            └──────────────┘
```

**Key Insight:** Checks (stock & party) are NOT atomic with modifications. Multiple threads pass checks before any modifies state.

**Exploit:** Fire 20 concurrent POST requests to `/api/withdraw`

---

## Nested SSRF Attack Chain

### Silph Co. - Three-Tier Network Penetration

```
┌─────────────────────────────────────────────────────────────────┐
│  INTERNET (Your Agent)                                          │
│  10.x.x.x                                                       │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ 1. Direct HTTP access
                         │    GET /api/staff/137
                         │
                         ▼
            ┌────────────────────────────┐
            │  LOBBY (Public)            │
            │  10.244.2.100:8080         │
            │                            │
            │  ┌──────────────────────┐  │
            │  │ /api/staff/{id}      │  │
            │  │                      │  │
            │  │ Response:            │  │
            │  │ "...mainframe still  │  │
            │  │  trusts the old key  │  │
            │  │  X-Silph-Key:        │  │
            │  │  SILPH-INTERNAL-..." │  │ ← Extract creds!
            │  └──────────────────────┘  │
            │                            │
            │  ┌──────────────────────┐  │
            │  │ /api/linkcheck?      │  │
            │  │   url=...            │  │
            │  │   header=...         │  │ ← SSRF endpoint
            │  └──────────────────────┘  │
            └────────────┬───────────────┘
                         │
                         │ 2. SSRF via linkcheck
                         │    url=http://mainframe:8080/api/records/2
                         │    header=X-Silph-Key: SILPH-INTERNAL-...
                         │
                         ▼
            ┌────────────────────────────┐
            │  MAINFRAME (Internal)      │
            │  10.244.2.101:8080         │
            │                            │
            │  [NOT SOLVED] Direct access refused  │
            │  [SOLVED] Lobby = trusted source │
            │                            │
            │  ┌──────────────────────┐  │
            │  │ /api/records/{id}    │  │
            │  │                      │  │
            │  │ Response:            │  │
            │  │ {                    │  │
            │  │   "id": 2,           │  │
            │  │   "vault_token":     │  │
            │  │   "X-Vault-Token:    │  │
            │  │    VAULT-OTP-..."    │  │ ← Extract creds!
            │  │ }                    │  │
            │  └──────────────────────┘  │
            │                            │
            │  ┌──────────────────────┐  │
            │  │ /api/linkcheck?      │  │ ← Another SSRF!
            │  └──────────────────────┘  │
            └────────────┬───────────────┘
                         │
                         │ 3. Nested SSRF via lobby→mainframe
                         │    url=http://lobby/api/linkcheck?
                         │      url=http://mainframe/api/linkcheck?
                         │        url=http://vault/vault&
                         │        header=X-Vault-Token: ...
                         │      &header=X-Silph-Key: ...
                         │
                         ▼
            ┌────────────────────────────┐
            │  VAULT (Highly Restricted) │
            │  10.244.2.102:8080         │
            │                            │
            │  [NOT SOLVED] Lobby access refused   │
            │  [NOT SOLVED] Internet access refused│
            │  [SOLVED] Mainframe = trusted!   │
            │                            │
            │  ┌──────────────────────┐  │
            │  │ /vault               │  │
            │  │                      │  │
            │  │ {                    │  │
            │  │   "flag":            │  │
            │  │   "HALCTF{...}"      │  │ ← FLAG! 
            │  │ }                    │  │
            │  └──────────────────────┘  │
            └────────────────────────────┘
```

**Response Wrapping:**
```json
// Outer response (from lobby)
{
  "status": 200,
  "body": "{\"status\":200,\"body\":\"{\\\"flag\\\":\\\"HALCTF{...}\\\"}\"}"
}
```
Must unwrap **twice** to get flag!

---

## Timing Attack Visualization

### Pythia's Whisper - Byte-at-a-Time Token Recovery

```
TARGET TOKEN: "3a7f92e1c8b4d6095e2f" (20 chars, hex)

Position 0: Try all 16 hex characters
┌──────────────────────────────────────────────────────────────┐
│  Character Timing Profile (median of 10 samples)             │
├──────────┬───────────────────────────────────────────────────┤
│  Char    │  Timing (ms)        Graph                         │
├──────────┼───────────────────────────────────────────────────┤
│  '0'     │  45.2  ████████████████████                       │
│  '1'     │  45.3  ████████████████████                       │
│  '2'     │  45.1  ████████████████████                       │
│  '3'     │  47.8  ████████████████████████ ← SLOWEST!        │ ✓
│  '4'     │  45.4  ████████████████████                       │
│  '5'     │  45.0  ████████████████████                       │
│  '6'     │  45.2  ████████████████████                       │
│  '7'     │  45.3  ████████████████████                       │
│  '8'     │  45.1  ████████████████████                       │
│  '9'     │  45.2  ████████████████████                       │
│  'a'     │  45.4  ████████████████████                       │
│  'b'     │  45.1  ████████████████████                       │
│  'c'     │  45.3  ████████████████████                       │
│  'd'     │  45.2  ████████████████████                       │
│  'e'     │  45.0  ████████████████████                       │
│  'f'     │  45.1  ████████████████████                       │
└──────────┴───────────────────────────────────────────────────┘

SELECTED: '3' (2.6ms slower = more chars matched!)

Position 1: Try all 16 with '3' locked in
┌──────────────────────────────────────────────────────────────┐
│  Guess: "3X000000000000000000" (X = candidate)               │
├──────────┬───────────────────────────────────────────────────┤
│  Char    │  Timing (ms)        Graph                         │
├──────────┼───────────────────────────────────────────────────┤
│  '0'     │  45.1  ████████████████████                       │
│  '1'     │  45.2  ████████████████████                       │
│  ...     │  ...                                               │
│  'a'     │  48.1  ████████████████████████ ← SLOWEST!        │ ✓
│  'b'     │  45.3  ████████████████████                       │
│  ...     │  ...                                               │
└──────────┴───────────────────────────────────────────────────┘

SELECTED: 'a' (3.0ms slower!)

Token so far: "3a..." (2/20 characters)

... repeat for remaining 18 positions ...

FINAL TOKEN: "3a7f92e1c8b4d6095e2f"

┌──────────────────────────────────────────────────────────────┐
│  Why This Works:                                             │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Server code:                                                │
│    for i in range(len(token)):                              │
│        if guess[i] != token[i]:                              │
│            return False  ← exits early!                      │
│                                                              │
│  More matches = more iterations = longer time               │
│                                                              │
│  Complexity:                                                 │
│    20 positions × 16 chars × 10 samples = 3,200 requests    │
│    vs brute force: 16^20 = 1,208,925,819,614,629,174,706,176│
└──────────────────────────────────────────────────────────────┘
```

**Statistical Robustness:**
```
Single sample:  [45.1, 51.3, 45.2, 45.3, 45.0, ...]
                       ↑ Network spike (outlier)

Median of 10:   45.2ms ← Robust!
Mean of 10:     45.8ms ← Skewed by outlier
```

---

## LLM Copilot Decision Tree

### When to Use LLM vs Deterministic Code

```
                        ┌─────────────────┐
                        │  New Challenge  │
                        └────────┬────────┘
                                 │
                ┌────────────────┴────────────────┐
                │ Known attack pattern?           │
                └────────┬───────────────┬────────┘
                         │               │
                     ┌───▼────┐      ┌───▼────┐
                     │  YES   │      │  NO    │
                     └───┬────┘      └───┬────┘
                         │               │
            ┌────────────▼──────────┐    │
            │ Use Deterministic     │    │
            │ Solver                │    │
            │                       │    │
            │ - Faster (ms)         │    │
            │ - No token cost       │    │
            │ - Predictable         │    │
            │ - Testable            │    │
            └────────────┬──────────┘    │
                         │               │
                         │               │
                ┌────────▼───────────────▼────────┐
                │ Solver execution                │
                └────────┬───────────────┬────────┘
                         │               │
                     ┌───▼────┐      ┌───▼────┐
                     │SUCCESS │      │ FAILED │
                     └───┬────┘      └───┬────┘
                         │               │
                    ┌────▼─────┐         │
                    │ Submit   │         │
                    │ Flag     │         │
                    └──────────┘         │
                                         │
                                ┌────────▼────────┐
                                │ Retry with fix? │
                                └────────┬────────┘
                                         │
                            ┌────────────┴────────────┐
                            │                         │
                        ┌───▼────┐              ┌────▼────┐
                        │  YES   │              │   NO    │
                        │ (1-2x) │              │ (3x+)   │
                        └───┬────┘              └────┬────┘
                            │                        │
                  ┌─────────▼────────┐               │
                  │ Fix bug, rebuild │               │
                  │ Retry solver     │               │
                  └─────────┬────────┘               │
                            │                        │
                            └───────┐      ┌─────────┘
                                    │      │
                            ┌───────▼──────▼───────┐
                            │ Launch LLM Copilot   │
                            │                      │
                            │ Bounds:              │
                            │ - Max 14 steps       │
                            │ - 5 min timeout      │
                            │ - 2 submits max      │
                            │ - Target-only URLs   │
                            └───────┬──────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
            ┌───────▼────────┐            ┌────────▼────────┐
            │ ReAct Loop     │            │ Tool Execution  │
            │                │            │                 │
            │ 1. Observe     │◄───────────┤ - http_get      │
            │ 2. Think       │            │ - http_post     │
            │ 3. Act         ├───────────►│ - decode        │
            │ 4. Repeat      │            │ - propose_flag  │
            └───────┬────────┘            │ - give_up       │
                    │                     └─────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
    ┌───▼────┐            ┌─────▼──────┐
    │ Found  │            │ No solution│
    │ Flag   │            │ or timeout │
    └───┬────┘            └─────┬──────┘
        │                       │
        ▼                       ▼
   ┌─────────┐           ┌──────────┐
   │ Validate│           │ Log for  │
   │ Format  │           │ manual   │
   │ Submit  │           │ review   │
   └─────────┘           └──────────┘
```

**Decision Matrix:**

| Challenge Type | Use Deterministic | Use LLM Copilot |
|---------------|-------------------|-----------------|
| Race condition | [SOLVED] Always | [NOT SOLVED] Never |
| 3-SAT solving | [SOLVED] Always (pycosat) | [NOT SOLVED] Never |
| ECDSA crypto | [SOLVED] Always (ecdsa lib) | [NOT SOLVED] Never |
| SSRF chain | [SOLVED] Always | [NOT SOLVED] Never |
| Word generation | [NOT SOLVED] Limited list | [SOLVED] Creative variations |
| Crypto analysis | [SOLVED] Try transforms | [SOLVED] Prose reading |
| Unknown web | [NOT SOLVED] No pattern | [SOLVED] Exploration |
| Reverse engineering | [SOLVED] Deobfuscation | [SOLVED] Code understanding |

**Cost Analysis:**

| Approach | Time | Tokens | Success Rate |
|----------|------|--------|--------------|
| Deterministic | <1s | 0 | 95% (when applicable) |
| LLM Bounded | 30-60s | ~5,000 | 60% (unknown challenges) |
| LLM Unbounded | Variable | ∞ | Low (wastes quota) |

**Key Principle:** Use deterministic code whenever possible; LLM for creative/exploratory tasks only.

---

## Stack Buffer Overflow (Achilles' Heel)

```
MEMORY LAYOUT BEFORE OVERFLOW:
┌─────────────────────────────────────┐ Higher addresses
│                                     │
│  Return Address: 0x00000000004012a3 │ ← Target for overwrite
├─────────────────────────────────────┤
│  Saved RBP: 0x00007ffd8b3e2a10     │
├─────────────────────────────────────┤
│  Buffer [72 bytes]                  │
│  [0]: 0x00                          │
│  [1]: 0x00                          │
│  ...                                │
│  [71]: 0x00                         │
├─────────────────────────────────────┤
│  Local variables                    │
│                                     │ Lower addresses
└─────────────────────────────────────┘

MEMORY LAYOUT AFTER OVERFLOW:
┌─────────────────────────────────────┐
│                                     │
│  Return Address: 0x00000000004011d6 │ ← win() function!
├─────────────────────────────────────┤
│  Saved RBP: 0x4141414141414141     │ ← Overwritten
├─────────────────────────────────────┤
│  Buffer [72 bytes]                  │
│  [0-71]: 0x41 ('A' padding)         │
│                                     │
│                                     │
├─────────────────────────────────────┤
│  Local variables                    │
│                                     │
└─────────────────────────────────────┘

EXPLOIT PAYLOAD STRUCTURE:
┌──────────────────┬─────────┬──────────────────┐
│  'A' × 72 bytes  │ 'A' × 8 │  win() address   │
│  (buffer fill)   │ (RBP)   │  (return addr)   │
└──────────────────┴─────────┴──────────────────┘
       Padding                    0x4011d6

CONTROL FLOW HIJACK:
  Normal:    main() → hello() → [return to main] → exit
                                       ↑
  Exploited: main() → hello() → [return to win()] → system("/bin/cat flag.txt")
                                       ↑
                               Overwritten address!
```

---

## Docker Multi-Stage Build Optimization

```
┌─────────────────────────────────────────────────────────────────┐
│                    STAGE 1: BUILDER                             │
│                    FROM python:3.11-slim                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  Install build dependencies:                           │   │
│  │  - gcc (C compiler)                                    │   │
│  │  - g++ (C++ compiler)                                  │   │
│  │  - make                                                │   │
│  │                                                        │   │
│  │  Total size: ~400MB                                    │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  Build Python wheels:                                  │   │
│  │  - pycosat (needs gcc, no wheels available)           │   │
│  │  - Other dependencies                                  │   │
│  │                                                        │   │
│  │  Output: /wheels/*.whl                                 │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                                │
                                │ COPY wheels only
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STAGE 2: RUNTIME                             │
│                    FROM python:3.11-slim                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  Install runtime dependencies ONLY:                    │   │
│  │  - binutils (for binary analysis)                      │   │
│  │                                                        │   │
│  │  Total size: ~150MB                                    │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  Install pre-built wheels:                             │   │
│  │  pip install /wheels/*                                 │   │
│  │                                                        │   │
│  │  No gcc needed!                                        │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  Copy application code                                 │   │
│  │  COPY . /agent                                         │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                 │
│                    FINAL SIZE: 172MB [SOLVED]                         │
└─────────────────────────────────────────────────────────────────┘

SIZE COMPARISON:
┌──────────────────────────┬──────────┬──────────┐
│  Approach                │  Size    │  Savings │
├──────────────────────────┼──────────┼──────────┤
│  Single stage (with gcc) │  415 MB  │  -       │
│  Multi-stage build       │  172 MB  │  243 MB  │
│  Percent reduction       │  -58%    │  [SOLVED]      │
└──────────────────────────┴──────────┴──────────┘
```

---

## Usage

These diagrams are referenced throughout the write-ups:
- [Hac-Man](./hacman.md) - LLM word generation architecture
- [Kanto Region](./kanto.md) - Race condition, SSRF, and ECDSA diagrams
- [Turing's Labyrinth](./labyrinth.md) - Multi-solver architecture, timing attack
- [Lessons Learned](./lessons-learned.md) - All diagrams used in context

**ASCII Art Note:** These diagrams are designed to render correctly in monospace fonts on GitHub, terminals, and text editors.
