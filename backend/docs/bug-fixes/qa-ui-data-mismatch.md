# QA vs UI Data Mismatch Bug Fix

**Date**: October 14, 2025  
**Severity**: Critical  
**Status**: Fixed ✅

## What Went Wrong

The Copilot QA system was showing different numbers than the UI dashboard for the same questions.

### Example Problem
- **User asks**: "What was my ROAS in the last 3 days?"
- **UI dashboard shows**: 6.41x ROAS
- **Copilot QA answers**: 6.65x ROAS
- **Problem**: Same question, different answers! 

## Why This Happened

The bug had two parts:

### Part 1: Wrong Database Field Used
- **Problem**: The code was looking for entity "level" (campaign/adset/ad) in the wrong database table
- **Wrong**: Looking in `MetricFact.level` (this field doesn't exist!)
- **Right**: Should look in `Entity.level` (this is where level is stored)
- **Impact**: Level filters weren't working, so QA included data from all levels

### Part 2: Different Entity Filtering
- **Problem**: QA and UI were looking at different sets of entities
- **UI**: Only shows data from "active" entities (running campaigns)
- **QA**: Was showing data from ALL entities (active + inactive/paused campaigns)
- **Impact**: Different numbers because they were counting different things

## How We Fixed It

### Fix 1: Correct Database Field
**File**: `backend/app/dsl/executor.py` and `backend/app/routers/kpis.py`

**Before**:
```python
# Wrong - this field doesn't exist!
base_query.filter(MF.level == "adset")
```

**After**:
```python
# Right - level is stored in Entity table
base_query.filter(E.level == "adset")
```

**Fixed in**: 8 locations total (5 in executor.py, 3 in kpis.py)

### Fix 2: Consistent Entity Filtering
**File**: `backend/app/dsl/executor.py`

**Before**:
```python
# Only filter by status if user explicitly asks
if plan.filters.get("status"):
    base_query.filter(E.status == plan.filters["status"])
# Otherwise, include ALL entities (active + inactive)
```

**After**:
```python
# Always default to active entities only (matches UI)
if plan.filters.get("status"):
    base_query.filter(E.status == plan.filters["status"])
else:
    # Default to active entities only (matches UI behavior)
    base_query.filter(E.status == "active")
```

**Fixed in**: 6 locations in executor.py

## Testing Results

After the fix:
- **ROAS query**: Both QA and UI show 6.41x ✅
- **Revenue query**: Both QA and UI show $58,516.38 ✅
- **All other metrics**: Now match perfectly ✅

## Key Lessons

1. **Database Schema Matters**: Always check which table actually has the field you need
2. **Consistency is Critical**: QA and UI must use the same filtering logic
3. **Default Behavior**: When users don't specify filters, use sensible defaults that match the UI
4. **Test Both Systems**: Always verify that QA answers match UI dashboard values

## Files Changed

- `backend/app/dsl/executor.py` - Fixed level filter bug and added default active filter
- `backend/app/routers/kpis.py` - Fixed level filter bug
- `docs/metricx_BUILD_LOG.md` - Documented the fix
- `backend/docs/QA_SYSTEM_ARCHITECTURE.md` - Updated architecture docs

## Prevention

To prevent similar bugs in the future:
1. Always check database schema before writing filters
2. Test QA answers against UI values for the same questions
3. Document default filtering behavior clearly
4. Add automated tests that compare QA vs UI results

---

*This bug fix ensures users get consistent, trustworthy answers from both the Copilot QA system and the UI dashboard.*
