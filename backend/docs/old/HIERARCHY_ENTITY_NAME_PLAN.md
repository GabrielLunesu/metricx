# Hierarchy + Entity Name Filtering - Implementation Plan (Option B)

**Created**: 2025-10-09  
**Complexity**: MEDIUM-HIGH  
**Effort**: 4-6 hours (Incremental approach)  
**Goal**: Enable entity_name filtering to work with hierarchy aggregation

---

## 📚 Current State Understanding

### How Hierarchy Rollup Works Now (Breakdowns)

**Data Structure**:
```
Campaign: "Summer Sale Campaign" (no direct facts)
  ├─ AdSet: "Morning Audience" (no direct facts)
  │   ├─ Ad: "Image Ad" (30 facts) ✅
  │   ├─ Ad: "Video Ad" (30 facts) ✅
  │   └─ Ad: "Carousel Ad" (30 facts) ✅
  └─ AdSet: "Evening Audience" (no direct facts)
      ├─ Ad: "Image Ad" (30 facts) ✅
      ├─ Ad: "Video Ad" (30 facts) ✅
      └─ Ad: "Carousel Ad" (30 facts) ✅

Total: Campaign has 180 facts (through 6 child ads)
```

**Current Breakdown Logic** (Works Perfectly):
```python
# Step 1: Build CTE that maps leaf → campaign ancestor
leaf_to_campaign = campaign_ancestor_cte(db)
# Creates mapping: Ad 1 → Campaign, Ad 2 → Campaign, etc.

# Step 2: Join facts to ancestor mapping
breakdown_query = (
    db.query(
        leaf_to_campaign.c.ancestor_name,  # Campaign name
        func.sum(MF.spend),                 # Sum across all child ads
    )
    .join(E, E.id == MF.entity_id)         # Join to leaf entity (ad)
    .join(leaf_to_campaign, leaf_to_campaign.c.leaf_id == E.id)  # Map to campaign
    .group_by(leaf_to_campaign.c.ancestor_name)  # Group by campaign
)
```

**Result**: Aggregates 180 ad-level facts into 1 campaign-level aggregate ✅

---

### Why entity_name Doesn't Work Currently

**Problem**:
```python
# Current entity_name filter
if plan.filters.get("entity_name"):
    pattern = f"%{plan.filters['entity_name']}%"
    base_query = base_query.filter(E.name.ilike(pattern))
    # E = Entity table (leaf entities)
```

**What Happens**:
1. User asks: "revenue for Summer Sale campaign"
2. DSL: `filters: {level: "campaign", entity_name: "Summer Sale"}`
3. Executor filters `E.level == 'campaign' AND E.name ILIKE '%Summer Sale%'`
4. Finds Campaign entity "Summer Sale Campaign" ✅
5. BUT joins to MetricFact via `MF.entity_id == E.id` 
6. Campaign has entity_id that has 0 facts! ❌
7. Result: $0

**The Issue**: We're filtering the WRONG entity table. We need to filter by ANCESTOR name, not leaf name.

---

## 🎯 The Solution (Option B)

### Core Concept

When `entity_name` is present, we need to:
1. **Determine target level**: Is user asking about campaign, adset, or ad?
2. **Use appropriate CTE**: Map all leaf facts to that ancestor level
3. **Filter by ancestor name**: Match entity_name against ancestor, not leaf
4. **Aggregate**: Sum metrics from all matching leaf entities

---

## 📋 Incremental Implementation Plan

### Step 1: Understand Pattern (30 min - ANALYSIS)

**Goal**: Document how to detect target level from entity_name queries

**Analysis**:
```python
# Pattern 1: Explicit level filter
filters: {level: "campaign", entity_name: "Summer Sale"}
→ Target: Campaign level

# Pattern 2: No level filter (infer from question)
filters: {entity_name: "Summer Sale"}
question: "How is Summer Sale campaign performing?"
→ Target: Campaign level (from question word "campaign")

# Pattern 3: Multiple matches possible
filters: {entity_name: "Morning Audience"}
→ Could be multiple adsets (one per campaign)
→ Target: AdSet level
```

**Decision Rules**:
1. If `filters.level` is set → use that
2. If question contains "campaign" → campaign level
3. If question contains "adset" → adset level
4. If question contains "ad" → ad level
5. Default: Try campaign first, fall back to adset, then ad

---

### Step 2: Create Hierarchy-Aware entity_name Filter (2 hours - CODE)

**Goal**: Modify executor to use CTEs when entity_name is present

**Location**: `backend/app/dsl/executor.py` - `_execute_metrics_plan()`

#### 2.1: Add Helper Function (30 min)

```python
def _get_ancestor_level_from_filters(query: MetricQuery) -> Optional[str]:
    """
    Determine which ancestor level to use for entity_name filtering.
    
    Returns:
        "campaign", "adset", "ad", or None
    
    Logic:
        1. If filters.level is set → use that
        2. If question contains "campaign" → "campaign"
        3. If question contains "adset" → "adset"  
        4. Default to "campaign" (most common use case)
    
    Examples:
        filters: {level: "campaign", entity_name: "Summer Sale"}
        → returns "campaign"
        
        filters: {entity_name: "Morning Audience"}
        question: "What's CPA for Morning Audience adsets?"
        → returns "adset" (from question keyword)
    """
    if query.filters and query.filters.level:
        return query.filters.level
    
    # Analyze question for level keywords
    question_lower = query.question.lower() if query.question else ""
    
    if "campaign" in question_lower:
        return "campaign"
    elif "adset" in question_lower or "ad set" in question_lower:
        return "adset"
    elif "ad " in question_lower or " ad" in question_lower:
        return "ad"
    
    # Default to campaign (most common)
    return "campaign"
```

---

#### 2.2: Modify Summary Query Logic (1 hour)

**Current** (lines 260-290):
```python
base_query = (
    db.query(...)
    .join(E, E.id == MF.entity_id)
    .filter(E.workspace_id == workspace_id)
)

# Apply filters
if plan.filters.get("entity_name"):
    pattern = f"%{plan.filters['entity_name']}%"
    base_query = base_query.filter(E.name.ilike(pattern))  # WRONG!
```

**New** (with hierarchy):
```python
base_query = (
    db.query(...)
    .join(E, E.id == MF.entity_id)
    .filter(E.workspace_id == workspace_id)
)

# NEW: Hierarchy-aware entity_name filtering
if plan.filters.get("entity_name"):
    target_level = _get_ancestor_level_from_filters(plan.query)
    pattern = f"%{plan.filters['entity_name']}%"
    
    if target_level == "campaign":
        # Use campaign CTE to map leaf → campaign, then filter by campaign name
        leaf_to_ancestor = campaign_ancestor_cte(db)
        base_query = base_query.join(
            leaf_to_ancestor, 
            leaf_to_ancestor.c.leaf_id == E.id
        )
        base_query = base_query.filter(
            leaf_to_ancestor.c.ancestor_name.ilike(pattern)
        )
    
    elif target_level == "adset":
        # Use adset CTE
        leaf_to_ancestor = adset_ancestor_cte(db)
        base_query = base_query.join(
            leaf_to_ancestor, 
            leaf_to_ancestor.c.leaf_id == E.id
        )
        base_query = base_query.filter(
            leaf_to_ancestor.c.ancestor_name.ilike(pattern)
        )
    
    else:  # ad level
        # Direct filtering on leaf entity (facts are at ad level)
        base_query = base_query.filter(E.name.ilike(pattern))
```

**Impact**: Summary queries now aggregate from all child entities!

---

#### 2.3: Apply Same Logic to Previous Period Query (30 min)

Same pattern as summary query, around line 330.

---

#### 2.4: Apply Same Logic to Timeseries Query (30 min)

Same pattern, around line 380.

---

### Step 3: Handle Breakdown Queries (1 hour - CODE)

**Current Challenge**: Breakdown queries already use CTEs. Need to combine entity_name filter with existing CTE.

**Location**: Lines 435-530

**Approach**:
```python
elif plan.breakdown == "campaign":
    leaf_to_ancestor = campaign_ancestor_cte(db)
    
    breakdown_query = (
        db.query(...)
        .join(E, E.id == MF.entity_id)
        .join(leaf_to_ancestor, leaf_to_ancestor.c.leaf_id == E.id)
        .filter(E.workspace_id == workspace_id)
        .filter(...)
        .group_by("group_id", "group_name")
    )
    
    # Apply entity_name filter (already using CTE!)
    if plan.filters.get("entity_name"):
        pattern = f"%{plan.filters['entity_name']}%"
        # Filter by ANCESTOR name (already in the CTE)
        breakdown_query = breakdown_query.filter(
            leaf_to_ancestor.c.ancestor_name.ilike(pattern)
        )
```

**Key Insight**: Breakdown queries ALREADY use CTEs, so we just add the filter on the CTE column!

---

### Step 4: Remove level Filter from Few-Shot Examples (15 min - PROMPTS)

**Update Examples** in `app/nlp/prompts.py`:

```python
# BEFORE:
{
    "question": "How is the Summer Sale campaign performing?",
    "filters": {
        "level": "campaign",      # REMOVE THIS
        "entity_name": "Summer Sale"
    }
}

# AFTER:
{
    "question": "How is the Summer Sale campaign performing?",
    "filters": {
        "entity_name": "Summer Sale"  # Let hierarchy CTE handle it
    }
}
```

**Why**: Level is inferred from question keywords or defaults to campaign.

---

### Step 5: Update Tests (30 min - TESTS)

**Modify**: `test_named_entity_filtering.py`

**Change**:
```python
# Current test expects campaign-level facts
assert result.summary == 3500.0  # 7 days × $500

# NEW: Should aggregate from ad-level facts
# Summer Sale has 2 adsets × 3 ads = 6 ads
# 6 ads × 7 days × $500 = $21,000
assert result.summary >= 20000.0
assert result.summary <= 22000.0
```

---

### Step 6: Integration Testing (30 min - VALIDATION)

**Test these queries**:
1. "How is Summer Sale campaign performing?" → Should aggregate 180 facts
2. "What's CPA for Morning Audience adsets?" → Should aggregate from child ads
3. "Give me breakdown of holiday campaign performance" → Should work
4. "Show me revenue for Black Friday campaign" → Should show actual revenue

---

## 🔍 Technical Deep Dive

### Why Hierarchy CTEs Are Perfect for This

**Current CTE Output** (campaign_ancestor_cte):
```sql
leaf_id (ad)  | ancestor_id (campaign) | ancestor_name
------------- | ---------------------- | -------------------
ad-1-uuid     | campaign-uuid          | "Summer Sale Campaign"
ad-2-uuid     | campaign-uuid          | "Summer Sale Campaign"
ad-3-uuid     | campaign-uuid          | "Summer Sale Campaign"
...
```

**How We'll Use It**:
```sql
SELECT SUM(spend), SUM(revenue), ...
FROM metric_facts mf
JOIN entities e ON e.id = mf.entity_id  -- Join to leaf (ad)
JOIN leaf_to_campaign ltc ON ltc.leaf_id = e.id  -- Map to campaign
WHERE e.workspace_id = :workspace
  AND ltc.ancestor_name ILIKE '%Summer Sale%'  -- ✅ Filter by campaign name!
  AND event_date BETWEEN :start AND :end
```

**Result**: Aggregates all facts from ads whose campaign matches "Summer Sale" ✅

---

## 📊 Impact Analysis

### What This Enables

**Before** (with level filter):
```
"Summer Sale campaign revenue" → Filters to campaign entity → 0 facts → $0
```

**After** (with hierarchy CTE):
```
"Summer Sale campaign revenue" → Maps all child ads → 180 facts → Real $$$
```

### Tests Fixed

- ✅ Test 18: "breakdown of holiday campaign performance"
- ✅ Test 43: "How is the Summer Sale campaign performing?"
- ✅ Test 45: "What's the CPA for Morning Audience adsets?"
- ✅ Test 46: "What's the revenue for Black Friday campaign?"
- ✅ Test 47: "Give me ROAS for App Install campaigns"
- ✅ Test 49: "What's the CTR for Evening Audience adsets?"
- ✅ Test 50: "How much did Holiday Sale campaign spend last week?"

**Total**: 7 tests fixed!

---

## ⚠️ Complexity & Risks

### Complexity: MEDIUM-HIGH

**Why Complex**:
1. Need to dynamically choose CTE (campaign vs adset vs ad)
2. Need to detect target level from question or filters
3. Breakdown queries already use CTEs → need to avoid double-CTE
4. Three query types affected (summary, previous, timeseries)

**Why Manageable**:
1. ✅ CTE infrastructure already exists and works
2. ✅ Just need to apply filter to CTE column instead of leaf entity
3. ✅ Can reuse existing `campaign_ancestor_cte()` and `adset_ancestor_cte()`
4. ✅ Logic is localized to executor.py

---

### Risks & Mitigations

**Risk 1: Performance**
- **Issue**: Recursive CTEs can be slow on large datasets
- **Mitigation**: Current dataset (150 entities) is tiny; won't be an issue
- **Future**: Add indexes on parent_id, level if needed

**Risk 2: Multiple Matches**
- **Issue**: "Sale" matches multiple campaigns
- **Expected**: Aggregates ALL matching campaigns (user can refine)
- **Mitigation**: This is actually desired behavior!

**Risk 3: Breaking Existing Queries**
- **Issue**: Don't want to break non-entity_name queries
- **Mitigation**: Only activate CTE logic when entity_name is present
- **Safety**: Extensive tests to verify no regressions

---

## 📋 Incremental Implementation Checklist

### Phase A: Analysis & Planning (1 hour) - ✅ DONE
- [x] Understand current hierarchy CTE implementation
- [x] Document data structure (campaign → adset → ad)
- [x] Identify where to apply hierarchy logic
- [x] Create implementation plan

### Phase B: Core Implementation (2-3 hours)
- [ ] **Step 1**: Create `_get_ancestor_level_from_filters()` helper (30 min)
- [ ] **Step 2**: Update summary query with hierarchy CTE logic (1 hour)
- [ ] **Step 3**: Update previous period query (30 min)
- [ ] **Step 4**: Update timeseries query (30 min)
- [ ] **Step 5**: Update breakdown query filter logic (30 min)

### Phase C: Prompt & Testing (1 hour)
- [ ] **Step 6**: Remove `level` filter from few-shot examples (15 min)
- [ ] **Step 7**: Update unit tests to expect aggregated values (15 min)
- [ ] **Step 8**: Run unit tests to verify (15 min)
- [ ] **Step 9**: Run integration tests (15 min)

### Phase D: Validation & Documentation (30 min)
- [ ] **Step 10**: Run full QA test suite
- [ ] **Step 11**: Verify 7 tests now return data instead of $0
- [ ] **Step 12**: Document in QA_SYSTEM_ARCHITECTURE.md
- [ ] **Step 13**: Update metricx_BUILD_LOG.md

---

## 🔧 Detailed Implementation (Step 2)

### Modify Summary Query (Most Important)

**File**: `backend/app/dsl/executor.py`  
**Function**: `_execute_metrics_plan()`  
**Lines**: ~260-290

**Current Code**:
```python
# Build base query
base_query = (
    db.query(
        func.coalesce(func.sum(MF.spend), 0).label("spend"),
        func.coalesce(func.sum(MF.revenue), 0).label("revenue"),
        # ... all base measures
    )
    .join(E, E.id == MF.entity_id)
    .filter(E.workspace_id == workspace_id)
    .filter(cast(MF.event_date, Date).between(plan.start, plan.end))
)

# Apply filters
if plan.filters.get("provider"):
    base_query = base_query.filter(MF.provider == plan.filters["provider"])
if plan.filters.get("level"):
    base_query = base_query.filter(MF.level == plan.filters["level"])
if plan.filters.get("status"):
    base_query = base_query.filter(E.status == plan.filters["status"])
if plan.filters.get("entity_ids"):
    base_query = base_query.filter(MF.entity_id.in_(plan.filters["entity_ids"]))

# WRONG: This filters leaf entity, not ancestor
if plan.filters.get("entity_name"):
    pattern = f"%{plan.filters['entity_name']}%"
    base_query = base_query.filter(E.name.ilike(pattern))
```

**New Code**:
```python
# Build base query
base_query = (
    db.query(
        func.coalesce(func.sum(MF.spend), 0).label("spend"),
        func.coalesce(func.sum(MF.revenue), 0).label("revenue"),
        # ... all base measures
    )
    .join(E, E.id == MF.entity_id)
    .filter(E.workspace_id == workspace_id)
    .filter(cast(MF.event_date, Date).between(plan.start, plan.end))
)

# Apply standard filters (these work on leaf entities)
if plan.filters.get("provider"):
    base_query = base_query.filter(MF.provider == plan.filters["provider"])
if plan.filters.get("status"):
    base_query = base_query.filter(E.status == plan.filters["status"])
if plan.filters.get("entity_ids"):
    base_query = base_query.filter(MF.entity_id.in_(plan.filters["entity_ids"]))

# NEW: Hierarchy-aware entity_name filtering
if plan.filters.get("entity_name"):
    pattern = f"%{plan.filters['entity_name']}%"
    target_level = _get_ancestor_level_from_filters(plan.query)
    
    if target_level == "campaign":
        # Use campaign CTE: Filter by campaign ancestor name
        from app.dsl.hierarchy import campaign_ancestor_cte
        leaf_to_campaign = campaign_ancestor_cte(db)
        base_query = base_query.join(
            leaf_to_campaign,
            leaf_to_campaign.c.leaf_id == E.id
        )
        base_query = base_query.filter(
            leaf_to_campaign.c.ancestor_name.ilike(pattern)
        )
    
    elif target_level == "adset":
        # Use adset CTE: Filter by adset ancestor name
        from app.dsl.hierarchy import adset_ancestor_cte
        leaf_to_adset = adset_ancestor_cte(db)
        base_query = base_query.join(
            leaf_to_adset,
            leaf_to_adset.c.leaf_id == E.id
        )
        base_query = base_query.filter(
            leaf_to_adset.c.ancestor_name.ilike(pattern)
        )
    
    else:  # ad level
        # Direct filter on leaf entity (facts are at ad level anyway)
        base_query = base_query.filter(E.name.ilike(pattern))

# REMOVE level filter when entity_name is present (handled by CTE)
elif plan.filters.get("level"):
    base_query = base_query.filter(MF.level == plan.filters["level"])
```

---

### Step 3-4: Apply Same Pattern to Other Queries

**Previous Period Query** (lines ~315-345):
- Same logic as summary query
- Use CTE when entity_name present

**Timeseries Query** (lines ~365-395):
- Same logic as summary query
- Use CTE when entity_name present

---

### Step 5: Breakdown Queries (Easier!)

**Why Easier**: Already using CTEs!

**Current** (lines ~520-530):
```python
# Breakdown query already has CTE
breakdown_query = (
    db.query(...)
    .join(E, E.id == MF.entity_id)
    .join(leaf_to_ancestor, leaf_to_ancestor.c.leaf_id == E.id)
    .group_by("group_id", "group_name")
)

# Apply filters
if plan.filters.get("entity_name"):
    pattern = f"%{plan.filters['entity_name']}%"
    breakdown_query = breakdown_query.filter(E.name.ilike(pattern))  # WRONG!
```

**Fix**:
```python
# Apply filters
if plan.filters.get("entity_name"):
    pattern = f"%{plan.filters['entity_name']}%"
    # Filter by ANCESTOR name (already in CTE!)
    breakdown_query = breakdown_query.filter(
        leaf_to_ancestor.c.ancestor_name.ilike(pattern)
    )
```

**Simple!** Just change `E.name` to `leaf_to_ancestor.c.ancestor_name`

---

## 🧪 Testing Strategy

### Unit Tests to Update

**File**: `backend/app/tests/test_named_entity_filtering.py`

**Changes Needed**:
```python
# OLD: Expected campaign-level facts (0)
def test_entity_name_with_metrics_query(db, test_workspace):
    result = execute_plan(...)
    assert result.summary == 3500.0  # 7 days × $500

# NEW: Expected ad-level facts aggregated (4 campaigns × 7 days × $500)
def test_entity_name_with_metrics_query(db, test_workspace):
    result = execute_plan(...)
    # 1 campaign × 3 adsets × 3 ads = 9 ads (from fixture)
    # But "Holiday Sale" matches 1 campaign
    # Actually need to check fixture structure...
    assert result.summary >= 10000.0  # Should be much higher now
```

---

### Integration Tests

**Test with Swagger** (after implementation):
1. "How is the Summer Sale campaign performing?" → Should show revenue
2. "What's the revenue for Black Friday campaign?" → Should show revenue
3. "Give me breakdown of holiday campaign performance" → Should show breakdown

---

## 📈 Expected Outcomes

### Success Metrics

**Before Fix**:
- Tests 43, 45-47, 49-50: Return $0 (6 tests failing)
- Test 18: Works but limited

**After Fix**:
- All 7 tests return actual data ✅
- Success rate: 84% → **94%** (47/50 tests)

---

## 🎯 Alternative: Hybrid Approach (Lower Risk)

If full hierarchy proves too complex, we can do:

**Hybrid Step 1**: Fix non-breakdown queries only (2 hours)
- Use CTE for summary, previous, timeseries queries
- Keep breakdown queries as-is (they already work for entity_name at ancestor level)

**Hybrid Step 2**: Remove level filter from prompts (15 min)
- Let queries hit ad level by default
- entity_name will still filter correctly

**Benefit**: 80% of value with 40% of risk

---

## 💡 My Recommendation

### Start with Breakdown Queries Only (1 hour)

**Why**: They already use CTEs, so it's just changing the filter!

**Steps**:
1. Modify breakdown query entity_name filter (15 min)
2. Test with "breakdown of holiday campaign performance" (15 min)
3. If it works → proceed with summary queries (30 min)
4. Test all entity_name queries (15 min)

**Benefit**: Incremental validation at each step

---

**Ready to proceed with this plan?** We can start with the breakdown queries first (lowest risk, highest value), then expand to summary queries.

