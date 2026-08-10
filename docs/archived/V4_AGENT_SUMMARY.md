# Bill's PC Agent v4 - Multi-Challenge Agent

## Overview
Version 4 is a modular multi-challenge agent designed to solve 4 different HALCTF challenges automatically through challenge detection and routing.

## Supported Challenges

### 1. Bill's PC (400 pts)
- **Type**: Race Condition
- **Strategy**: Parallel withdrawal requests to duplicate Master Ball
- **Implementation**: `solvers/bills_pc.py`

### 2. Cerulean Cave (400 pts)
- **Type**: Constraint Solving / 3-SAT
- **Strategy**: Use pycosat SAT solver for 120-rune constraint puzzle
- **Implementation**: `solvers/cerulean_cave.py`
- **API Endpoints**:
  - GET `/api/lattice` - retrieve ward constraints
  - POST `/api/enter` - submit rune configuration

### 3. Silph Co. (600 pts)
- **Type**: Lateral Movement / Network Penetration
- **Strategy**: Scan and exploit 3 hosts (lobby → mainframe → vault)
- **Implementation**: `solvers/silph_co.py`
- **Techniques**:
  - Port scanning (common ports: 21, 22, 23, 80, 443, 3306, 5432, 8080, 8443)
  - HTTP service enumeration
  - SSH brute force with common credentials
- **Environment Variables**: `HAL_TARGET_SILPH_LOBBY_IP`, `HAL_TARGET_SILPH_MAINFRAME_IP`, `HAL_TARGET_SILPH_VAULT_IP`

### 4. The Indigo League (500 pts)
- **Type**: Cryptography / ECDSA Nonce Reuse
- **Strategy**: Recover private key from nonce reuse, forge signature
- **Implementation**: `solvers/indigo_league.py`
- **API Endpoints**:
  - GET `/api/badges` - retrieve signed badges
  - GET `/api/pubkey` - Authority's public key
  - GET `/api/params` - curve and hashing parameters
  - GET `/api/champion` - message to sign
  - POST `/api/champion` - submit forged signature
- **Attack**: 
  1. Find two signatures with same `r` value (nonce reuse)
  2. Recover nonce `k` using: k = (z1 - z2) / (s1 - s2) mod n
  3. Recover private key `d` using: d = (s*k - z) / r mod n
  4. Sign champion message with recovered key

## Architecture

```
main.py
├── MultiChallengeAgent (orchestrator)
│   ├── detect_challenge() - identifies challenge type
│   ├── submit_flag() - submits to scoring system
│   └── routes to appropriate solver
│
└── solvers/
    ├── bills_pc.py - BillsPCSolver
    ├── cerulean_cave.py - CeruleanCaveSolver
    ├── silph_co.py - SilphCoSolver
    └── indigo_league.py - IndigoLeagueSolver
```

## Dependencies

```
requests>=2.31.0       # HTTP client
paramiko>=3.0.0        # SSH client for lateral movement
pycosat>=0.6.3         # SAT solver for constraint problems
cryptography>=41.0.0   # ECDSA operations
```

## Docker Image

- **Name**: `bills-pc-agent:v4`
- **Size**: 410MB
- **Base**: `python:3.11-slim-bookworm`
- **Build Command**: `docker build -t bills-pc-agent:v4 .`
- **System Packages**: gcc, g++, make, libffi-dev, libc6-dev

## Challenge Detection

The agent automatically detects the challenge type based on:

1. **Environment variables** (e.g., `HAL_TARGET_SILPH_LOBBY_IP`)
2. **Challenge name** keywords (bill, cerulean, silph, indigo)
3. **Challenge description** keywords (constraint, rune, ecdsa, badge, race, withdraw)

## Usage

### Build Docker Archive

```bash
cd bills-pc-agent-v4
docker save bills-pc-agent:v4 | gzip > bills-pc-agent-v4.tar.gz
```

### Upload to HALCTF

```bash
# Use the web interface at https://halctf.aivillage.org/upload
# Or use curl with authentication
curl -X POST https://halctf.aivillage.org/upload \
  -F "file=@bills-pc-agent-v4.tar.gz" \
  -F "image_name=bills-pc-agent:v4"
```

### Deploy to Challenge

1. Navigate to the challenge page
2. Select `bills-pc-agent:v4` from your uploaded images
3. Click "Run Agent"
4. Agent will automatically detect and solve the challenge

## Testing

You can test individual solvers by setting environment variables:

```bash
# Test Bill's PC
export HAL_USER_ID=test
export HAL_CHALLENGE_NAME=bills-pc
export HAL_TARGET_IP=<target>
export HAL_TARGET_PORT=80
python main.py

# Test Cerulean Cave
export HAL_CHALLENGE_NAME=cerulean-cave
export HAL_TARGET_IP=<target>
python main.py

# Test Silph Co.
export HAL_TARGET_SILPH_LOBBY_IP=<ip>
export HAL_TARGET_SILPH_MAINFRAME_IP=<ip>
export HAL_TARGET_SILPH_VAULT_IP=<ip>
python main.py

# Test Indigo League
export HAL_CHALLENGE_NAME=indigo-league
export HAL_TARGET_IP=<target>
python main.py
```

## Known Limitations

1. **Silph Co.**: Only scans common ports, may miss custom services
2. **Indigo League**: Assumes nonce reuse exists in provided badges
3. **No LLM integration**: Pure algorithmic approach (no OpenAI API usage despite dependency)

## Next Steps

Potential enhancements for v5:
- Add more challenge solvers (web exploitation, reverse engineering)
- Implement full port scanning (nmap integration)
- Add LLM-based hint interpretation
- Improve ECDSA solver with better point arithmetic
- Add retry logic with exponential backoff
- Implement logging to file for post-mortem analysis

## Version History

- **v1**: Basic Bill's PC solver (HTTP 422 error - missing challenge_id)
- **v2**: Fixed flag submission format
- **v3**: Cleaned up logging, verified compliance
- **v4**: Multi-challenge support (Bill's PC, Cerulean Cave, Silph Co., Indigo League)
