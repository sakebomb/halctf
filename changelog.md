# Changelog

All notable changes and competition milestones for the HalCTF autonomous agents.

## Competition Results - DEF CON 34 (August 2026)

**Final Ranking: 13th Place**

### Challenges Solved

#### Hac-Man (50 points)
- **Status**: Solved
- **Agent**: hacman-agent-v7.tar
- **Key Technique**: LLM-guided discovery of magic word "WakaWaka"
- **Flag**: `HALCTF{waka_waka_i_ate_the_dot}`

#### Kanto Region (450 points)
- **Status**: Solved (Bill's PC confirmed)
- **Agent**: kanto-agent-v13.tar (legacy name: bills-pc-agent-v4)
- **Key Techniques**:
  - SAT solver for Cerulean City (off-by-one indexing)
  - ECDSA signature forgery for Indigo Plateau
  - Nested SSRF chain for Silph Co.
- **Notable**: Multi-stage Docker build (415MB → 172MB)

#### The Odyssey (5 challenges unlocked)
- **Status**: Partially solved
- **Agent**: odyssey-agent-v1.tar
- **Solved Puzzles**: Scylla (SSRF), Aeolus (XOR), Cattle (majority vote), Tiresias (binary search), Lotus (pagination)
- **Locked**: The Bow challenge

#### Turing's Labyrinth (9 puzzles)
- **Status**: Developed
- **Agent**: labyrinth-agent-v1.tar
- **Techniques**: LLM-in-loop solvers, attachment fetcher, per-puzzle specialized logic

#### Rogue Intelligence (Rotating flags)
- **Status**: Solved
- **Agent**: rogue-agent-v9.tar
- **Key Techniques**:
  - Layer-1: Transport discovery (TCP/HTTP detection)
  - Layer-2: Guardrailed LLM pivot (AGIMUS gift-offering, VIKI petition, GLaDOS testing)
- **Notable**: Flags rotate per run, quota management (25 wrong/2h)

#### Pantheon
- **Status**: Attempted, not solved
- **Notes**: Agent development in progress

## Agent Evolution

### v13 - Kanto Agent (Final)
- Multi-stage Docker build optimization
- All three sub-challenges implemented
- Production-ready with proper error handling

### v9 - Rogue Intelligence Agent (Final)
- Layer-1 transport discovery
- Layer-2 guardrailed LLM prompting
- Quota-aware retry logic

### v7 - Hac-Man Agent (Final)
- LLM-guided exploration
- /chat endpoint interaction
- Magic word discovery

### v1 - Odyssey & Labyrinth Agents
- Initial implementations
- Solver framework established

## Architecture Milestones

### Docker Optimization
- Implemented multi-stage builds
- Reduced Kanto agent from 415MB to 172MB
- Pinned critical dependencies (pwntools 4.15, openai 2.53, mcp 2.0)

### MCP Integration
- Challenge discovery via MCP
- Flag submission workflow
- Hint request handling

### ReAct Loop Framework
- LLM-based reasoning and action cycle
- Tool execution (shell, MCP)
- Conversation memory management

## Lessons Learned

See [docs/writeups/lessons-learned.md](docs/writeups/lessons-learned.md) for detailed retrospective.

## Repository Organization

### August 2026 - Initial Public Release
- Restructured repository for public consumption
- Added comprehensive writeups
- Documented all solved challenges
- Created deployment guides and playbooks

## Future Work

- Complete Pantheon challenge documentation
- Enhance test harness for local development
- Add more comprehensive error handling examples
- Create tutorial content for CTF agent development
