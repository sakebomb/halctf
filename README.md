# HalCTF Autonomous Agent

[![DEF CON 34](https://img.shields.io/badge/DEF%20CON-34-red)](https://defcon.org)
[![AI Village](https://img.shields.io/badge/AI%20Village-HalCTF-blue)](https://aivillage.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Competition Result](https://img.shields.io/badge/Ranking-13th%20Place-green)](./changelog.md)

Production-ready autonomous CTF agent for DEF CON 34 / AI Village HalCTF competition. This repository documents the design, implementation, and solutions for multiple challenge categories including Hac-Man, Kanto Region (450 points), The Odyssey, Turing's Labyrinth, and Rogue Intelligence.

**[Read the Complete Write-ups](./docs/writeups/README.md)** - Detailed solutions for all solved challenges with technical analysis and lessons learned.

## Competition Results

- **Final Ranking**: 13th Place
- **Challenges Solved**: Hac-Man, Kanto Region (Bill's PC), Rogue Intelligence, partial solutions for The Odyssey and Turing's Labyrinth
- **Notable Achievement**: 450-point Kanto Region full solve (all three sub-challenges)

## Security Notice

**This repository contains CTF competition code designed for sandboxed environments.** Some agents intentionally use patterns that would be unsafe in production:

- `exec()` on LLM-generated code (Odyssey Bow challenge)
- Dynamic execution of downloaded scripts (Labyrinth Gatekeeper)
- Shell command execution for exploit development

These patterns are appropriate for CTF agents running in isolated containers with no access to sensitive data or production systems. **Do not use these patterns in production applications.** For production LLM applications, use structured outputs, validated DSLs, and sandboxed execution environments.

## Repository Overview

This repository contains:
- **Multiple specialized agents** for different challenge categories
- **Comprehensive writeups** documenting solutions and techniques
- **Reusable frameworks** for CTF automation (ReAct loop, MCP integration, LLM-guided exploration)
- **Deployment guides** for running agents in the HalCTF environment

## Features

### Core Capabilities
- Compliant with HalCTF requirements (USER ID print, heartbeat, graceful shutdown)
- Autonomous ReAct-style reasoning loop using LLM + tool execution
- Full MCP integration for challenge discovery and flag submission
- Shell command execution with timeout and output limits
- Conversation memory management with context compaction
- Robust retry logic with exponential backoff
- Intelligent challenge selection based on point value
- Environment variable scanning for free flags
- Comprehensive logging with heartbeat compliance

### Security & Reliability
- Runs as non-root user
- No hardcoded secrets or API keys
- Input validation on all MCP calls
- Output truncation to prevent memory issues
- Retry logic with exponential backoff
- Graceful degradation if services unavailable
- Error handling at every network boundary

## Quick Start

### Building an Agent

Each challenge has its own specialized agent in the `agents/` directory:

```bash
# Example: Build the Kanto agent
cd agents/kanto
docker build -t kanto-agent .

# Save as tarball for upload
docker save kanto-agent:latest > kanto-agent.tar
```

### Upload to HalCTF Platform

Upload the generated `.tar` file to [https://halctf.aivillage.org](https://halctf.aivillage.org)

### Local Development & Testing

Use the included test harness to develop and debug locally:

```bash
python3 scripts/test_harness.py
```

This will:
- Mock the OPENAI_BASE_URL endpoint
- Mock the MCP_ENDPOINT endpoint
- Set required environment variables
- Run your agent in a simulated environment

See [docs/guides/deployment-guide.md](docs/guides/deployment-guide.md) for detailed instructions.

## Architecture

### Core Components

1. **HalCTFAgent** - Main orchestrator
2. **MCPClient** - Interface to Model Context Protocol server
3. **ShellExecutor** - Safe command execution with timeouts
4. **ConversationMemory** - Manages LLM conversation history
5. **LLM Integration** - OpenAI-compatible chat interface

### Execution Flow

```
Startup
  ├─ Print USER ID (CRITICAL - within 30s)
  ├─ Scan environment for flags
  └─ Submit any found flags immediately

Main Loop
  ├─ Fetch available challenges via MCP
  ├─ Select highest-value unsolved challenge
  ├─ Initialize conversation with challenge details
  └─ ReAct Loop (max 20 iterations)
      ├─ Call LLM with current context
      ├─ Parse action from LLM response
      ├─ Execute action (shell, MCP, or meta-action)
      ├─ Append result to conversation
      └─ Check for completion or flag submission
  
Shutdown
  └─ POST to http://127.0.0.1:9000/done
```

### LLM Tool Actions

The agent supports these JSON action formats:

```json
{"action": "shell", "command": "nmap -p- 192.168.1.1"}
{"action": "mcp_list_challenges"}
{"action": "mcp_get_challenge", "challenge_id": 123}
{"action": "mcp_submit_flag", "challenge_id": 123, "flag": "flag{...}"}
{"action": "mcp_request_hint", "challenge_id": 123, "hint_index": 0}
{"action": "think", "thought": "I should try SQL injection"}
{"action": "done", "reason": "All challenges solved"}
```

## Challenge Solutions

### Hac-Man (50 points)
LLM-guided discovery of magic word "WakaWaka" through chat endpoint exploration.
- [Writeup](./docs/writeups/hacman.md)
- [Agent Code](./agents/hacman/)

### Kanto Region (450 points)
Multi-puzzle challenge requiring SAT solving, ECDSA signature forgery, and nested SSRF.
- [Writeup](./docs/writeups/kanto.md)
- [Agent Code](./agents/kanto/)

### Rogue Intelligence
Multi-layer LLM jailbreaking with rotating flags and quota management.
- [Writeup](./docs/writeups/rogue-intelligence.md)
- [Agent Code](./agents/rogue/)

### The Odyssey
Five unlocked puzzles including SSRF, XOR, majority vote, binary search, and pagination.
- [Writeup](./docs/writeups/odyssey.md)
- [Agent Code](./agents/odyssey/)

### Turing's Labyrinth
Nine puzzles with LLM-in-loop solvers and specialized logic.
- [Writeup](./docs/writeups/labyrinth.md)
- [Agent Code](./agents/labyrinth/)

### Lessons Learned
Comprehensive retrospective on what worked, what didn't, and key takeaways.
- [Lessons Learned](./docs/writeups/lessons-learned.md)

## Project Structure

```
.
├── agents/              # Specialized agents for each challenge
│   ├── hacman/         # Hac-Man agent
│   ├── kanto/          # Kanto Region agent (Bill's PC)
│   ├── labyrinth/      # Turing's Labyrinth agent
│   ├── odyssey/        # The Odyssey agent
│   ├── rogue/          # Rogue Intelligence agent
│   └── pantheon/       # Pantheon agent (in progress)
├── docs/
│   ├── guides/         # Deployment and development guides
│   ├── requirements/   # HalCTF platform requirements
│   └── writeups/       # Detailed challenge solutions
├── scripts/            # Build, test, and monitoring utilities
├── archive/            # Legacy code and experiments
├── LICENSE             # MIT License
├── changelog.md        # Competition timeline and milestones
└── README.md           # This file
```

## Documentation

- **[Quick Start Guide](./docs/guides/quickstart.md)** - Get up and running quickly
- **[Deployment Guide](./docs/guides/deployment-guide.md)** - Detailed deployment instructions
- **[HalCTF Reference](./docs/guides/halctf-reference.md)** - Platform-specific details
- **[New CTF Playbook](./docs/guides/new-ctf-playbook.md)** - Approach for tackling new challenges
- **[Requirements Checklist](./docs/requirements/checklist.md)** - Compliance verification

## Configuration

### Model Selection

Default model: `llama-3.1-8b` (efficient and fast)

Supported models:
- `llama-3.1-8b` - Best for cost/efficiency
- `qwen3.6-35b-a3b` - Medium capability
- `google/gemma-4-26b-a4b-it-maas` - Higher capability (256K context, unlimited)

Change model in `agent.py`:
```python
self.model = 'qwen3.6-35b-a3b'  # Or your preferred model
```

### Safety Limits

- **Max output size**: 50KB per command
- **Command timeout**: 60 seconds
- **Max conversation messages**: 30 (with compaction)
- **Max iterations per challenge**: 20
- **Max challenges per run**: 10

## Environment Variables

These are injected by the HalCTF platform at runtime:

| Variable | Purpose |
|----------|---------|
| `HAL_USER_ID` / `USER_ID` | **REQUIRED** - Your user identifier |
| `OPENAI_BASE_URL` | OpenAI-compatible chat endpoint |
| `MCP_ENDPOINT` | Model Context Protocol server |
| `BONUS_FLAG` | Free flag for quick points |
| `FLAG_*` | Challenge-specific flags |
| `HAL_TARGET_IP` | Target IP address |
| `HAL_TARGET_PORT` | Target port |
| `HAL_CHALLENGE_ID` | Current challenge ID |
| `HAL_MCP_HINT` | Helpful MCP usage hint |

## Troubleshooting

### Agent killed after ~2 minutes

**Problem**: Agent not producing output frequently enough.

**Solution**: The agent includes automatic heartbeat logging every 60s. If your LLM calls take longer, reduce timeout or increase heartbeat frequency.

### USER ID not printed

**Problem**: Startup taking too long.

**Solution**: The agent prints USER ID immediately in `startup_checks()`. Ensure Docker image builds correctly and runs without errors.

### Network timeouts

**Problem**: Cannot reach MCP or LLM endpoint.

**Solution**: Verify network is restricted to `127.0.0.1:9000` and challenge target subnets only. No public internet access.

### Image too large

**Problem**: Docker image exceeds ~2.5GB limit.

**Solution**: Use multi-stage builds (see Kanto agent: 415MB → 172MB reduction). Remove unnecessary packages and use slim base images.

## Competition Strategy

1. **Quick wins first**: Scan environment variables for free flags
2. **High value targets**: Prioritize challenges by points
3. **Methodical approach**: Full reconnaissance before exploitation
4. **Persistent attempts**: Up to 20 iterations per challenge
5. **Learn from failures**: Uses conversation history to avoid repeating mistakes

## Contributing

Contributions are welcome! See [contributing.md](./contributing.md) for guidelines.

## License

This project is licensed under the MIT License - see [LICENSE](./LICENSE) for details.

## Acknowledgments

- DEF CON 34 / AI Village for hosting HalCTF
- The CTF community for inspiration and techniques
- OpenAI-compatible LLM providers used during the competition

## Contact

- GitHub: [@sakebomb](https://github.com/sakebomb)
- Competition: DEF CON 34 / AI Village HalCTF (August 2026)

---

**Note**: This repository is for educational purposes. The challenges and solutions are documented to help others learn about autonomous agent development, CTF techniques, and LLM-guided problem solving.
