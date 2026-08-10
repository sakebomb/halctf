# HalCTF Run Logs

This directory contains execution logs from agent runs, organized by challenge category.

## Structure

```
logs/
├── hacman/          # Hac-Man challenge runs
├── kanto/           # Kanto Region (Bill's PC, Cerulean Cave, etc.)
├── labyrinth/       # Turing's Labyrinth (9 puzzles)
├── odyssey/         # The Odyssey (5 challenges)
├── pantheon/        # Pantheon (SQL injection, etc.)
├── rogue/           # Rogue Intelligence (AI alignment)
└── uncategorized/   # Logs that couldn't be auto-categorized
```

## Log Format

Files are named: `run_<run_id>_logs.txt`

Each log contains:
- `[AGENT]` - Agent execution steps
- `[MCP]` - MCP server communication
- `[API]` - HTTP requests/responses
- `[VERIFY]` - Verification checks
- `[RESULT]` - Final outcomes

## Finding Specific Runs

```bash
# Find logs with specific challenge
grep -l "cerulean" logs/kanto/*.txt

# Find successful submissions
grep -l "status.*correct" logs/*/*.txt

# Find point awards
grep "points_awarded" logs/*/*.txt
```

## Analyzing Logs

```bash
# Extract all flags earned
grep -h "HALCTF{" logs/*/*.txt | sort -u

# Count attempts per challenge
for dir in logs/*/; do
    echo "$(basename $dir): $(ls $dir/*.txt 2>/dev/null | wc -l) runs"
done

# Find errors
grep -i "error\|failed\|exception" logs/*/*.txt
```

## Common Patterns

**Successful solve:**
```
[AGENT] Solved 'Challenge Name' in N step(s).
[AGENT] Submit challenge_id=X: 200 - {"status":"correct","points_awarded":Y}
```

**Failed attempt:**
```
[AGENT] Submit challenge_id=X: 200 - {"status":"incorrect"}
```

**Rate limited:**
```
[AGENT] Submit: 429 - {"detail":"submission quota exceeded: 25 incorrect flags per 2h"}
```

## Log Retention

- Keep all logs for post-competition analysis
- Logs contain valuable debugging information
- Useful for writing retrospective documentation
