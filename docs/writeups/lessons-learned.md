# Lessons Learned - HalCTF 2026

A comprehensive analysis of what we learned building autonomous AI agents for CTF challenges across three major challenge categories: Hac-Man, Kanto Region, and Turing's Labyrinth.

## Executive Summary

**Challenges Solved:** 14/14 fully documented  
**Total Points:** 2,675+  
**Agent Versions:** 30+ iterations across all categories  
**Time Investment:** ~12 hours total  
**Success Rate:** 93% (14 solved, 1 locked)

---

## Meta-Learnings: Building Autonomous CTF Agents

### 1. Architecture Patterns

#### Multi-Solver Architecture Wins

**Pattern:** Single agent with pluggable solvers per challenge type

```
agent/
├── agent.py              # Main entry, routing
├── solvers/
│   ├── race_condition.py
│   ├── sat_solver.py
│   ├── ecdsa_nonce.py
│   ├── ssrf.py
│   └── timing_attack.py
└── utils/
    ├── mcp_client.py
    └── submit.py
```

**Why it works:**
- Per-solver isolation makes debugging easy
- Can test solvers independently
- Graceful degradation if one fails
- Shared utilities reduce code duplication

**Anti-pattern:** Monolithic agent trying to handle everything in one file

#### Bundle-Offline for Unreachable Files

**Problem:** Some challenges require files that MCP can't fetch (binary exploits, obfuscated scripts)

**Solution:**
1. Human downloads files from challenge page
2. Drops into `agent/attachments/`
3. Dockerfile bakes files into image
4. Agent loads from bundle at runtime

**Example:** Achilles' Heel binary exploitation required the exact binary served on the port, but the port was raw TCP (not HTTP). Bundle-offline solved this.

#### LLM Copilot as Fallback, Not Primary

**Pattern:** Deterministic solvers first, LLM fallback for unknown/failed cases

**Why:**
- Deterministic code is faster (ms vs seconds)
- No token cost for known patterns
- Predictable behavior for debugging
- LLM handles edge cases gracefully

**Bounds for LLM fallback:**
- Max steps: 14
- Wall clock timeout: 5 minutes
- Submission quota: 2 per run
- Tool vocabulary: Limited to essential operations

**Anti-pattern:** LLM-first approach wastes tokens and time on solvable problems

#### Case Study: Odyssey v10 Hybrid Architecture

**Problem:** Field names and API structures kept changing between challenges, requiring v4/v5/v6 rebuilds for single-field fixes.

**Solution:** Hybrid deterministic + LLM fallback architecture

```python
# Fast path: Deterministic field extraction
for field in ("crew", "ashore", "men", "register"):
    if field in response:
        names = response[field]
        break

# Adaptive path: LLM fallback when deterministic fails
if not names:
    names = llm_extract_json(
        "Extract crew names from this shore register",
        response.text,
        ["name1", "name2"]
    )
```

**Results:**
- [SOLVED] No rebuild needed for API variations
- [SOLVED] 2-5 second overhead only when deterministic fails
- [SOLVED] Scylla/Aeolus/Lotus all got LLM fallbacks in v10
- [SOLVED] Bow of Odysseus uses LLM to parse protocol spec AND generate implementation

**When to use:**
- Field names unknown at build time
- Protocol specs only available at runtime
- API structure varies between challenges
- Code generation needed (e.g., binary protocol clients)

**When NOT to use:**
- Known, stable APIs (waste of tokens)
- Time-critical operations (deterministic is faster)
- Simple transformations (overkill)

---

### 2. Development Workflow

#### Iterate on Real Challenges, Not Mocks

**Learning:** Building against live CTF challenges accelerated development far more than building against synthetic test cases.

**Process:**
1. Attempt challenge with agent v1
2. Read logs to understand failure
3. Fix specific issue
4. Rebuild and retry
5. Repeat until solved

**Typical iteration cycle:** 15-30 minutes per version

#### Version Control for Docker Images

**Pattern:** Tag every working version

```bash
docker build -t kanto-agent:v13 .
docker save kanto-agent:v13 > kanto-agent-v13.tar
```

**Why:**
- Can roll back to last working version
- Easy to diff what changed between versions
- Upload history for auditing
- Disk is cheap; debugging time is expensive

#### Log Everything, Trust Nothing

**Pattern:** Structured logging with request/response capture

```python
logging.info(f"[SOLVER] Attempting {challenge_name}")
logging.debug(f"[API] Request: {method} {endpoint}")
logging.debug(f"[API] Body: {json.dumps(body)}")
logging.debug(f"[API] Response: {response.text}")
logging.info(f"[RESULT] Flag: {flag}")
```

**Why:**
- Remote debugging is impossible without logs
- Response bodies often contain hints
- Error messages reveal API expectations
- Timing information aids optimization

---

### 3. Challenge-Specific Learnings

#### Race Conditions (Bill's PC)

**Key Insight:** "Concurrency" means REAL parallelism, not sequential requests

```python
# WRONG - Sequential (no race)
for _ in range(20):
    requests.post("/api/withdraw")

# CORRECT - Concurrent (exploits TOCTOU)
with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
    futures = [executor.submit(requests.post, "/api/withdraw") for _ in range(20)]
```

**Lesson:** Async/threading isn't optional for race conditions; it's the exploit

#### 3-SAT Solving (Cerulean Cave)

**Key Insight:** Use battle-tested solvers, don't reinvent the wheel

**Anti-pattern:** Implementing DPLL algorithm from scratch  
**Correct approach:** Use pycosat (optimized C library)

**Gotchas:**
- 0-indexed vs 1-indexed clauses (auto-detect)
- Response format must be wrapped: `{"assignment": [...]}`
- Off-by-one in output array

**Lesson:** For NP-complete problems, leverage existing optimized implementations

#### ECDSA Nonce Reuse (Indigo League)

**Key Insight:** String matching is dangerous

```python
# WRONG - "p256" matches "secp256k1"!
if "p256" in curve_name:
    return NIST256p  # Incorrect for secp256k1

# CORRECT - Check longest match first
if "256k1" in curve_name:
    return SECP256k1
elif "256r1" in curve_name or "p256" in curve_name:
    return NIST256p
```

**Lesson:** Substring matching needs careful ordering; prefer exact matches

#### Nested SSRF (Silph Co.)

**Key Insight:** API endpoint names aren't consistent across hosts

- Lobby: `/api/staff/{id}` (IDs from 101+)
- Mainframe: `/api/records/{id}` (IDs from 1+)

**Don't assume** similar hosts use identical schemas!

**Lesson:** Verify API structure per host, don't generalize from one example

#### Timing Attacks (Pythia's Whisper)

**Key Insight:** Network timing attacks work, but require statistics

**Single measurement:** Unreliable (network jitter)  
**Median of 10 samples:** Robust to outliers

```python
samples = []
for _ in range(10):
    start = time.time()
    response = requests.post("/verify", json={"token": guess})
    samples.append(time.time() - start)

timing = statistics.median(samples)  # Not mean!
```

**Lesson:** Median filters noise better than mean for timing side-channels

#### LLM Word Generation (Hac-Man)

**Key Insight:** LLM creativity beats exhaustive enumeration for word puzzles

**Scripted list:** 100 attempts, all failed  
**LLM-generated:** 30 attempts, success on #10

**Why:** LLM found compound camelCase variation (`WakaWaka`) that scripted list missed

**Lesson:** For creative/linguistic challenges, LLM generation is cost-effective

---

## Technical Anti-Patterns We Discovered

### 1. Assuming API Consistency

**Bad assumption:** All endpoints use the same authentication method  
**Reality:** Silph Co. had different auth per host (internal key vs vault token)

**Bad assumption:** Field names are standard across endpoints  
**Reality:** Indigo League used `"message"` for badges but `"trial_message"` for champion

**Lesson:** Read every response, extract robustly, never hardcode field names

### 2. Early Optimization

**Mistake:** Multi-stage Docker build for size optimization in v1  
**Reality:** Didn't need it until image exceeded limits (never happened)

**Cost:** Debugging was harder (build cache invalidation)

**Lesson:** Build straightforward images first; optimize only when necessary

### 3. Over-Engineering for Future Challenges

**Mistake:** Building generic "crypto solver" framework anticipating many crypto challenges  
**Reality:** Each crypto challenge was unique (timing attack, obfuscated python, transform cascade)

**Cost:** Framework code was never reused

**Lesson:** YAGNI (You Aren't Gonna Need It) - solve the challenge at hand

### 4. Ignoring Hint Metadata

**Mistake:** Guessing flag formats instead of reading hint penalty costs  
**Reality:** Pythia's Whisper hints cost 38 points each; could have solved without hints

**Lesson:** Read all available information before spending resources

### 5. Silent Failure Tolerance

**Mistake:** Catching all exceptions and continuing  
**Reality:** Masked bugs that could have been fixed quickly

```python
# BAD
try:
    result = solve_challenge()
except:
    pass  # Silent failure!

# GOOD
try:
    result = solve_challenge()
except Exception as e:
    logging.error(f"Solver failed: {e}")
    raise  # Or handle specifically
```

**Lesson:** Fail loudly during development; graceful degradation in production

---

## Optimization Learnings

### 1. Docker Image Size Optimization

**Pattern:** Multi-stage build when build dependencies ≠ runtime dependencies

```dockerfile
# Stage 1: Build (needs gcc)
FROM python:3.11-slim as builder
RUN apt-get install gcc
RUN pip wheel pycosat

# Stage 2: Runtime (only binutils)
FROM python:3.11-slim
COPY --from=builder /wheels /wheels
RUN pip install /wheels/*
```

**Result:** 415MB → 172MB for Kanto agent

**When to use:** When build-time tools (gcc, make, g++) aren't needed at runtime

### 2. Streaming Large Files

**Problem:** 100MB log file in memory  
**Solution:** Stream and process line-by-line

```python
# BAD
log_text = requests.get("/access.log").text  # 100MB in memory!
for line in log_text.split('\n'):
    process(line)

# GOOD
response = requests.get("/access.log", stream=True)
for line in response.iter_lines(decode_unicode=True):
    process(line)
```

**Lesson:** Always stream large responses

### 3. Model Selection Strategy

**Hierarchy:**
1. Deterministic code (free, instant)
2. Small model (gemma, cheap, fast)
3. Medium model (qwen, balanced)
4. Large model (llama-3.1-70b, expensive, slow)

**Never default to large model** - use only when complexity demands it

**Lesson:** Right-size model to task complexity

---

## Security Learnings

### 1. Input Validation at Boundaries

**Pattern:** Validate all external inputs (API responses, environment variables)

```python
def parse_challenge_id(env_value):
    """
    HAL_CHALLENGE_ID must be integer, not string
    """
    if not env_value:
        return None
    
    try:
        return int(env_value)
    except ValueError:
        logging.error(f"Invalid challenge ID: {env_value}")
        return None
```

**Lesson:** Never trust external data, even from "trusted" sources

### 2. Quota-Safe LLM Interactions

**Problem:** LLM copilot could hallucinate 100 flags and waste submission quota

**Solution:** Gate submissions through validation

```python
def propose_flag(candidate):
    # Validate format
    if not re.match(r'HALCTF\{[^}]+\}', candidate):
        return False
    
    # Deduplicate
    if candidate in submitted_flags:
        return False
    
    # Enforce limit
    if len(submitted_flags) >= MAX_SUBMITS:
        return False
    
    # Actually submit
    return submit_flag(candidate)
```

**Lesson:** Never give LLMs direct access to rate-limited resources

### 3. Command Injection Prevention

**Pattern:** Use list arguments, not shell strings

```python
# VULNERABLE
subprocess.run(f"ping {user_input}", shell=True)

# SAFE
subprocess.run(["ping", user_input])
```

**Lesson:** Even in CTF agents, practice secure coding (teaches good habits)

---

## Debugging Strategies That Worked

### 1. Differential Analysis

**Pattern:** Compare working vs failing runs

```bash
# Extract API calls from successful run
grep "\[API\]" run_success.log > success_api.txt

# Extract API calls from failed run
grep "\[API\]" run_fail.log > fail_api.txt

# Diff them
diff success_api.txt fail_api.txt
```

**Frequently revealed:** Missing headers, wrong endpoints, malformed bodies

### 2. Skeleton Request Capture

**Pattern:** Start with minimal request, add complexity incrementally

```python
# Step 1: Can we reach the endpoint?
response = requests.get(f"{target}/api/records/1")
print(response.status_code)

# Step 2: What headers are required?
response = requests.get(f"{target}/api/records/1", 
                       headers={"X-Silph-Key": "..."})
print(response.status_code)

# Step 3: What about body format?
# ... continue
```

**Lesson:** Binary search for the minimal working request

### 3. Known-Good Reference

**Pattern:** Capture working manual solution, then automate

```bash
# Manual exploration
curl -X POST http://target/api/withdraw
curl -X POST http://target/api/withdraw
curl http://target/api/storage
# -> Got flag!

# Now automate exact same sequence
requests.post(f"{target}/api/withdraw")
requests.post(f"{target}/api/withdraw")
requests.get(f"{target}/api/storage")
```

**Lesson:** Prove exploit works manually before automating

---

## Collaboration Patterns (Human + AI)

### Division of Labor

**Human responsibilities:**
- High-level strategy (which challenges to attempt)
- Downloading unreachable files (bundle-offline pattern)
- Reading challenge hints and translating to solver specs
- Approving risky operations (submission attempts)

**AI agent responsibilities:**
- Executing deterministic solvers
- Making API calls with correct formatting
- Retrying with backoff
- Logging for post-mortem analysis

**Collaborative tasks:**
- Debugging (human reads logs, AI proposes fixes)
- Optimization (human identifies bottleneck, AI refactors)
- Testing (AI runs tests, human interprets failures)

### When to Override the AI

**Red flags:**
- Agent repeating the same failed approach
- API calls clearly malformed (from logs)
- Solver logic has obvious bug
- Approaching quota limits without progress

**Action:** Stop agent, fix code, rebuild, retry

**Lesson:** Autonomous doesn't mean unsupervised; monitor and intervene

---

## Competition Strategy Insights

### 1. Quick Wins First

**Strategy:** Scan environment variables, test simple exploits, grab easy points

**Why:** Early points build confidence and leaderboard position

**Quick wins in our run:**
- BONUS_FLAG (instant)
- Icarus Uplink (20 pts, 5 minutes)
- The Haystack (30 pts, 10 minutes)
- Hac-Man (50 pts, 15 minutes)

### 2. Parallel Challenge Development

**Strategy:** Work on multiple agents simultaneously (separate directories)

**How:**
```bash
# Terminal 1
cd hacman-agent/
# Iterate on Hac-Man

# Terminal 2
cd kanto-agent/
# Iterate on Kanto challenges

# Terminal 3
cd labyrinth-agent/
# Iterate on Labyrinth
```

**Benefit:** Blocked on one challenge? Switch to another.

### 3. Don't Get Stuck

**Pattern:** 3-attempt rule

1. First attempt fails → Read logs, fix obvious issue
2. Second attempt fails → Try alternative approach
3. Third attempt fails → **Move to different challenge**

**Reasoning:** Diminishing returns; other challenges might be easier

**We skipped:** The Exchange (modem protocol) - would have taken hours

### 4. Version Tag Everything

**Pattern:** Every successful solve gets a version tag

```bash
docker build -t hacman-agent:v7 .  # Working version
docker save hacman-agent:v7 > hacman-agent-v7.tar
```

**Why:**
- Can submit last working version if new attempt breaks
- Easy to see progression (v1 → v7)
- Upload history for post-CTF analysis

---

## Cost Analysis

### Token Usage Estimates

**Hac-Man (LLM-heavy):**
- Phase 1: Scripted (0 tokens)
- Phase 2: LLM generation (~2,000 tokens)
- Phase 3: Conversational (reserved, not used)

**Kanto (mostly deterministic):**
- Bill's PC: 0 tokens (pure race condition)
- Cerulean Cave: 0 tokens (pycosat)
- Indigo League: 0 tokens (ECDSA math)
- Silph Co.: 0 tokens (SSRF chain)

**Labyrinth (mixed):**
- 6 network challenges: 0 tokens (deterministic)
- 2 file-based challenges: ~1,000 tokens (analysis)
- LLM copilot fallback: ~5,000 tokens (bounded runs)

**Total estimated:** ~8,000 tokens across all challenges

**Cost (at $0.50/1M tokens):** < $0.01

**Lesson:** Deterministic solvers massively reduce token costs

### Development Time

| Challenge Category | Time Invested | Iterations |
|-------------------|---------------|------------|
| Hac-Man | 2 hours | 7 versions |
| Kanto Region | 4 hours | 13 versions |
| Turing's Labyrinth | 5 hours | 10 versions |
| Write-ups | 3 hours | - |
| **Total** | **14 hours** | **30 versions** |

**Time per challenge:** ~1 hour average (range: 15 min to 3 hours)

---

## Tools That Paid Off

### Essential

1. **Docker** - Consistent environments, easy upload
2. **Python** - Rapid prototyping, rich library ecosystem
3. **requests** - HTTP client (used in every challenge)
4. **MCP SDK** - Challenge discovery and submission

### Specialized

5. **pycosat** - 3-SAT solving (Cerulean Cave)
6. **pwntools** - Binary exploitation (Achilles' Heel)
7. **ecdsa library** - ECDSA math (Indigo League)
8. **statistics.median** - Timing attack noise reduction (Pythia)

### Nice-to-Have

9. **pyelftools** - ELF binary parsing
10. **OpenAI SDK** - LLM integration (for copilot and word generation)

### Didn't Need

- Burp Suite (all challenges scriptable)
- Ghidra (binary was bundled, no complex RE)
- sqlmap (no SQL injection challenges)

**Lesson:** Pack light; install specialized tools as needed

---

## If We Did This Again

### Do More Of

1. **Earlier parallelization** - Could have tackled challenges simultaneously from day 1
2. **Upfront research** - Reading all challenge hints before starting would have saved time
3. **Test-driven development** - Writing tests for solvers before implementing
4. **Documented solver specs** - Formal API contract per challenge

### Do Less Of

1. **Premature optimization** - Multi-stage builds weren't needed initially
2. **Generic frameworks** - Most "reusable" code was never reused
3. **Guess-and-check** - More upfront analysis, fewer blind attempts
4. **Monolithic commits** - Smaller, more atomic changes would aid debugging

### New Approaches

1. **Unified agent harness** - Single codebase with pluggable solvers (instead of separate agents per category)
2. **Solver registry** - Dynamic routing based on challenge metadata
3. **Offline test suite** - Mock challenges for regression testing
4. **Cost tracking** - Log token usage per challenge for optimization

---

## Advice for Future Competitors

### Before the Competition

1. **Read the rules thoroughly** - USER_ID print, heartbeat, submission format
2. **Test against dry-run environment** - Validate agent can boot and submit
3. **Build modular from day 1** - Per-solver isolation pays dividends
4. **Set up logging infrastructure** - You'll need it for debugging

### During the Competition

1. **Start with easy challenges** - Build momentum and confidence
2. **Don't chase locked challenges** - Some aren't worth the time investment
3. **Version control religiously** - Tag every working version
4. **Read logs between attempts** - Don't spam retries blindly

### Technical Priorities

1. **Deterministic solvers > LLM** - Code is faster and cheaper
2. **Robust error handling** - Remote debugging is hard; fail gracefully
3. **Structured logging** - Request/response capture aids debugging
4. **Quota management** - Never let LLM waste submission attempts

### Mental Model

**Autonomous agent ≠ Unsupervised agent**

- Monitor progress via logs
- Intervene when stuck
- Human strategy + AI execution = winning combination

---

## Final Thoughts

Building autonomous CTF agents is a **collaboration between human insight and AI execution**. The human provides:
- Strategic direction
- Domain knowledge
- Debugging intuition
- Resource management

The AI provides:
- Tireless execution
- Fast iteration
- Pattern matching
- Graceful degradation

The winning formula: **Right-size the problem, right-size the solution, iterate rapidly.**

**Most important lesson:** Don't overthink it. Start simple, iterate on real challenges, and let the failures guide your improvements.

---

## Appendix: Quick Reference

### Agent Architecture Checklist

- [ ] Multi-solver architecture (pluggable per challenge type)
- [ ] MCP integration (challenge discovery + submission)
- [ ] Environment variable scanning (quick wins)
- [ ] Structured logging (debugging)
- [ ] Graceful error handling (retries with backoff)
- [ ] Version tagging (rollback capability)
- [ ] Docker optimization (multi-stage if needed)
- [ ] LLM copilot (bounded, fallback only)

### Solver Development Checklist

- [ ] Read challenge description thoroughly
- [ ] Check for existing libraries/tools
- [ ] Test approach manually first
- [ ] Implement deterministic solver
- [ ] Add robust error handling
- [ ] Log request/response pairs
- [ ] Test against live challenge
- [ ] Iterate based on failures

### Pre-Upload Checklist

- [ ] USER_ID prints within 30 seconds
- [ ] Heartbeat logs every 60 seconds
- [ ] All solvers tested individually
- [ ] Docker image builds successfully
- [ ] Image size < 2.5GB
- [ ] Submission format validated
- [ ] Version tagged and saved

---

**Total challenges documented:** 14  
**Total points earned:** 2,675+  
**Success rate:** 93%  
**Time invested:** 14 hours  
**Lessons learned:** Priceless 
