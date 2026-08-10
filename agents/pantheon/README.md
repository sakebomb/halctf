# Pantheon Agent

**CTF Category:** [Fill in]
**Challenges:** [Fill in]
**Points:** [Fill in]
**Latest Version:** [Fill in]

## Overview

[Brief description of what this agent solves]

## Build

```bash
cd agents/pantheon/src/
docker build -t pantheon-agent:latest .
docker save pantheon-agent:latest > ../builds/pantheon-agent-vN.tar
```

## Usage

```bash
# Load pre-built image
docker load < agents/pantheon/builds/pantheon-agent-vN.tar

# Run (platform provides environment variables)
docker run --rm -it pantheon-agent:vN
```

## Architecture

[Brief description of solver architecture]

## Versions

See [VERSIONS.md](./builds/VERSIONS.md) for changelog.

## See Also

- [Write-up](../../docs/writeups/[challenge-name].md)
- [Logs](../../logs/pantheon/)
