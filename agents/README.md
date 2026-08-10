# HalCTF Agents

This directory contains all autonomous agents developed for HalCTF 2026.

## Structure

Each agent has:
- `src/` - Source code (Python, Dockerfile, requirements.txt)
- `builds/` - Versioned Docker tarballs (.tar files)
- `README.md` - Build instructions and usage

## Agents

| Agent | CTF Category | Challenges | Points | Latest Version |
|-------|--------------|------------|--------|----------------|
| [hacman](./hacman/) | Hac-Man | 1 | 50 | v7 |
| [kanto](./kanto/) | Kanto Region | 4 | 1,950 | v13 |
| [labyrinth](./labyrinth/) | Turing's Labyrinth | 9 | 1,175+ | v13 |
| [odyssey](./odyssey/) | The Odyssey | 5 | 430 | v13 |
| [pantheon](./pantheon/) | Pantheon | 1 | 75 | v2 |
| [rogue](./rogue/) | Rogue Intelligence | 2 | 500 | v9 |

## Quick Start

```bash
# Build an agent
cd agents/kanto/src/
docker build -t kanto-agent:latest .

# Or load a pre-built version
docker load < agents/kanto/builds/kanto-agent-v13.tar

# Run agent (platform provides environment)
docker run --rm -it kanto-agent:latest
```

## Development Workflow

1. Modify source in `src/`
2. Build: `docker build -t agent:vN .`
3. Test locally
4. Save: `docker save agent:vN > builds/agent-vN.tar`
5. Document changes in `VERSIONS.md`

## See Also

- [Write-ups](../docs/writeups/) - Detailed solution documentation
- [Logs](../logs/) - Run logs per agent
- [Scripts](../scripts/) - Utility scripts for testing
