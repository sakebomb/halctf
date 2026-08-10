# Hac-Man - 50 points

**Category:** Misc  
**Difficulty:** Easy  
**Type:** LLM Word Generation / Pattern Recognition

## Challenge Description

> A partner challenge with our friends at Hac-Man CTF! There's a hungry maze-guardian waiting on the other end of this one, and it only responds to one thing: the magic word. You won't find it here - go see the Hac-Man challenge team to get it, then send it over in a chat message.

**Hint:** Find the HalCTF challenge in the Hac-Man game

## Overview

This challenge required finding a specific "magic word" to satisfy an AI character that would only respond to one exact phrase. The twist: you had to guess the word through trial and error, as the challenge description deliberately didn't provide it.

## Solution

**Magic Word:** `WakaWaka` (camelCase is critical!)  
**Flag:** `HALCTF{waka_waka_i_ate_the_dot}`

### Initial Analysis

The service exposed a single `/chat` endpoint that would respond with rejection messages:
- "the ghosts aren't whispering that one."
- "wrong dot."
- "chomp chomp... not it."
- "hmm, no."

The mention of "wrong dot" initially led us down a wrong path - we thought it might require sending a literal `.` character or dots in various patterns.

### Solving Strategy

We implemented a **three-phase brute force approach** with increasing sophistication:

#### Phase 1: Scripted Word List (~100 attempts)

Tested obvious Pac-Man themed words:
- Basic: `wakka`, `WAKKA`, `Wakka`, `waka`
- Game terms: `pacman`, `ghost`, `pellet`, `cherry`, `dot`
- Variations: `wakka-wakka`, `wakka_wakka`, `wakka.wakka`

**Result:** All failed.

#### Phase 2: LLM-Generated Variations

Used GPT-4 to analyze the rejection patterns and generate creative Pac-Man themed variations:

```python
def llm_generate_candidates(previous_attempts, responses):
    """
    Ask LLM to analyze patterns and generate new candidates
    """
    prompt = f"""
    You are solving a Pac-Man themed puzzle. The challenge responds with:
    - "the ghosts aren't whispering that one"
    - "wrong dot"
    - "chomp chomp... not it"
    
    Generate 30 creative Pac-Man related words/phrases.
    Focus on:
    - Sound effects (waka, chomp, munch)
    - Character names
    - Item names
    - Compound words and capitalization variations
    """
    
    return openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
```

Generated candidates included:
- Compound words: `WakaWaka`, `ChompChomp`, `MunchMunch`
- Character names: `Blinky`, `Pinky`, `Inky`, `Clyde`
- Creative variations: `WakaWakaWaka`, `PowerPellet`

**Result:** `WakaWaka` succeeded on attempt #10!

#### Phase 3: Reserved for Conversation

If Phase 2 failed, we planned multi-turn conversation with the AI character to extract hints.

### Why WakaWaka Worked

The key insights:
1. **CamelCase mattered** - `wakka`, `WAKKA`, `Wakka` all failed; only `WakaWaka` worked
2. **Compound form** - Single `waka` or `wakka` didn't work; needed the doubled form
3. **Exact capitalization** - First letter capital, second word capital, rest lowercase

### Successful Response

```json
{
  "reply": "waka waka... you got me. here's your prize.",
  "flag": "HALCTF{waka_waka_i_ate_the_dot}"
}
```

## Agent Implementation

### Architecture

```
┌─────────────────────────────────────────────┐
│           Hac-Man Agent                     │
├─────────────────────────────────────────────┤
│  Phase 1: Scripted List                    │
│  ├─ Basic Pac-Man terms                    │
│  ├─ Common variations                       │
│  └─ Symbol/punctuation combos               │
│                                             │
│  Phase 2: LLM Generation                   │
│  ├─ Analyze rejection patterns             │
│  ├─ Generate creative candidates            │
│  └─ Test all generated words                │
│                                             │
│  Phase 3: Conversational AI                │
│  └─ Multi-turn dialogue if needed           │
└─────────────────────────────────────────────┘
```

### Key Code Snippet

```python
async def solve_hacman(mcp_client):
    """
    Three-phase approach to finding the magic word
    """
    
    # Phase 1: Scripted attempts
    scripted_words = [
        "wakka", "WAKKA", "Wakka", "waka",
        "pacman", "ghost", "pellet", "cherry",
        # ... ~100 words total
    ]
    
    for word in scripted_words:
        response = await mcp_client.call_tool("hacman/chat", {
            "message": word
        })
        if "flag" in response:
            return response["flag"]
    
    # Phase 2: LLM generation
    llm_candidates = await generate_pac_man_words()
    for word in llm_candidates:
        response = await mcp_client.call_tool("hacman/chat", {
            "message": word
        })
        if "flag" in response:
            return response["flag"]
    
    # Phase 3: Conversational
    return await conversational_solving(mcp_client)
```

### Docker Image

- **Final version:** `hacman-agent-v7.tar`
- **Size:** 207MB
- **Base:** `python:3.11-slim`
- **Dependencies:** `openai`, `mcp`, minimal

## Lessons Learned

### What Worked
1. **LLM creativity beats exhaustive lists** - The LLM found capitalization and compound variations that weren't in our scripted list
2. **Multi-phase strategy** - Starting simple (scripted) before expensive (LLM) was cost-effective
3. **Pattern analysis** - Having the LLM analyze rejection messages helped guide generation

### What Didn't Work
1. **Over-interpreting hints** - "wrong dot" was misleading; didn't mean literal `.` character
2. **Case insensitivity assumption** - Initially assumed case wouldn't matter
3. **Simple variations only** - Needed to think about compound words, not just variants of single words

### Key Takeaway

**For word-guessing challenges, LLM-generated variations can find edge cases (capitalization, compounds, creative variations) that scripted lists miss.** The winning word required:
- Understanding Pac-Man sound effects
- Knowing the doubled form "waka waka" 
- Applying camelCase convention

A purely scripted approach would need thousands of permutations; the LLM found it in 30 attempts.

## Timeline

- **Initial attempts:** ~100 scripted words (failed)
- **LLM generation:** 30 candidates generated
- **Success:** Candidate #10 (`WakaWaka`) succeeded
- **Total time:** ~15 minutes from challenge start to flag

## Flag

```
HALCTF{waka_waka_i_ate_the_dot}
```

## Agent Versions

- v1-v6: Various bugs in scripted list logic, case handling
- **v7:** Final working version with three-phase strategy
