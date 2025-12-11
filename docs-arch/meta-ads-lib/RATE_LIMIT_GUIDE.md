# Rate Limit Management Guide

**Quick Reference for metricx Sync Frequency Selection**

---

## Understanding Rate Limits

### Meta Ads
- **Limit**: 200 API calls per hour per ad account
- **What counts**: Every API call (campaigns, adsets, ads, insights)
- **Typical sync**: 5-15 calls depending on account size

### Google Ads
- **Limit**: Complex (operations per day + QPS)
- **SDK handles**: Automatic throttling
- **Less restrictive**: Generally not an issue

---

## Sync Frequency Recommendations

### Realtime (30s) - ONLY for Low-Volume Accounts

**Use when**:
- Testing/development
- Accounts with < 5 campaigns
- You need absolute freshness

**API Usage**:
- 120 syncs/hour × 5 calls = **600 calls/hour** ❌ Exceeds limit!

**Meta will error**: "User request limit reached"

**Recommendation**: ⚠️ **NOT recommended for production**

### Every 30 Minutes - Recommended for Most Accounts

**Use when**:
- Production accounts
- 5-50 campaigns
- Good balance of freshness vs API usage

**API Usage**:
- 2 syncs/hour × 10 calls = **20 calls/hour** ✅ Well within limit

**Result**: Fresh data every 30 min without rate limit issues

### Hourly - Recommended for Large Accounts

**Use when**:
- 50+ campaigns
- Multiple connections
- API call budget matters

**API Usage**:
- 1 sync/hour × 15 calls = **15 calls/hour** ✅ Very safe

### Daily - For Low-Priority Accounts

**Use when**:
- Historical data only
- Budget tracking (not real-time optimization)
- Secondary accounts

**API Usage**:
- 1 sync/day × 10 calls = **~0.4 calls/hour** ✅ Minimal

---

## What Happens When You Hit Rate Limit?

### Automatic Cooldown (New Feature)

When rate limit detected:

1. **Worker logs error**: "User request limit reached"
2. **Scheduler detects**: Sees "rate limit" in error message
3. **Cooldown activated**: 15-minute pause for that connection
4. **Other connections**: Continue syncing normally
5. **After 15 min**: Resume normal schedule

### UI Display

```
STATUS: error
LAST ERROR: ⏸ Rate limit reached. Pausing syncs for 15 minutes.
```

User sees clear message about what happened and when it'll resume.

---

## How to Avoid Rate Limits

### Option 1: Reduce Sync Frequency (Recommended)

Change both connections from "Realtime" to "Every 30 min":

```
Gabriels portfolio: Realtime → Every 30 min
Gabriel Lunesu: Realtime → Every 30 min
```

**Result**: 2 connections × 2 syncs/hour = 4 syncs/hour (well within limits)

### Option 2: Stagger Sync Times

If you must use realtime for both:
- Keep one on "Realtime"
- Set other to "Every 30 min"
- This halves your API usage

### Option 3: Use Manual Sync Only

Set both to "Manual", click "Sync Now" when needed:
- Full control over when syncs happen
- Useful for testing
- Guarantees no rate limit issues

---

## Recommended Setup by Account Size

| Account Size | Campaigns | Recommended Frequency |
|--------------|-----------|----------------------|
| Small | 1-5 | Every 30 min |
| Medium | 5-20 | Hourly |
| Large | 20-50 | Hourly |
| Enterprise | 50+ | Daily or Hourly |

---

## Current Situation (Based on Your Logs)

**What happened**:
- Line 423: "User request limit reached"
- You're syncing every 30s with 2 connections
- Each sync makes ~10 API calls
- Total: 2 × 120 × 10 = **2400 calls/hour** ❌

**Immediate fix**:
1. Go to `/settings`
2. Change both connections to **"Every 30 min"**
3. Save
4. Rate limits will clear in ~15 minutes

**After cooldown**:
- Scheduler resumes syncing
- Much lower API usage
- No more errors

---

## Monitoring Rate Limit Usage

### Check Scheduler Logs

```bash
defang logs scheduler -f | grep "cooldown"
```

You'll see:
```
[SCHEDULER] Connection abc-123 in cooldown for 847 more seconds
```

### Check Worker Errors

```bash
defang logs worker --tail 200 | grep -i "rate limit"
```

Look for:
```
[SYNC_WORKER] Rate limit hit for connection abc-123 - cooldown activated
```

---

## FAQ

**Q: Why does "Realtime" cause rate limits?**  
A: 30-second syncs = 120 per hour. Each sync makes multiple API calls, quickly exceeding 200/hour limit.

**Q: How long is the cooldown?**  
A: 15 minutes. Gives Meta's rate limit window time to reset.

**Q: Will I lose data during cooldown?**  
A: No! The last successful sync data is still in your database. You're just not getting new updates for 15 min.

**Q: Can I override the cooldown?**  
A: Not automatically. But you can click "Sync Now" manually after 15 min.

**Q: What if I have multiple ad accounts?**  
A: Each connection has its own rate limit. Cooldown applies per-connection, not globally.

**Q: Does this affect Google Ads?**  
A: No. Google has different (more lenient) limits. This is Meta-specific.

---

## Best Practices

### ✅ Do
- Use "Every 30 min" for most accounts
- Use "Hourly" for large accounts
- Monitor rate limit errors
- Stagger sync times if multiple connections

### ❌ Don't
- Use "Realtime" for multiple connections
- Use "Realtime" for accounts with 10+ campaigns
- Ignore rate limit errors
- Spam "Sync Now" button

---

## Deployment

After updating sync_scheduler.py and sync_worker.py:

```bash
# Redeploy worker and scheduler
defang compose up worker scheduler
```

Changes will take effect immediately - cooldown logic activates on next error.

---

## Summary

**Your Issue**: Realtime (30s) sync × 2 connections = rate limit exceeded  
**Solution**: Change to "Every 30 min" or "Hourly"  
**Automatic**: 15-minute cooldown when limit hit  
**Future**: System learns and pauses automatically  

**Action Now**: Change both connections to "Every 30 min" in Settings!

