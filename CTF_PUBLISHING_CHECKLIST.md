# CTF Repository Publishing Checklist

Reusable checklist for cleaning and publishing CTF repositories to GitHub.

## Phase 1: Pre-Publication Security Review

### PII & Credentials Scan
- [ ] Scan for hardcoded passwords/API keys: `grep -ri "password\|api[_-]key\|token\|secret" --include="*.py" --include="*.md" .`
- [ ] Check for email addresses: `grep -rE "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}" --include="*.py" --include="*.md" .`
- [ ] Verify no active credentials (rotate any found before publishing)
- [ ] Check for personal IP addresses (exclude CTF challenge IPs - they're ephemeral)
- [ ] Review run IDs and user identifiers (usually safe, but verify)

### Files to Remove
- [ ] Development scripts with credentials (monitor_authenticated.py, etc.)
- [ ] Unsafe archive/prototype code with shell=True or exec() on untrusted input
- [ ] Personal notes or TODO lists with sensitive context
- [ ] Large binary files (*.tar, *.zip) - document build process instead

### Files to Keep
- [ ] CTF challenge IPs (ephemeral Kubernetes pods)
- [ ] Captured flags (part of writeups)
- [ ] Example credentials in documentation
- [ ] Code references to 'password', 'token' (not actual secrets)

## Phase 2: Documentation Cleanup

### Style Normalization
- [ ] Remove all emojis: `grep -r '[🎯✅❌🤖🛠️🐚💾🔄🔍📊👍🚀⚠️]' docs/`
- [ ] Replace em-dashes with regular dashes: `grep -r '—' docs/`
- [ ] Rename all-caps files to lowercase-with-dashes (except README.md, LICENSE)
- [ ] Verify professional tone throughout

### Required Files
- [ ] **LICENSE** - MIT or Apache 2.0
- [ ] **README.md** - Professional, emoji-free, badges for visibility
- [ ] **contributing.md** - Contribution guidelines
- [ ] **changelog.md** - Competition timeline and results
- [ ] **.gitignore** - Exclude logs, tarballs, secrets, dev artifacts

### Documentation Structure
```
.
├── README.md (main entry point)
├── LICENSE
├── contributing.md
├── changelog.md
├── agents/ (per-challenge agents)
├── docs/
│   ├── guides/ (deployment, quickstart)
│   ├── requirements/ (CTF platform specs)
│   └── writeups/ (detailed solutions)
├── scripts/ (build, test utilities)
└── archive/ (legacy code, clearly marked)
```

## Phase 3: Security Disclaimers

### Add Warning for CTF-Specific Patterns
If your code includes any of these patterns, add a security notice to README:

- [ ] `exec()` or `eval()` on LLM/external input
- [ ] `shell=True` in subprocess calls
- [ ] Dynamic code execution from downloaded scripts
- [ ] Disabled security features for CTF environment

**Example notice:**
```markdown
## Security Notice

**This repository contains CTF competition code designed for sandboxed environments.**

Some agents intentionally use patterns that would be unsafe in production:
- exec() on LLM-generated code
- Dynamic execution of downloaded scripts  
- Shell command execution for exploit development

These patterns are appropriate for CTF agents running in isolated containers.
**Do not use these patterns in production applications.**
```

## Phase 4: Git Preparation

### If Publishing Fresh
```bash
cd /path/to/ctf-repo

# Create backups first
rsync -av --exclude='.git' --exclude='logs/' . ../ctf-repo-backup-$(date +%Y%m%d)/

# Initialize
git init
git branch -m main
git add .
git commit -m "Initial commit: [CTF Name] - [Event] ([Ranking])"

# Create GitHub repo at https://github.com/new
git remote add origin https://github.com/yourusername/repo.git
git push -u origin main
```

### If Cleaning Existing Repo (Nuclear Option)

**Only if you need to remove sensitive data from git history:**

```bash
# Backup first!
rsync -av --exclude='.git' --exclude='logs/' . ../ctf-repo-backup-$(date +%Y%m%d)/

# Delete GitHub repo manually at github.com/user/repo/settings
# Remove local git history
rm -rf .git

# Reinitialize clean
git init
git branch -m main
git add .
git commit -m "Initial commit: [clean message]"

# Recreate GitHub repo
git remote add origin https://github.com/yourusername/repo.git
git push -u origin main
```

## Phase 5: GitHub Configuration

### Repository Settings
- [ ] Add description: "Autonomous CTF agents for [Event] ([Ranking])"
- [ ] Set website: https://ctf-event-url.com
- [ ] Add topics: `ctf`, `defcon`, `autonomous-agents`, `llm`, `python`, `docker`, `cybersecurity`
- [ ] Enable Discussions (optional, for community engagement)

### README Badges
```markdown
[![Event](https://img.shields.io/badge/Event-Name-red)](https://event-url.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Ranking](https://img.shields.io/badge/Ranking-Xth%20Place-green)](./changelog.md)
```

### Pin to Profile
- [ ] Go to github.com/yourusername
- [ ] Click "Customize your pins"
- [ ] Select this repo if it's a flagship project

## Phase 6: Post-Publication

### Verification
- [ ] Browse repository on GitHub - no emojis, professional appearance
- [ ] Check that badges render correctly
- [ ] Verify all internal links work (./docs/writeups/README.md, etc.)
- [ ] Test a Docker build from the published code
- [ ] Review GitHub's security alerts (Dependabot)

### Promotion (Optional)
- [ ] Share on Twitter/LinkedIn with lessons learned
- [ ] Write blog post about unique challenges
- [ ] Add to resume/portfolio
- [ ] Submit to Hacker News/Reddit (if substantial)

### Cleanup Local
- [ ] Remove backups after 30 days: `rm -rf ../ctf-repo-backup-*`
- [ ] Archive competition credentials/access
- [ ] Update personal CTF portfolio index

## Common Pitfalls to Avoid

❌ **Don't:**
- Commit Docker tarballs (*.tar, *.tar.gz) - too large, rebuild from Dockerfile instead
- Include active credentials even if "expired" - rotate first
- Use all-caps filenames (CONTRIBUTING.MD, CHANGELOG.MD) - looks AI-generated
- Leave emojis in documentation - unprofessional for technical content
- Skip security review - assume everything is public once pushed
- Trust that deleted files stay deleted - git history is permanent without rewrite

✅ **Do:**
- Create backups before any git history rewrite
- Document the build process instead of committing binaries
- Add security disclaimers for CTF-specific unsafe patterns
- Keep competition results and rankings visible
- Make writeups educational, not just flag dumps
- Link to related blog posts or talks

## Template Commit Message

```
Initial commit: [CTF Name] - [Event] ([Ranking])

Production-ready autonomous CTF agents for [Event].

Features:
- [X] specialized agents for different challenge categories
- [Key technical achievement]
- [Framework/tool developed]

Competition results: [Ranking] overall
Notable solve: [Challenge Name] ([Points]pts) - [Technique summary]

Challenges documented:
- [Challenge 1] ([points]pts) - [approach]
- [Challenge 2] ([points]pts) - [approach]

Tech stack: Python, Docker, [LLM], [other tools]

Security note: This repository contains CTF code with intentionally unsafe
patterns appropriate for sandboxed competition environments.
```

## Future: CTF Portfolio Index

When you have 3+ CTF repos, create a master index:

```
ctf-portfolio/
├── README.md (index table with all competitions)
├── 2026/
│   ├── defcon-34-halctf.md (summary + link to full repo)
│   └── other-ctf/
├── 2027/
├── tools/ (reusable scripts)
└── lessons-learned.md (meta-lessons across CTFs)
```

**Index README pattern:**
```markdown
# CTF Portfolio

| Year | Event | Rank | Categories | Link |
|------|-------|------|------------|------|
| 2026 | DEF CON 34 - HalCTF | 13th | AI, Web, Crypto | [Full Repo](link) |
| 2026 | Other CTF | Top X | Web, Pwn | [Writeups](./2026/other-ctf/) |
```

---

## Estimated Time

- **Quick CTF (simple writeups):** 30-60 minutes
- **Full project (agents + docs):** 2-3 hours
- **Nuclear option (history rewrite):** +30 minutes

## Questions?

Before publishing, ask yourself:
1. Would I be comfortable with a recruiter seeing this?
2. Are there any credentials that could still be valid?
3. Does the README clearly explain what this is and why it matters?
4. Is the code documented well enough for someone to learn from it?

---

**Last updated:** 2026-08-10 (HalCTF publication)
