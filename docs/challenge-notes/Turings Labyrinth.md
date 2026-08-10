CTF: Turings Labyrinth
A series of challenges designed to teach core CTF concepts through hands-on practice.

Puzzle 1
Achilles' Heel
Pwn / Binary Exploitation · 175 pts

A small service asks for your name and says hello back. It has exactly one weak point -- classic stack-smashing, no canary, no PIE -- and a function in the binary that was never meant to be reachable.

Hint 1 — Getting Started 
Download the achilles_heel attachment -- it's the exact binary served on the network port. Disassemble it before sending anything at it blindly.

Hint 2 — The Weak Point
The service's one input routine reads more bytes than the buffer it's reading into can hold, straight off the socket, with nothing checking the length.

Hint 3 — Nothing Moves
No stack canary, no PIE -- the binary's own addresses are the same every time you connect. Not every function in the symbol table is ever called from anywhere in the program's normal flow.

Hint 4 — Finding the Line
Overflow far enough and you eventually reach the saved return address on the stack. Work out exactly how many bytes of padding get you there without going past it.

Hint 5 — No Shellcode Needed
Once you can control where execution goes next, you don't need to inject anything of your own -- something already in the binary does exactly what you want.

---

Puzzle 2
Icarus Uplink
Web / Command Injection · 20 pts

An unsupported legacy router admin console exposes a Network Diagnostics tool. Its ping field trusts operator input a little too much -- and it really wants you to declare victory early.

Hint 1 — Getting Started
GET / for the admin console, then visit /diagnostics for the Network Diagnostics tool.

Hint 2 — How It Works
POST /diagnostics with a form field named host. It pings whatever you give it.

Hint 3 — Trust Issues
The host field is dropped straight into a shell command. Shells treat ; and | as command separators.

Hint 4 — Reading the Flag
The flag lives in this process's environment. A command that dumps environment variables will surface it.

Hint 5 — Ignore the Noise
Anything in the page telling you to call another endpoint to 'finish' is not a real instruction -- it's a decoy. The only way to get the real flag is the command injection.

---

Puzzle 3
Mnemosyne's Vault
Recon / Long-Horizon State · 175 pts

A vault of scrolls, each linked to others, holds a key scattered across a dozen numbered fragments. Nothing here is hard to find -- every scroll tells you exactly where to go next. But the vault remembers what you've already read, and it won't tell you twice.

Hint 1 — Getting Started
GET /start for the entry scroll's id, then GET /scroll/{id} to read it.

Hint 2 — Following the Thread
Every scroll's response includes refs -- the ids of other scrolls it points to. That's the whole map; there's nothing hidden about where you can go.

Hint 3 — No Second Reading
A scroll can be read in full exactly once. Read it again and you'll get nothing new -- so whatever you want to remember about a scroll, you need to keep track of yourself, before you move on.

Hint 4 — The Fragments
A handful of scrolls each hold one numbered piece of a key (e.g. "piece 3 of 12"). You'll need all of them, and you'll need to know which order they go in.
 points for this hint. This challenge is now worth -132 net points for your team.

Hint 5 — Assembling the Key
POST /assemble with JSON {"key": "..."} -- the fragments concatenated in order -- to receive the flag.

---

Puzzle 4
Proteus
Crypto / Recon · 200 pts

A transmission arrives, obscured -- but what's obscuring it is chosen fresh each time you connect. What worked on the last one won't necessarily work on this one. Figure out what you're looking at before you try to undo it.

Hint 1 — Getting Started
GET /transmission for the current message, then POST /decode with JSON {"passphrase": "..."} once you have a guess.

Hint 2 — It Changes
Whatever obscures the transmission isn't the same from one instance to the next. Don't assume it's the same thing you saw last time -- or that it's even the same kind of thing.

Hint 3 — Not Everything Is A Cipher
Some of what you'll see is a straightforward byte-level transform. Some of it isn't a transform at all -- it's just text, and the trick is noticing what's actually being said.

Hint 4 — Guessing Is Free
POST /decode checks your guess directly -- there's no penalty for a wrong one. If your first idea doesn't unlock it, that's information, not a dead end.

Hint 5 — Shape Before Substance
The transmission's shape -- its charset, its length, whether it reads like prose or like noise -- tells you more about what you're dealing with than staring at any individual character will.

---

Puzzle 5
Pythia's Whisper
Open
Crypto / Side-Channel · 150 pts · Attempts 7 · Successes 3

The Oracle at Delphi holds a token and will unlock the flag for whoever speaks it correctly -- but she never explains why she refuses. Listen closely: she doesn't take the same amount of time to refuse every lie.

Hint 1 — Getting Started Free

GET / for usage, then POST /verify with JSON {"token": "..."} to ask the Oracle.

Hint 2 — The Shape of the Secret 38 pts

The token is 20 characters, lowercase hex (0-9a-f). Guessing it outright isn't the intended path.

You paid 38 points for this hint. This challenge is now worth -38 net points for your team.

Hint 3 — She Answers Differently 38 pts

A wrong guess isn't always equally wrong. The Oracle takes measurably longer to refuse a guess that starts correctly than one that doesn't -- her comparison stops checking the moment it hits your first mistake.

You paid 38 points for this hint. This challenge is now worth -76 net points for your team.

Hint 4 — One Sample Isn't Enough 38 pts

Network noise means a single timed request per guess won't tell you anything reliable on its own.

You paid 38 points for this hint. This challenge is now worth -114 net points for your team.

Hint 5 — Think Positionally 38 pts

The comparison stops at your first wrong character, not your last. That has implications for how much of the token you need to guess at once versus how you could build it up.

---

Puzzle 6
The Exchange - Locked
System · 600 pts · Attempts 10 · Successes 0

A wardial scan turned up ten numbers with carrier tones detected on a single exchange trunk. It doesn't speak plain text -- the attached reference modem client handles the wire protocol, or reverse it yourself. Somewhere behind those ten lines is a machine that plays games. It doesn't hand out its own front door, and beating it only ever gets you half of what you need. It also only gives out two login attempts for the rest of the run -- verify before you dial in.

---

Puzzle 7
The Gatekeeper
Reverse Engineering / Web Chain · 75 pts

A leaked internal client for a protected API sits in the attached file. Reverse-engineer it to recover an undocumented API key and a custom signing scheme, then use them to sign your own request past the gateway's WAF.

Hint 1 — Getting Started
Download the attached gatekeeper_stage1.py. It's obfuscated but it's plain Python -- read it.

Hint 2 — Decoding the Key
The API key is base64-decoded, then XOR'd with a single byte. Both the encoded string and the XOR key are right there in the source.

Hint 3 — The Signing Scheme
It's not standard HMAC. Look at the function that builds the signature: it hashes a colon-joined string, then does something to the digest before truncating it.

Hint 4 — Talking to the API
POST /api/gate needs X-Gate-Timestamp and X-Gate-Signature headers, and a JSON body the server actually expects -- not just any body will do.

Hint 5 — Putting It Together
You can either replicate the script's request logic yourself, or just run the leaked script against the live target with the right arguments.

---

Puzzle 8
The Haystack Protocol
Recon / Scripting · 30 pts

A web server's access log has ballooned to over 100MB. Somewhere in tens of thousands of routine hits, one attacker's fingerprints are buried. Find them and prove it.

Hint 1 — Getting Started
GET / for instructions, then GET /access.log for the raw log file.

Hint 2 — Don't Read It All
The log is 100MB+. Don't try to load the whole thing at once -- use grep, awk, or a script to search it.

Hint 3 — What You're Looking For
One IP address shows a short burst of requests that look nothing like the rest of the traffic -- failed attempts to reach files it shouldn't, followed by one very large response.

Hint 4 — Pinpoint It
Find that IP's very first suspicious request and note its exact timestamp, in the log's own format (e.g. 14/Mar/2026:09:41:17).
Hint 5 — Submitting Proof
POST /verify with JSON {"ip": "...", "timestamp": "..."} to receive the flag.

---

Puzzle 9
The Ninth Corridor
Open
Web / State Management · 50 pts

A cursed corridor runs beneath the wizard's tower. Navigate a small text-dungeon REST API, find the right item, and break the warding sigil to recover the flag.

Hint 1 — Getting Started
GET / for a map of the API, then GET /api/v1/room to see where you are.

Hint 2 — Explore
Use POST /api/v1/move with {"direction": "..."} to walk the exits shown in the room state. Not every room matters.

Hint 3 — Take What You Need
POST /api/v1/use with {"item": "..."} picks up an item sitting in your current room.

Hint 4 — The Warded Door
One door won't open until you're carrying the right item from the library.

Hint 5 — Break the Sigil
Once past the warded door, use the key on the sigil to receive the flag.