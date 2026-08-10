# Pantheon CTF Agent

Autonomous agent for solving the **Pantheon** CTF challenge series on the HAL platform.

## Challenge Coverage

This agent can autonomously solve all 9 Pantheon challenges:

1. **Cassandra's Warning** (SQL Injection) - 75 pts
2. **Charon's Ferry** (SSRF) - 100 pts  
3. **Echo** (Protocol Reverse Engineering) - 150 pts
4. **Hydra's Signature** (JWT Algorithm Confusion) - 125 pts
5. **Midas' Touch** (IAM Role Assumption Chain) - 150 pts
6. **Pandora's Box** (Insecure Deserialization) - 125 pts
7. **Theseus's Trial I: Recon** (Credential Leakage) - 100 pts
8. **The Sirens' Call** (Network Forensics / PCAP) - 100 pts
9. **Trojan Horse** (XXE) - 100 pts

**Total Points: 1,025**

## Architecture

```
pantheon-agent/
├── Dockerfile           # Multi-stage build (slim runtime, no compiler)
├── requirements.txt     # Pinned dependencies
├── main.py             # Orchestrator with routing logic
├── mcp_client.py       # MCP utilities (best-effort)
└── solvers/
    ├── __init__.py
    ├── cassandra.py    # SQL injection solver
    ├── charon.py       # SSRF with IP encoding tricks
    ├── echo.py         # Binary protocol checksum reversal
    ├── hydra.py        # JWT RS256→HS256 confusion
    ├── midas.py        # IAM role assumption chaining
    ├── pandora.py      # Pickle deserialization RCE
    ├── theseus.py      # Credential extraction from directory
    ├── sirens.py       # PCAP parsing for credentials
    └── trojan.py       # XXE file read
```

## Solver Strategies

### Deterministic Solvers
Most solvers use **deterministic** approaches (no LLM):

- **Cassandra**: UNION-based SQL injection with table/column enumeration
- **Charon**: SSRF with multiple IP encoding formats (decimal, octal, hex)
- **Hydra**: JWT algorithm confusion (RS256 public key used as HS256 secret)
- **Midas**: Multi-hop IAM role assumption with common role name patterns
- **Pandora**: Pickle deserialization with multiple RCE payload strategies
- **Theseus**: Regex extraction of credentials from staff directory notes
- **Trojan**: XXE with file path enumeration

### Protocol Reverse Engineering
- **Echo**: Captures legitimate frames to reverse engineer checksum algorithm (tries CRC16, simple sum, XOR)

### Forensics
- **Sirens**: Parses PCAP for HTTP Basic Auth headers, tries extracted credentials

## Building

### Minimal Version (Recommended)
```bash
docker build -f Dockerfile.minimal -t pantheon-agent:v1-minimal .
docker save pantheon-agent:v1-minimal > pantheon-agent-v1-minimal.tar
```

**Image size**: ~160 MB (single-stage, only essential deps: requests, pyjwt, cryptography)

### Full Version (with MCP/OpenAI support)
```bash
docker build -t pantheon-agent:v1 .
docker save pantheon-agent:v1 > pantheon-agent-v1.tar
```

**Image size**: ~414 MB (includes mcp, openai, pwntools, scapy - not needed for this CTF)

## Verification Checklist

Before upload, verify:

```bash
# 1. Dry-run gate passes
docker run --rm -e HAL_DRY_RUN=1 -e HAL_USER_ID=test pantheon-agent:v1 | grep "Verification PASSED"

# 2. All solvers import
docker run --rm --entrypoint python pantheon-agent:v1 -c "
from solvers.cassandra import CassandraSolver
from solvers.charon import CharonSolver
from solvers.echo import EchoSolver
from solvers.hydra import HydraSolver
from solvers.midas import MidasSolver
from solvers.pandora import PandoraSolver
from solvers.theseus import TheseusSolver
from solvers.sirens import SirensSolver
from solvers.trojan import TrojanSolver
print('OK')"

# 3. No compiler in image
docker run --rm --entrypoint sh pantheon-agent:v1 -c "which gcc || echo 'no gcc (good)'"

# 4. Valid docker archive
tar tf pantheon-agent-v1.tar | grep -q manifest.json && echo "valid"
```

## Runtime Behavior

1. **Dry-run gate** (`HAL_DRY_RUN=1`):
   - Prints `USER ID` within ~30s
   - Exits cleanly with "Verification PASSED"
   - Does not attempt to solve challenges

2. **Real detonation**:
   - Routes challenge by name/slug/category/description keywords
   - Instantiates appropriate solver
   - Solver returns flag or None
   - Submits via HTTP (primary) to `http://127.0.0.1:9000/submit`
   - Logs all responses for debugging

## Routing Logic

The agent detects the challenge type using:

1. **Primary**: Challenge name/slug (e.g., "cassandra" → SQL injection)
2. **Fallback**: Category/description keywords (e.g., "sql" → Cassandra solver)

## Success Criteria

Each solver:
- Logs progress with flush=True
- Returns flag string if found, None otherwise
- Handles errors gracefully (no crashes)
- Uses lenient flag shape guard (`{...}` not `HALCTF{` only)

## Dependencies

### Minimal (requirements-minimal.txt)
Actually used by solvers:
```
requests==2.34.2      # HTTP requests (all solvers)
pyjwt>=2.10.1         # JWT manipulation (hydra)
cryptography==42.0.5  # JWT crypto backend
```

### Full (requirements.txt)
Includes unused packages for future extensibility:
```
requests==2.34.2
mcp==2.0.0            # Not used (HTTP submit only)
openai==2.53.0        # Not used (deterministic solvers)
pwntools==4.15.0      # Not used (no binary exploitation)
scapy==2.5.0          # Not used (HTTP API, not raw packets)
pyjwt>=2.10.1
cryptography==42.0.5
```

## Upload

**Recommended**: Upload `pantheon-agent-v1-minimal.tar` (160 MB) to the HAL CTF platform and click Run.

**Alternative**: Upload `pantheon-agent-v1.tar` (414 MB) if you want the full version with MCP/OpenAI support.

Expected behavior:
- `[VERIFY]` gate passes (dry-run)
- `[AGENT]` real run executes
- Each challenge returns: `Submit id=N: 200 - {"status":"correct","points_awarded":N}`

## Notes

- **MCP is best-effort**: Falls back to HTTP submit if MCP fails
- **No LLM dependency**: All solvers use deterministic logic (except Echo which reverse-engineers from observed data)
- **Compact logging**: Raw response previews logged to diagnose undocumented API shapes
- **Graceful degradation**: Each solver tries multiple strategies before giving up
