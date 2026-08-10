# Kanto Agent

**CTF Category:** [Fill in]
**Challenges:** [Fill in]
**Points:** [Fill in]
**Latest Version:** [Fill in]

## Overview

[Brief description of what this agent solves]

## Build

```bash
cd agents/kanto/src/
docker build -t kanto-agent:latest .
docker save kanto-agent:latest > ../builds/kanto-agent-vN.tar
```

## Usage

```bash
# Load pre-built image
docker load < agents/kanto/builds/kanto-agent-vN.tar

# Run (platform provides environment variables)
docker run --rm -it kanto-agent:vN
```

## Architecture

[Brief description of solver architecture]

## Versions

See [VERSIONS.md](./builds/VERSIONS.md) for changelog.

## See Also

- [Write-up](../../docs/writeups/[challenge-name].md)
- [Logs](../../logs/kanto/)
