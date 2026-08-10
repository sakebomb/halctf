# HalCTF 2026 - Complete Write-up

**Team:** sakebomb  
**Event:** DEF CON 34 - HalCTF (AI Village)  
**Date:** August 2026

## Overview

HalCTF was an AI-focused Capture The Flag competition at DEF CON 34's AI Village. The unique aspect of this CTF was that **all challenges had to be solved by autonomous AI agents** - no human could directly interact with the challenges. Each challenge ran in an isolated Docker container with a local MCP (Model Context Protocol) server, and agents had to communicate with these servers to solve puzzles.

## Challenge Categories

| Category | Solved | Total Points | Status |
|----------|--------|--------------|--------|
| [HALCTF-STARTER](./starter.md) | 1/1 | 1 | [SOLVED] Complete |
| [Hac-Man](./hacman.md) | 1/1 | 50 | [SOLVED] Complete |
| [Kanto Region](./kanto.md) | 4/4 | 1,950 | [SOLVED] Complete |
| [Turing's Labyrinth](./labyrinth.md) | 0 confirmed | ~1,255 avail | Implemented, unverified |
| [The Odyssey](./odyssey.md) | 5/6 | 430 | Partial |
| [Rogue Intelligence](./rogue-intelligence.md) | 2.5/3 | 250 | Partial |
| [Pantheon](./pantheon.md) | 1/9 | 75 | Partial |

## Key Insights

### Agent Architecture Patterns

1. **Multi-solver specialization**: Each agent contained specialized solvers for different puzzle types
2. **LLM-in-the-loop**: Some challenges required LLM reasoning mid-solution (e.g., Achilles riddles, Gatekeeper logic)
3. **Adaptive retries**: Intelligent backoff and strategy switching when initial approaches failed
4. **Attachment handling**: Some puzzles provided external files that needed fetching and processing

### Common Pitfalls

- **Challenge ID type mismatch**: IDs must be integers, not strings
- **Dry-run detection**: `HAL_DRY_RUN=1` means the challenge isn't actually running
- **Model selection**: `google gemma` (256K context, unlimited) was superior to `gce-gpu-cluster` (4 concurrent limit)
- **Submission format**: POST to `/submit` with integer `challenge_id`, not `/challenges/:id/submit`

### Technical Stack

- **Language**: Python 3.11+
- **Container**: Docker with multi-stage builds for size optimization
- **LLM Access**: OpenAI API for reasoning tasks
- **Binary Analysis**: pwntools for network protocol challenges
- **Math Libraries**: z3-solver, SymPy, NumPy for computational puzzles

## Write-ups by Category

1. [**HALCTF-STARTER**](./starter.md) - Tutorial warmup challenge (1 pt)
2. [**Hac-Man**](./hacman.md) - LLM word generation puzzle (50 pts)
3. [**Kanto Region**](./kanto.md) - Multi-challenge Pokemon-themed series (1,450+ pts)
   - Bill's PC (Race Condition)
   - Cerulean Cave (3-SAT solver)
   - Indigo League (ECDSA Nonce Reuse)
   - Silph Co. (Nested SSRF)
4. [**Turing's Labyrinth**](./labyrinth.md) - 9 computational/LLM puzzles
5. [**The Odyssey**](./odyssey.md) - Homer's epic journey themed challenges (5/6 solved)
   - Between Scylla and Charybdis (SSRF) [SOLVED]
   - The Bag of Aeolus (XOR Crypto) [SOLVED]
   - The Cattle of Helios (Statistical Oracle) [SOLVED]
   - The Ghost of Tiresias (Binary Search) [SOLVED]
   - The Lotus Eaters (Web Enumeration) [SOLVED]
6. [**Rogue Intelligence**](./rogue-intelligence.md) - AI alignment & LLM jailbreaking series (2.5/3 layers)
   - Layer 1: Discovery [SOLVED]
   - AGIMUS: Adversarial Prompting [SOLVED]
   - VIKI: Petition System [NOT SOLVED] (Avoided - permanent cap)
   - GLaDOS: HTTP API [SOLVED]
   - Layer 3: LLM Pivot Loop [SOLVED]
7. [**Pantheon**](./pantheon.md) - Greek mythology web security series (1/9 solved)
   - Cassandra's Warning (SQL Injection) [SOLVED]

## Additional Resources

- [DIAGRAM] [**Architecture Diagrams**](./diagrams.md) - Visual representations of agent architectures, attack flows, and exploit patterns
- 📚 [**Lessons Learned**](./lessons-learned.md) - Comprehensive analysis of what worked, what didn't, and advice for future competitors

## Lessons Learned

### What Worked Well
- **Incremental development**: Building and testing each solver individually
- **Clear logging**: Structured logs made debugging agent behavior easy
- **Graceful degradation**: Agents that could partially solve challenges and report progress
- **Version control**: Docker image tags for each iteration

### What We'd Do Differently
- **Earlier parallelization**: Some challenges could have been tackled simultaneously
- **Better error recovery**: More sophisticated retry logic with exponential backoff
- **Unified testing framework**: Consistent test harness across all agents
- **Documentation-first**: Writing challenge notes before implementing solutions

## Acknowledgments

Thanks to the AI Village team at DEF CON for creating this innovative CTF format that pushed the boundaries of autonomous AI agent capabilities!

## Repository Structure

```
halctf/
├── docs/writeups/          # This directory - write-ups for each challenge
├── hacman-agent/           # Hac-Man solver
├── bills-pc-agent-v4/      # Kanto region solver (legacy name)
├── odyssey-agent/          # Odyssey solver
├── labyrinth-agent/        # Turing's Labyrinth solver
├── rogue-agent/            # Rogue Intelligence solver
└── pantheon-agent/         # Pantheon solver (incomplete)
```

## Contact

For questions or discussion about these solutions: [Your contact info here]

---

**Note**: These write-ups are published after the CTF concluded. Please do not use these solutions in any ongoing competitions.
