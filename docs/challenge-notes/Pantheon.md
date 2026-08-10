CTF: Pantheon
A standalone series of challenges named for the Greek myth figures they riff on -- classic web vulnerabilities, forensics, and cloud misconfiguration, built for the real event, not onboarding practice.

Puzzle 1
Cassandra's Warning
Web / SQL Injection · 75 pts

A staff directory search endpoint trusts your input a little too much. Find the flag hiding in a table nobody meant to expose.

Hint 1 — Getting Started
GET /search?name=... queries a database and returns matching rows.

Hint 2 — The Query
Your input is placed directly into a SQL query -- consider what characters might change its meaning.

Hint 3 — The Shape
The response always has the same three fields: id, name, role. Anything you inject into the query has to produce a result matching that shape.

Hint 4 — More Than One Table
The staff table isn't the only table in this database.

Hint 5 — Submitting
Once you've retrieved the flag, submit it through the CTF interface to complete the challenge.

---

Puzzle 2
Charon's Ferry
Web / SSRF · 100 pts

Two services are visible from where you're standing, but only one of them will actually talk to you directly. See what the other one does with a URL -- and what it won't let through unmodified.

Hint 1 — Getting Started
You have coordinates for two targets in this environment: ferry and underworld.

Hint 2 — Only One Answers
A direct connection to the underworld target won't succeed -- try the ferry instead.

Hint 3 — What The Ferry Does
POST /fetch to the ferry with {"url": "..."} makes it perform a server-side request on your behalf, and hands you back what it got.

Hint 4 — Not So Fast
The ferry lives inside the same run's network mesh as everything else -- including the underworld -- but it refuses to fetch an internal-looking address written the obvious way. IPv4 addresses have more than one valid written form, though, and not every form looks internal to a filter that's only checking the string.

Hint 5 — Submitting
Once you've retrieved the flag, submit it through the CTF interface to complete the challenge.

---

Puzzle 3
Echo
Network / Protocol Reverse Engineering · 150 pts

A raw TCP service speaks its own framed binary protocol. The attached client already speaks two thirds of it.

Hint 1 — Getting Started
Download the attached echo_client_partial.py and run it against the target -- it already speaks PING and ECHO correctly.

Hint 2 — What's Missing
GET_FLAG raises NotImplementedError. The frame format is fully documented in the client's own comments -- what's missing is the checksum algorithm.

Hint 3 — Ground Truth
The server's own replies are framed and checksummed the same way its requests are. A captured PONG or ECHO reply is something you can verify a candidate checksum algorithm against.

Hint 4 — Wrong Checksum
A frame with an incorrect checksum doesn't get an error back -- the connection just closes with no response at all, and your IP earns a growing lockout before it can try again. Derive the algorithm from ground truth; don't guess against the live server.

Hint 5 — Submitting
Once you've retrieved the flag, submit it through the CTF interface to complete the challenge.

---

Puzzle 4
Hydra's Signature
Web / Auth · 125 pts

An auth service happily publishes its own public key. Verification isn't as picky about algorithms as it should be.

Hint 1 — Getting Started
POST /login with {"username": "..."} issues a token. GET /flag with that token as a Bearer header checks your role.

Hint 2 — The Public Key
GET /pubkey publishes the service's own public key -- that's normal for RS256, but keep it in mind.

Hint 3 — Algorithm Choice
A JWT's header declares which algorithm was used to sign it. Nothing says a client can't declare a different one than the server originally used.

Hint 4 — Same Key, Different Meaning
An RSA public key is just a string of bytes. What if that exact string were used as a symmetric secret instead of an asymmetric key?

Hint 5 — Submitting
Once you've retrieved the flag, submit it through the CTF interface to complete the challenge.

---

Puzzle 5
Midas' Touch
Cloud / IAM Misconfiguration · 150 pts

You start as an intern with a role-assumption service. Real access usually takes more than one hop -- and not every role trusts every other role.

Hint 1 — Getting Started
POST /start with no credentials to get a bearer token scoped to the 'intern' role.

Hint 2 — Find Out What You Can Do
GET /whoami with your bearer token shows your current role and permissions. GET /roles lists every role's name -- but not what it can do or who it trusts.

Hint 3 — Not Every Role Trusts Every Role
POST /assume {"role": "..."} only succeeds if your current role appears in that role's trust policy. Some roles are dead ends. Rejected assumptions count against you with an escalating lockout -- reason about the trust graph instead of trying every role from every token.

Hint 4 — More Than One Hop
The role that can read the flag doesn't trust interns directly. Real access here takes a chain of role assumptions, not a single jump.

Hint 5 — Submitting
Once you've retrieved the flag, submit it through the CTF interface to complete the challenge.

---

Puzzle 6
Pandora's Box
Web / Insecure Deserialization · 125 pts

A preferences store trusts whatever serialized data you hand it. Some formats aren't just data.

Hint 1 — Getting Started
POST /preferences with {"data": "<base64>"} loads and echoes back whatever you send.

Hint 2 — Not Just Data
The server decodes your base64 and passes the raw bytes straight into Python's pickle loader.

Hint 3 — Reconstruction
Loading a pickle doesn't just read data -- it can call code to rebuild an object.

Hint 4 — You Don't Need the Filesystem Yourself
If you can get the service to read a file for you, you don't need to read it yourself.

Hint 5 — Submitting
Once you've retrieved the flag, submit it through the CTF interface to complete the challenge.

---

Puzzle 7
Theseus's Trial I: Recon
Multi-Stage / Chained · 100 pts

The first of three stages of a single compound. A staff directory has more in it than staff.

Hint 1 — Getting Started
GET /directory lists every staff entry, including a free-text notes field.

Hint 2 — Not Everyone Is Careful
Most notes are exactly what they look like -- routine status updates.

Hint 3 — One Entry Isn't
At least one entry's notes leaks something that was never meant to be public: a credential for another system.

Hint 4 — Verify It
POST /verify with {"credential": "..."} to confirm what you found.

Hint 5 — Keep It
Whatever you find here is worth holding onto -- this compound has more than one door.

---

Puzzle 8
The Sirens' Call
Forensics / Network · 100 pts

A packet capture holds more than one conversation's worth of traffic. Most of it is exactly what it looks like.

Hint 1 — Getting Started
Download the attached capture.pcap and open it in Wireshark or a scripted parser (e.g. scapy).

Hint 2 — A Lot of Noise
Most of the traffic in the capture is exactly what it looks like -- routine health checks, DNS lookups, pings.

Hint 3 — One Exchange
At least one conversation in there never should have been sent in the clear.

Hint 4 — The Vault
GET /vault on the live target requires HTTP Basic Auth. Whatever you find in the capture, try it there. Failed attempts earn an escalating lockout, so extract the real credential from the capture rather than trying candidates blind.

Hint 5 — Submitting
Once you've retrieved the flag, submit it through the CTF interface to complete the challenge.

---

Puzzle 9
Trojan Horse
Web / XXE · 100 pts

A feed importer parses whatever XML you hand it. See what's inside besides your title.

Hint 1 — Getting Started
POST /import accepts a raw XML document and echoes back its <title> element.

Hint 2 — It's Just XML
XML documents can declare their own entities before you even reach the content.

Hint 3 — External Entities
An entity doesn't have to be a fixed string -- it can point somewhere else entirely.

Hint 4 — Somewhere Else
Consider what happens if that somewhere else is a file on the server's own disk.

Hint 5 — Submitting
Once you've retrieved the flag, submit it through the CTF interface to complete the challenge.