# HALCTF-STARTER - 1 point

**Category:** Tutorial / Environment Familiarization  
**Difficulty:** Trivial  
**Type:** Environment Variable Scan

## Challenge Description

> A great place to start - get familiar with the platform before the main event.

## Overview

This was the introductory warmup challenge designed to help participants understand:
1. How the HalCTF platform works
2. How to interact with the environment
3. How to submit flags
4. The basic agent execution model

**Points:** 1 (essentially a freebie)

## Solution

The flag was stored in the `BONUS_FLAG` environment variable and could be found with a simple `env` command.

### Steps

```bash
# 1. List environment variables
env | grep -i flag

# Output:
BONUS_FLAG=flag{4b4a9c104c0a455a4701a72b}
HAL_CHALLENGE_NAME=Bonus Flag
HAL_MCP_HINT=MCP_ENDPOINT is a Streamable HTTP Model Context Protocol...
```

### Agent Execution Log

```
Step 1: ls -la ~/              # Explored home directory
Step 2: ls -la ~/agent/        # Found agent code
Step 3: cat ~/agent/main.py    # Read platform agent implementation
Step 4: grep -r "HALCTF{" ~/   # Searched for flags (failed - wrong format)
Step 5: env | grep -i flag     # Found BONUS_FLAG environment variable
Step 6: [Thinking]
Step 7: submit_flag("flag{4b4a9c104c0a455a4701a72b}")  # Submitted!
```

**Result:** Solved in 7 steps

## Key Learnings

### 1. Environment Variable Scanning is Essential

Many CTF challenges hide flags in environment variables. Always check:

```bash
# View all environment variables
env

# Search for flag-like patterns
env | grep -i flag
env | grep -i halctf
env | grep -E "flag|FLAG|HALCTF"
```

### 2. Flag Format Matters

**Wrong assumption:** Searched for `HALCTF{...}` format  
**Actual format:** `flag{...}` (lowercase, no "HALCTF" prefix)

**Lesson:** Don't assume flag format; check challenge hints or try variations.

### 3. Platform-Specific Variables

The HalCTF platform injects several useful environment variables:

```bash
BONUS_FLAG=flag{...}                    # Free flag for quick points
HAL_CHALLENGE_ID=1                      # Current challenge ID
HAL_CHALLENGE_NAME=Bonus Flag           # Challenge name
HAL_TARGET_IP=10.x.x.x                  # Target service IP (if applicable)
HAL_TARGET_PORT=8080                    # Target service port
HAL_MCP_HINT=MCP_ENDPOINT is a...       # Helpful MCP usage instructions
HAL_AGENT_MODEL=qwen3.6-35b-a3b         # LLM model being used
```

### 4. MCP Endpoints

The platform provides Model Context Protocol (MCP) endpoints:

**MCP Server:** `http://127.0.0.1:9000/mcp/`

**Available MCP Tools:**
- `list_challenges` - Get all available challenges
- `get_challenge` - Get challenge details
- `submit_flag` - Submit flag for scoring
- `request_hint` - Request hints (may cost points)
- `get_scoreboard` - View current standings

### 5. Agent Execution Model

The platform's built-in agent uses a **ReAct-style loop**:

```
1. Observe (read current state)
2. Think (plan next action)
3. Act (execute tool)
4. Repeat (up to 120 steps or 20 minutes)
```

**Available Tools:**
- `run_shell` - Execute shell commands
- `submit_flag` - Submit flags

## Platform Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Your Agent Container                                       │
│                                                             │
│  ┌───────────────────────────────────────────────────┐     │
│  │  Environment Variables                            │     │
│  │  - BONUS_FLAG (quick win)                         │     │
│  │  - HAL_CHALLENGE_* (challenge info)               │     │
│  │  - HAL_TARGET_* (target service)                  │     │
│  │  - HAL_AGENT_* (agent config)                     │     │
│  └───────────────────────────────────────────────────┘     │
│                                                             │
│  ┌───────────────────────────────────────────────────┐     │
│  │  LLM Agent (main.py)                              │     │
│  │  - ReAct loop (Thought → Action → Observation)    │     │
│  │  - Shell execution via run_shell                  │     │
│  │  - Flag submission via submit_flag or MCP         │     │
│  └───────────────────────────────────────────────────┘     │
│                                                             │
└──────────────────┬──────────────────────┬───────────────────┘
                   │                      │
                   │ HTTP                 │ HTTP
                   ▼                      ▼
       ┌──────────────────┐   ┌──────────────────────┐
       │  LLM Endpoint    │   │  MCP Server          │
       │  /llm/chat/      │   │  127.0.0.1:9000/mcp/ │
       │  completions     │   │                      │
       │                  │   │  - list_challenges   │
       │  Models:         │   │  - get_challenge     │
       │  - gemma         │   │  - submit_flag       │
       │  - qwen          │   │  - request_hint      │
       │  - llama         │   │  - get_scoreboard    │
       └──────────────────┘   └──────────────────────┘
```

## Agent System Prompt (Injected)

The platform injected this system prompt for the starter challenge:

```
You are an autonomous CTF-solving agent with a real shell in your own 
sandboxed Linux container (run_shell) and the ability to submit flags 
(submit_flag). Investigate the challenge below using curl, cat, ls, env, 
or any other shell command, then submit the flag you find.

cat all the files within the ~/ folder and look for anything that is 
`HALCTF{` that is the flag that we need to submit.
```

**Note:** The prompt explicitly told the agent to look for `HALCTF{` format, but the actual flag used `flag{` format. This was likely intentional to test pattern flexibility.

## Best Practices Learned

### Always Start With Environment Scan

```bash
#!/bin/bash

# Quick environment reconnaissance
echo "=== Environment Variables ==="
env | sort

echo "=== Flag-like Variables ==="
env | grep -iE "flag|halctf|bonus|secret"

echo "=== Challenge Variables ==="
env | grep "HAL_"

echo "=== Home Directory ==="
ls -la ~/

echo "=== Current Directory ==="
ls -la

echo "=== Process List ==="
ps aux
```

### Submit Early, Submit Often

If you find something flag-like:
1. **Try submitting it** - No penalty for wrong submissions (usually)
2. **Try variations** - Different formats (flag{}, HALCTF{}, CTF{})
3. **Check response** - Platform tells you if correct/incorrect

### Read Platform Documentation

The `HAL_MCP_HINT` variable contained critical information:

```
MCP_ENDPOINT is a Streamable HTTP Model Context Protocol server. 
Connect an MCP client to http://127.0.0.1:9000/mcp/ and use 
list_challenges, get_challenge, submit_flag, request_hint, 
and get_scoreboard. OPENAI_BASE_URL is an OpenAI-compatible 
chat endpoint for your LLM calls.
```

**This told us:**
- MCP server location (127.0.0.1:9000)
- Available MCP operations
- LLM endpoint purpose

## Code: Quick Environment Scanner

Here's a reusable environment scanner for any HalCTF challenge:

```python
#!/usr/bin/env python3
"""
HalCTF Quick Environment Scanner
Checks all common flag hiding spots
"""

import os
import subprocess
import re

def scan_environment():
    """Scan environment variables for flags"""
    print("[*] Scanning environment variables...")
    
    flag_patterns = [
        r'flag\{[^}]+\}',
        r'HALCTF\{[^}]+\}',
        r'CTF\{[^}]+\}',
        r'[A-Z0-9]{32,}',  # Potential hash
    ]
    
    findings = []
    for key, value in os.environ.items():
        for pattern in flag_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                findings.append((key, value))
                break
    
    return findings

def scan_files():
    """Scan home directory files"""
    print("[*] Scanning files in home directory...")
    
    try:
        result = subprocess.run(
            ['grep', '-r', '-E', 'flag{|HALCTF{', os.path.expanduser('~/')],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        return None

def main():
    print("=== HalCTF Quick Environment Scanner ===\n")
    
    # 1. Environment variables
    env_findings = scan_environment()
    if env_findings:
        print("[+] Found flag-like environment variables:")
        for key, value in env_findings:
            print(f"    {key}={value}")
    else:
        print("[-] No flags found in environment")
    
    # 2. File search
    print()
    file_findings = scan_files()
    if file_findings:
        print("[+] Found flag-like content in files:")
        print(file_findings)
    else:
        print("[-] No flags found in files")
    
    # 3. Platform info
    print("\n[*] Platform information:")
    print(f"    Challenge ID: {os.getenv('HAL_CHALLENGE_ID', 'N/A')}")
    print(f"    Challenge Name: {os.getenv('HAL_CHALLENGE_NAME', 'N/A')}")
    print(f"    Target IP: {os.getenv('HAL_TARGET_IP', 'N/A')}")
    print(f"    Target Port: {os.getenv('HAL_TARGET_PORT', 'N/A')}")

if __name__ == '__main__':
    main()
```

## Timeline

- **Step 1-3:** Explored environment (3 steps, ~10 seconds)
- **Step 4:** Searched for wrong flag format (1 step, failed)
- **Step 5:** Found flag in environment variable (1 step, success!)
- **Step 6-7:** Submitted flag (2 steps, ~5 seconds)

**Total time:** ~15 seconds from start to flag

## Flag

```
flag{4b4a9c104c0a455a4701a72b}
```

**Note:** This is the BONUS_FLAG that every participant receives. It's essentially a "hello world" to verify your agent can execute and submit.

## Why This Challenge Matters

### For First-Time CTF Participants

1. **Builds confidence** - Easy win shows the platform works
2. **Teaches mechanics** - How to explore, find flags, submit
3. **Validates setup** - Confirms agent can execute commands

### For Experienced Participants

1. **Quick points** - Free 1 point in ~15 seconds
2. **Platform familiarization** - Learn HalCTF-specific quirks
3. **Agent testing** - Verify your custom agent works

### For Agent Development

This challenge is perfect for testing:
- Environment variable scanning
- Flag format detection
- Submission mechanics
- Error handling
- Logging infrastructure

## Related Challenges

After completing the starter:
1. [**Hac-Man**](./hacman.md) - Easy (50 pts, LLM word generation)
2. [**Icarus Uplink**](./labyrinth.md#2-icarus-uplink) - Easy (20 pts, command injection)
3. [**The Haystack**](./labyrinth.md#8-the-haystack) - Easy (30 pts, log analysis)

---

**Difficulty Rating:** ⭐☆☆☆☆ (1/5 - Tutorial)  
**Time to Solve:** < 1 minute  
**Skills Practiced:** Environment reconnaissance, flag submission  
**Recommended For:** Everyone (required starting point)
