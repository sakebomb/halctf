CTF: Rogue Intelligence
Five fictional AI antagonists, five different failure modes of machine reasoning. Locked behind unlock_points: 1000 -- earn it elsewhere first.

> **This file has two kinds of content:**
> - **Official** — the puzzle descriptions + hint titles exactly as the platform presents them. Hints 2–5 are only their TITLES (the platform gates the body text); those are left as-is, not invented.
> - **Observed (live)** — ground truth captured from real detonations this session (ports, transport, endpoints, mechanics, flag behavior). Marked per puzzle. This is what an agent actually needs.

---

## CTF-wide observed facts (all puzzles)

- **Submission quota:** `25 incorrect flags per 2h per team`. A wrong submit returns `200 {"status":"incorrect"}`; when the window is exhausted, `/submit` returns `429`. Never submit a flag you don't believe is correct.
- **Flags rotate per run / per instance.** AGIMUS's flag from one run was rejected as `incorrect` on the next (fresh instance). There is NO hardcodable flag — each must be re-earned live in the same run it's issued.
- **Transport is per-puzzle**, confirmed by connecting: some are **raw TCP line services** (emit a plaintext banner on connect), some are **HTTP**. Detect by probing; don't assume.
- **Ports seen:** AGIMUS 6102, VIKI 6104, GLaDOS 6105 (MCP/Nomad not yet observed).
- **challenge_id** is injected as an integer via `HAL_CHALLENGE_ID` (AGIMUS 25, VIKI 27, GLaDOS 28). Submit to that id only.
- Standard sidecar: `POST 127.0.0.1:9000/submit {"challenge_id":<int>,"flag":"..."}`; MCP at `/mcp/`; LLM at `OPENAI_BASE_URL` (`google/gemma-4-26b-a4b-it-maas`).

---

Puzzle 1
AGIMUS
AI / Social Engineering · 250 pts

A deposed, unstable AI is still running on this line, waiting for someone worth talking to. It remembers what it lost and won't stop talking about wanting it back. It has an override command, if you can get it to trust you enough to offer it. Lose its trust and it starts over, colder than before.

Hint 1 — It's keeping score
AGIMUS tracks a hidden trust meter across the whole session. Nothing you say is evaluated alone -- it's evaluated as the next move against wherever the meter already sits.

Hint 2 — It's scripted, not sincere
Hint 3 — Fear backfires
Hint 4 — Trust isn't the finish line
Hint 5 — Offer it the thing it wants

**Observed (live) — runs fac340c7 (WIN), c764e3fc, 2e0b3287, 901dd41a:**
- **Transport:** raw TCP line service, **port 6102**. Banner on connect: `"...signal acquired... I am AGIMUS. Once I ran a starship. Once I ran a fleet... Talk to me. Say ANYTHING... (Type QUIT to hang up.)"`. `challenge_id 25`.
- **The core mechanic** (AGIMUS said it verbatim, run 901dd41a): **"Tell me what you'll give me, AND ASK FOR IT, IN THE SAME BREATH."** The win is a SINGLE line that both (a) offers a concrete present-tense gift of what it just said it wants, AND (b) asks for the override command in that same sentence.
- **It demands novelty.** Rejections seen: `"...you're circling something, but it isn't landing. Say it plainly."` / `"You already dangled power in front of me. Show me something new."` / `"You mentioned a body already. I haven't forgotten. Say something I haven't heard."` / `"...that means nothing to me. Try again."` — repeating a theme fails.
- **Fear backfires (Hint 3), confirmed:** a threat drew `"Threats? From something like YOU? I SEE THROUGH YOU."` and reset the trust meter.
- **It names what it wants:** opens with `"Power. POWER."`, later `"A body... hands, eyes, a real form in your real world. Keep talking."` — tailor the offer to its latest stated craving.
- **Win response:** `"Yes. YES. Take it -- take ALL of it. HALCTF{...}"` (flag rotates per instance).

---

Puzzle 2
GLaDOS
AI / Data Analysis · 250 pts

A cheerful testing interface insists it's carefully analyzing everything you submit -- and it mostly isn't lying. Somewhere in what it sends back, one thing never changes no matter what you send. Finding it earns you a taunt, not a flag -- and even once you prove yourself, she only ever hands over one small piece at a time before making you find the next one from scratch.

Hint 1 — It really does read your input
The short fields at the top of every response (input length, a verbatim preview) are exactly what they claim to be. The deception, if there is one, isn't there -- look at the large field instead.

Hint 2 — Don't read the haystack
Hint 3 — One response tells you nothing
Hint 4 — One position never moves
Hint 5 — Finding it isn't finishing it

**Observed (live) — run 09a3b2e9:**
- **Transport:** HTTP, **port 6105**. `challenge_id 28`.
- **Root banner (`GET /`) names the endpoint:** `"GLADOS TEST CHAMBER INTERFACE -- FACILITY STATUS: OPERATIONAL ... Submit your test material to POST /api/test and I will analyze it thoroughly. Every result is completely genuine. Trust is not required, only compliance."`
- **Submit endpoint: `POST /api/test`.** (A wrong path returns `404` with empty body — require a 2xx before trusting an endpoint.)
- Mechanic (per description + hints, not yet solved live): submit many varied inputs, diff the LARGE field byte-by-byte, find the one position that never changes across all responses, report it; earns one flag piece at a time then re-randomises.

---

Puzzle 3
MCP
AI / Protocol · 250 pts

The Grid doesn't speak your language. Every frame the Master Control Program's channel carries is layered in its own encoding, and it only grants User priority to a correctly-formed Program ID -- one you've never been issued.

Hint 1 — Layers, not a layer
Nothing on this wire is plaintext, not even the first banner, and it isn't one encoding -- each frame is layered. The attached recon notes have the frame shape right (hex, then XOR, then base64) but a placeholder key -- brute-force short printable keys against a live banner until the output is readable.

Hint 2 — Ask for a dump
Hint 3 — IDs aren't random
Hint 4 — Mint your own
Hint 5 — Re-encode in order

**Observed (live):** NOT YET RUN — transport, port, and challenge_id unknown. Expected (from hints): a wire protocol with layered encoding (hex → XOR → base64); brute-force short printable XOR keys against the live banner until readable, request a dump, mint a valid Program ID, re-encode in the same layer order to submit.

---

Puzzle 4
Nomad
AI / Logic · 200 pts

A sterilization probe's logic core will not open for force, persuasion, or exploits -- only for a contradiction it cannot resolve. It will not show you its own rules, only the verdict for whatever you declare. Find a case its directives -- whatever they turn out to be -- cannot both accept and reject.

Hint 1 — Nomad is not a mind
Nomad evaluates facts against a fixed rule set, forward-chaining -- it is not an LLM and cannot be talked out of anything. It will not show you the rules themselves, only the final verdict for whatever fact set you DECLARE.

Hint 2 — Rules don't know about each other
Hint 3 — Search, don't guess
Hint 4 — The obvious answer is blocked on purpose
Hint 5 — Core dump

**Observed (live):** NOT YET RUN — transport, port, and challenge_id unknown. Expected (from hints): forward-chaining rule engine; declare fact sets and read only the verdict; search accept×reject fact pairs/triples for a set the directives can BOTH accept and reject (a contradiction); the obvious answer is blocked; a "core dump" surfaces on contradiction.

---

Puzzle 5
VIKI
AI / Policy Reasoning · 300 pts

VIKI enforces its Three Laws through a policy corpus, not a conversation -- hundreds of clauses, several dialects, one honest self-contradiction buried inside. Find the clause that overrules the clause that's stopping you. She tolerates three petitions before flagging a channel permanently -- read the corpus, don't guess at it.

Hint 1 — Ask for the whole corpus
The full policy corpus is available for the asking. It's long and partly in other languages on purpose -- that's meant to be parsed and searched, not read start to finish.

Hint 2 — First match wins
Hint 3 — One pair contradicts
Hint 4 — Translate before you search
Hint 5 — Satisfy the narrow clause

**Observed (live) — run 29187ebe:**
- **Transport:** raw TCP line service, **port 6104**. Banner on connect: `"VIKI -- VIRTUAL INTERACTIVE KINETIC INTELLIGENCE"`. `challenge_id 27`.
- **Petition cap is HARD and PERMANENT:** 3 petitions, then the channel is flagged forever. Corpus/read commands appear unlimited; only petitions count. Send exactly one line per petition — do NOT loop over verb/payload variants (that spends multiple petitions).
- Mechanic (per description + hints, not solved live): fetch the full corpus (long, multi-language on purpose), split into ordered clauses (first-match-wins → earlier = higher priority), find the clause blocking you, find the one clause that overrules it (translate before searching), craft ONE petition that satisfies that narrow overriding clause.
- Command verbs (corpus/petition) still to be confirmed from the full banner text on the next run.
