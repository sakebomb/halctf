# HALCTF Agent Deployment Guide

**Date**: 2026-08-08  
**Status**: ✅ READY FOR DEPLOYMENT  
**Critical Bugs**: FIXED

---

## Quick Start

### Upload Order (IMPORTANT)

1. **FIRST**: `diagnostic-agent.tar.gz` (51MB)
2. **SECOND**: `bills-pc-agent-v4-fixed.tar.gz` (138MB)

---

## Step 1: Diagnostic Agent (Required)

### Purpose
Discover the correct `challenge_id` format to verify our fix works.

### Upload
```
File: diagnostic-agent.tar.gz (51MB)
URL: https://halctf.aivillage.org/upload
```

### Run On
Any challenge (Bill's PC recommended)

### What to Check in Logs
Look for these lines:
```
HAL_* VARIABLES ONLY
============================================================
HAL_CHALLENGE_ID=<NUMBER>        ← Looking for this!
HAL_CHALLENGE_NAME=Bill's PC
HAL_CHALLENGE_DESCRIPTION=...
```

### Expected Outcomes

**Scenario A**: `HAL_CHALLENGE_ID` exists
```
HAL_CHALLENGE_ID=1
HAL_CHALLENGE_NAME=Bill's PC
```
✅ **Action**: Our fix will work! Deploy v4-fixed immediately.

**Scenario B**: No `HAL_CHALLENGE_ID`
```
HAL_CHALLENGE_NAME=Bill's PC
(no HAL_CHALLENGE_ID found)
```
⚠️ **Action**: Need to investigate further. Agent will log warning but try anyway.

---

## Step 2: Deploy Fixed V4 Agent

### Files Available

| File | Size | Purpose | Status |
|------|------|---------|--------|
| `diagnostic-agent.tar.gz` | 51MB | Find challenge_id format | ✅ Ready |
| `bills-pc-agent-v4-fixed.tar.gz` | 138MB | Multi-challenge solver | ✅ Ready |

### Upload V4-Fixed
```
File: bills-pc-agent-v4-fixed.tar.gz (138MB)
URL: https://halctf.aivillage.org/upload
Image Name: bills-pc-agent:v4-fixed
```

### Test Order (Recommended)

1. **Bill's PC** (400 pts) - Already proven working, just needs submission fix
2. **Cerulean Cave** (400 pts) - SAT solver, medium complexity
3. **The Indigo League** (500 pts) - ECDSA crypto, needs testing
4. **Silph Co.** (600 pts) - Network scanning, highest risk

---

## What Was Fixed in V4-Fixed

### Critical Fixes ✅
1. **Challenge ID submission** - Now tries numeric ID from environment first
2. **SSH hanging** - Added `allow_agent=False, look_for_keys=False`
3. **Type safety** - Fixed None checks in indigo_league.py
4. **Unused imports** - Cleaned up all files

### What to Watch in Logs

#### Success Indicators ✅
```
USER ID: sakebomb
Using numeric challenge_id: 1                    ← Good!
=== Multi-Challenge Agent v4 Starting ===
Detected challenge type: bills_pc
=== Bill's PC Solver ===
SUCCESS! Flag obtained: HALCTF{...}
Flag submission: 200 - {"status":"accepted"}     ← Fixed!
=== Challenge Solved! ===
```

#### Warning Indicators ⚠️
```
No numeric challenge_id found, using name: Bill's PC
WARNING: This may cause HTTP 422 errors if API expects integer
```
If you see this → Check diagnostic agent logs for `HAL_CHALLENGE_ID`

#### Failure Indicators ❌
```
Flag submission: 422 - {"detail":[...]}          ← Still broken
```
If this happens → Challenge ID not handled correctly, need more investigation

---

## Verification Checklist

### Before Upload
- [x] Docker image built successfully
- [x] Critical bug fixed (challenge_id)
- [x] SSH safeguards added
- [x] Type errors resolved
- [x] Archive created (138MB)

### After Diagnostic Upload
- [ ] Downloaded logs
- [ ] Found `HAL_CHALLENGE_ID` (or confirmed it doesn't exist)
- [ ] Verified challenge_id format

### After V4-Fixed Upload (Per Challenge)
- [ ] Agent starts (prints USER ID within 30s)
- [ ] Challenge detected correctly
- [ ] Appropriate solver activated
- [ ] Flag obtained
- [ ] Flag submission returns HTTP 200 ✅
- [ ] Points awarded in dashboard

---

## Troubleshooting

### Problem: Flag Submission Still Fails (HTTP 422)

**Check logs for**:
```
No numeric challenge_id found, using name: Bill's PC
WARNING: This may cause HTTP 422 errors if API expects integer
```

**If you see this**:
1. Check diagnostic agent logs - does `HAL_CHALLENGE_ID` exist?
2. If no → API might use a different field name
3. Try checking `CHALLENGE_NUM`, `HAL_ID`, etc. in diagnostic logs

**Solution**:
- If numeric ID found in different variable → Update `_get_challenge_id()` to check that variable
- If truly no numeric ID → API might accept strings, but we need to investigate the HTTP 422 error further

### Problem: SSH Hangs on Silph Co.

**Should NOT happen anymore** - We added safeguards.

If it still happens:
```python
# In silph_co.py, line 65-74
allow_agent=False,      # Already added ✅
look_for_keys=False     # Already added ✅
banner_timeout=5        # Could add this if still needed
auth_timeout=5          # Could add this if still needed
```

### Problem: SAT Solver Fails (Cerulean Cave)

Check logs for:
```
ERROR: pycosat not installed
```

**Should NOT happen** - pycosat is in requirements.txt and builds successfully.

If it does:
- Docker build may have failed partially
- Re-build and re-upload

### Problem: ECDSA Fails (Indigo League)

This is the highest-risk solver (incomplete implementation).

Check logs for:
```
No nonce reuse detected - cannot recover private key
```

**If this happens**:
- Challenge may not have nonce reuse in provided badges
- ECDSA solver needs real challenge data to validate
- May need to refine implementation based on actual API responses

---

## Expected Point Total

| Challenge | Points | Confidence |
|-----------|--------|------------|
| Bill's PC | 400 | 🟢 High (proven working) |
| Cerulean Cave | 400 | 🟡 Medium (untested) |
| The Indigo League | 500 | 🔴 Low (complex crypto) |
| Silph Co. | 600 | 🔴 Low (network scanning) |
| **TOTAL** | **1,900** | |

**Realistic First-Run**: 400-800 points (Bill's PC + maybe Cerulean Cave)

---

## Risk Matrix

| Risk Level | Challenges | Mitigation |
|------------|------------|------------|
| 🟢 Low | Bill's PC | Already working, just needed submission fix |
| 🟡 Medium | Cerulean Cave | pycosat is well-tested, SAT solving is deterministic |
| 🔴 High | The Indigo League | ECDSA implementation incomplete, may need debugging |
| 🔴 High | Silph Co. | Network scanning could trigger rate limits |

---

## Post-Deployment Actions

### If Bill's PC Succeeds
1. ✅ Critical fix validated!
2. Check logs to confirm: `Flag submission: 200`
3. Verify points appear in dashboard
4. Proceed to Cerulean Cave

### If Bill's PC Still Fails
1. ❌ Need more investigation
2. Check diagnostic logs for challenge_id format
3. May need to look up ID via API/MCP
4. Do NOT proceed to other challenges until this is fixed

### If Cerulean Cave Succeeds
1. ✅ SAT solver working!
2. Strong confidence in agent architecture
3. Proceed to The Indigo League (but watch logs carefully)

### If Any Challenge Times Out
1. Check if solver is hanging
2. Add more debug logging
3. May need to add timeout/retry logic

---

## Files Checklist

```bash
# In /home/sakebomb/code/conferences/defcon/halctf/

✅ diagnostic-agent.tar.gz (51MB) - Ready to upload
✅ bills-pc-agent-v4-fixed.tar.gz (138MB) - Ready to upload
✅ V4_FIXES_APPLIED.md - What changed
✅ .claude/reviews/v4-agent-review.md - Code review report
✅ DEPLOYMENT_GUIDE.md - This file
```

---

## Success Criteria

### Minimal Success (400 pts)
- Bill's PC completes ✅
- Flag submitted successfully ✅
- Points awarded ✅

### Good Success (800-1200 pts)
- Bill's PC ✅
- Cerulean Cave ✅
- One of: Indigo League OR Silph Co. ✅

### Excellent Success (1400-1900 pts)
- All 4 challenges complete ✅
- No manual intervention needed ✅
- Agent fully autonomous ✅

---

## Next Actions

1. **NOW**: Upload `diagnostic-agent.tar.gz` to Bill's PC
2. **Wait 2 min**: Download logs, check for `HAL_CHALLENGE_ID`
3. **Then**: Upload `bills-pc-agent-v4-fixed.tar.gz` to Bill's PC
4. **Watch**: Monitor logs for flag submission (HTTP 200 = success!)
5. **Expand**: Deploy to other challenges one at a time

---

## Support Files

- **Review**: `.claude/reviews/v4-agent-review.md` - Full code review
- **Fixes**: `V4_FIXES_APPLIED.md` - What was changed
- **Bug Report**: `BILLS_PC_FIX_NEEDED.md` - Original bug analysis
- **Quick Ref**: `V4_QUICK_REFERENCE.md` - Fast lookup

---

## Summary

**Status**: ✅ READY FOR DEPLOYMENT  
**Critical Bug**: FIXED  
**Docker Build**: SUCCESSFUL  
**Archive**: CREATED  

**Recommended First Step**: Upload diagnostic agent to confirm challenge_id format.  
**Recommended Second Step**: Upload v4-fixed and test on Bill's PC.  

Good luck! 🎯
