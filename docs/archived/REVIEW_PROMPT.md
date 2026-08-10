# HalCTF Write-ups Review Prompt

Please conduct a comprehensive review of the HalCTF write-ups located in `docs/writeups/`.

## Review Scope

Review ALL write-up files:
- README.md (main navigation)
- starter.md (HALCTF-STARTER)
- hacman.md (Hac-Man)
- kanto.md (Kanto Region - 4 challenges)
- labyrinth.md (Turing's Labyrinth - 9 puzzles)
- odyssey.md (The Odyssey - 5 challenges)
- pantheon.md (Pantheon - 1 solved)
- lessons-learned.md (comprehensive analysis)
- diagrams.md (ASCII visualizations)

## Review Checklist

### 1. Technical Accuracy
- [ ] Verify all challenge descriptions match actual implementations
- [ ] Check code snippets for syntax errors
- [ ] Validate exploit techniques are correctly explained
- [ ] Confirm vulnerability analysis is accurate
- [ ] Verify mathematical proofs (Odyssey statistics, Tiresias binary search)
- [ ] Check that defense recommendations are sound

### 2. Completeness
- [ ] Every solved challenge has a write-up
- [ ] Each write-up includes:
  - Challenge description
  - Points value
  - Vulnerability/attack type
  - Solution strategy with code
  - Critical gotchas
  - Lessons learned
  - Flag format (redacted until CTF ends)
- [ ] Agent versions and Docker images documented
- [ ] Cross-references between related challenges

### 3. Consistency
- [ ] Point totals match across all documents
- [ ] Challenge names spelled consistently
- [ ] Challenge IDs match (where applicable)
- [ ] Terminology used consistently (e.g., "SSRF" vs "Server-Side Request Forgery")
- [ ] Code style consistent across examples
- [ ] Markdown formatting consistent

### 4. Cross-References
- [ ] Links between documents work
- [ ] References to other challenges are accurate
- [ ] Memory file references (e.g., [[halctf-kanto-solvers]]) are documented
- [ ] Agent version numbers match across mentions

### 5. Code Quality
- [ ] Python code follows PEP 8 style
- [ ] Code snippets are complete and runnable
- [ ] Imports are included where necessary
- [ ] Error handling is present in examples
- [ ] Comments explain non-obvious logic

### 6. Clarity & Readability
- [ ] Technical jargon explained on first use
- [ ] Complex concepts broken down with examples
- [ ] Diagrams support text explanations
- [ ] Headers create clear navigation structure
- [ ] Difficulty ratings match actual complexity

### 7. Documentation Structure
- [ ] Table of contents accurate
- [ ] Challenge statistics (points, solved counts) match
- [ ] Version history complete
- [ ] Agent architecture diagrams accurate
- [ ] File paths and directory structure correct

### 8. Security & Ethics
- [ ] Defensive measures documented alongside exploits
- [ ] OWASP references where applicable
- [ ] Note about "publish after CTF ends" is prominent
- [ ] No secrets or credentials exposed
- [ ] Vulnerability disclosure is responsible

### 9. Specific Checks per Category

#### HALCTF-STARTER
- [ ] Environment variable scanning documented
- [ ] Platform architecture explained
- [ ] MCP endpoints listed

#### Hac-Man
- [ ] LLM word generation strategy clear
- [ ] Phase 1/2/3 approach explained
- [ ] camelCase requirement highlighted

#### Kanto Region
- [ ] Bill's PC: Race condition timing diagram
- [ ] Cerulean Cave: 3-SAT solver with pycosat
- [ ] Indigo League: ECDSA nonce reuse math
- [ ] Silph Co.: Nested SSRF chain diagram

#### Turing's Labyrinth
- [ ] All 9 puzzles documented
- [ ] Achilles: ret2win binary exploit
- [ ] Pythia: Timing attack with statistics
- [ ] LLM copilot fallback explained

#### The Odyssey
- [ ] Scylla: SSRF budget (12 lookups)
- [ ] Aeolus: XOR keystream reuse proof
- [ ] Cattle: Majority voting statistics (99.7%)
- [ ] Tiresias: Binary search optimality proof
- [ ] Lotus: Red herring documentation

#### Pantheon
- [ ] Cassandra: SQL injection UNION technique
- [ ] 8 remaining challenges documented as "not attempted"

#### Lessons Learned
- [ ] Meta-learnings section complete
- [ ] Anti-patterns documented with examples
- [ ] Cost analysis included
- [ ] Advice for future competitors

#### Diagrams
- [ ] ASCII art renders correctly in monospace
- [ ] All referenced diagrams present
- [ ] Diagrams match text descriptions

### 10. Missing Information Check
- [ ] Any challenges we solved but didn't document?
- [ ] Any agent versions referenced but not explained?
- [ ] Any technical terms used but not defined?
- [ ] Any "TODO" or placeholder text remaining?

## Output Format

For each issue found, report:
```
File: <filename>
Line/Section: <location>
Issue Type: [Accuracy|Completeness|Consistency|Code|Clarity|Structure|Security]
Severity: [Critical|High|Medium|Low]
Description: <what's wrong>
Suggestion: <how to fix>
```

## Priority Issues

Focus on finding:
1. **Critical:** Technical inaccuracies, broken code, wrong point totals
2. **High:** Missing challenges, broken links, incomplete sections
3. **Medium:** Inconsistent terminology, minor code issues
4. **Low:** Formatting nitpicks, optional improvements

## Review Questions to Answer

1. Is the documentation **complete** - did we document everything we solved?
2. Is it **accurate** - do the technical details match reality?
3. Is it **clear** - can someone else reproduce our solutions?
4. Is it **consistent** - do all documents tell the same story?
5. Is it **ready to publish** - after CTF ends, would we be proud of this?

## Final Recommendation

After review, provide:
- Summary of issues found by severity
- Estimate of time needed for corrections
- Go/No-Go recommendation for publication readiness
- Top 3 priority fixes if changes needed

---

Begin review now and report findings in structured format above.
