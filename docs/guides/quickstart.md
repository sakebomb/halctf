# HalCTF Agent - Quick Start Guide

## 🚀 Build & Deploy (Fast Path)

```bash
# 1. Build the Docker image and save as tarball
./build.sh

# 2. Upload agent.tar to HalCTF platform
# Visit: https://halctf.aivillage.org
# Upload: agent.tar

# Done! Your agent will start automatically when the competition begins.
```

## 🧪 Local Testing (Optional)

### Option 1: With Test Harness (Recommended)

```bash
# Install Python dependencies
pip install -r requirements.txt

# Run mock environment
python3 test_harness.py
```

This starts mock servers for:
- OpenAI-compatible LLM endpoint (port 8000)
- MCP endpoint (port 8001)
- Sidecar endpoint (port 9000)

### Option 2: Docker Local Test

```bash
# First, start test harness in one terminal
python3 test_harness.py

# Then, in another terminal:
./test_local.sh
```

## 📝 Customize the Agent

### Change LLM Model

Edit `agent.py`, line ~359:

```python
self.model = 'llama-3.1-8b'          # Fast, efficient (default)
# self.model = 'qwen3.6-35b-a3b'     # Medium capability
# self.model = 'google/gemma-4-26b-a4b-it-maas'  # Higher capability
```

### Adjust Challenge Limits

Edit `agent.py`:

```python
# Line ~454 - iterations per challenge
max_iterations: int = 20

# Line ~499 - max challenges to attempt
max_challenges = 10
```

### Modify System Prompt

Edit `agent.py`, `ConversationMemory._build_system_prompt()` method (line ~145).

## 🔍 Troubleshooting

### Image won't build

```bash
# Check Docker is running
docker ps

# Check for syntax errors
python3 -m py_compile agent.py

# Rebuild from scratch
docker build --no-cache -t halctf-agent .
```

### Agent killed after 2 minutes

- Heartbeat interval is set to 60 seconds (automatic)
- If LLM calls exceed 60s, increase heartbeat frequency in `agent.py`

### No USER ID printed

- Check agent.py `startup_checks()` method runs immediately
- Verify environment variable HAL_USER_ID or USER_ID is set

### Network timeouts

- Platform restricts network to:
  - 127.0.0.1:9000 (sidecar)
  - Challenge target subnets only
- NO public internet access

## 📊 Platform Limits

| Limit | Value |
|-------|-------|
| Image size | ~2.5 GB max |
| Startup time | 30s to print USER ID |
| Heartbeat | Output every 90s |
| Network | Restricted (no internet) |

## 🎯 Competition Tips

1. **Fast wins first**: Agent scans environment variables for flags on startup
2. **High value targets**: Prioritizes challenges by points
3. **Persistent**: Up to 20 attempts per challenge with full LLM reasoning
4. **Efficient**: Uses smallest viable model (llama-3.1-8b) for speed/cost
5. **Defensive**: Comprehensive error handling and retry logic

## 📁 File Overview

```
.
├── agent.py            # Main agent (ReAct loop + MCP integration)
├── requirements.txt    # Python dependencies
├── Dockerfile         # Container definition
├── build.sh           # Build helper script
├── test_local.sh      # Local Docker test script
├── test_harness.py    # Mock server for offline dev
├── README.md          # Full documentation
└── QUICKSTART.md      # This file
```

## 🆘 Need Help?

- **Agent code issues**: Check agent.py comments and README.md
- **Platform issues**: Visit https://halctf.aivillage.org
- **Docker issues**: `docker logs <container>` for debugging

## 📚 Further Reading

- Full documentation: [README.md](README.md)
- HalCTF platform: https://halctf.aivillage.org
- DEF CON AI Village: https://aivillage.org

---

**Good luck at DEF CON 34! 🏴‍☠️**
