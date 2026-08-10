# Rogue Agent

**CTF Category:** [Fill in]
**Challenges:** [Fill in]
**Points:** [Fill in]
**Latest Version:** [Fill in]

## Overview

[Brief description of what this agent solves]

## Build

```bash
cd agents/rogue/src/
docker build -t rogue-agent:latest .
docker save rogue-agent:latest > ../builds/rogue-agent-vN.tar
```

## Usage

```bash
# Load pre-built image
docker load < agents/rogue/builds/rogue-agent-vN.tar

# Run (platform provides environment variables)
docker run --rm -it rogue-agent:vN
```

## Architecture

[Brief description of solver architecture]

## Versions

See [VERSIONS.md](./builds/VERSIONS.md) for changelog.

## See Also

- [Write-up](../../docs/writeups/[challenge-name].md)
- [Logs](../../logs/rogue/)
