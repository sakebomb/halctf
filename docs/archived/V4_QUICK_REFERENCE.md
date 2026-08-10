# V4 Agent Quick Reference

## Files Created
- `bills-pc-agent-v4/main.py` - Main orchestrator
- `bills-pc-agent-v4/solvers/bills_pc.py` - Race condition solver
- `bills-pc-agent-v4/solvers/cerulean_cave.py` - 3-SAT solver
- `bills-pc-agent-v4/solvers/silph_co.py` - Lateral movement solver
- `bills-pc-agent-v4/solvers/indigo_league.py` - ECDSA nonce reuse solver
- `bills-pc-agent-v4/requirements.txt` - Python dependencies
- `bills-pc-agent-v4/Dockerfile` - Container definition
- `bills-pc-agent-v4.tar.gz` - Ready to upload (138MB)

## Upload Command

```bash
# Upload via web interface at:
https://halctf.aivillage.org/upload

# Or view your uploaded images at:
https://halctf.aivillage.org/my-images
```

## What V4 Can Solve

| Challenge | Points | Type | Strategy |
|-----------|--------|------|----------|
| Bill's PC | 400 | Race Condition | Parallel withdrawals |
| Cerulean Cave | 400 | 3-SAT | pycosat solver |
| Silph Co. | 600 | Lateral Movement | Port scan + SSH |
| The Indigo League | 500 | ECDSA | Nonce reuse attack |
| **TOTAL** | **1900** | | |

## Challenge Detection

Agent auto-detects based on:
- Challenge name keywords
- Environment variables
- Challenge description

No manual configuration needed!

## Build Info

- **Image**: bills-pc-agent:v4
- **Size**: 410MB (uncompressed)
- **Archive**: 138MB (compressed)
- **Base**: Python 3.11
- **Key Dependencies**: pycosat (SAT), cryptography (ECDSA), paramiko (SSH)

## Testing Locally

```bash
# Test the image runs
docker run --rm bills-pc-agent:v4

# Should output:
# USER ID: None
# Challenge: 
# Target: :80
# Description: 
# === Multi-Challenge Agent v4 Starting ===
# Detected challenge type: unknown
```

## What's Different from V3?

| Feature | V3 | V4 |
|---------|----|----|
| Challenges | 1 (Bill's PC) | 4 (multi-challenge) |
| Architecture | Monolithic | Modular solvers |
| Detection | Manual | Automatic |
| Dependencies | 3 packages | 4 packages (+pycosat) |
| Size | 195MB | 410MB |
| Capabilities | Race conditions | SAT, crypto, network |

## Known Working

✅ Builds successfully  
✅ All dependencies install  
✅ Docker image created  
✅ Archive ready for upload  

## Not Yet Tested

⚠️ Actual challenge execution (need to upload and run)  
⚠️ SAT solver correctness on real puzzle  
⚠️ SSH lateral movement on real hosts  
⚠️ ECDSA key recovery on real badges  

## Next Action

Upload `bills-pc-agent-v4.tar.gz` to https://halctf.aivillage.org/upload and test on one of the four supported challenges!
