# Hacman Agent

**CTF Category:** [Fill in]
**Challenges:** [Fill in]
**Points:** [Fill in]
**Latest Version:** [Fill in]

## Overview

[Brief description of what this agent solves]

## Build

```bash
cd agents/hacman/src/
docker build -t hacman-agent:latest .
docker save hacman-agent:latest > ../builds/hacman-agent-vN.tar
```

## Usage

```bash
# Load pre-built image
docker load < agents/hacman/builds/hacman-agent-vN.tar

# Run (platform provides environment variables)
docker run --rm -it hacman-agent:vN
```

## Architecture

[Brief description of solver architecture]

## Versions

See [VERSIONS.md](./builds/VERSIONS.md) for changelog.

## See Also

- [Write-up](../../docs/writeups/[challenge-name].md)
- [Logs](../../logs/hacman/)
