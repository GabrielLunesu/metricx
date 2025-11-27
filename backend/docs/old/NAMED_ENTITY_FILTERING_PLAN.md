# Named Entity Filtering - Implementation Plan

**Created**: 2025-10-08  
**Updated**: 2025-10-08  
**Priority**: HIGH (Week 3-4)  
**Effort**: MEDIUM (2-3 days)  
**Status**: ✅ DAY 1 COMPLETE - Core Implementation Done!

---

## 🎉 Implementation Progress

### ✅ Completed (Day 1 - Oct 8, 2025)

**Core Implementation**:
- ✅ Added `entity_name` field to `Filters` model in `schema.py`
- ✅ Updated executor with `.ilike()` name filtering logic in 4 places:
  - Entities queries
  - Metrics base query  
  - Previous period query
  - Timeseries query
  - Breakdown queries
- ✅ Added 4 few-shot examples to `prompts.py`
- ✅ Updated system prompt with entity_name guidance
- ✅ Updated canonicalization patterns to preserve entity names
- ✅ Created 9 unit tests (all passing!)

**Test Results**: 9/9 unit tests passed ✅
- ✅ Exact match: "Holiday Sale - Purchases"
- ✅ Partial match: "Sale" → finds both Sale campaigns
- ✅ Case-insensitive: "HOLIDAY" = "holiday"
- ✅ Metrics query with name filter
- ✅ Breakdown with name filter
- ✅ No match handling
- ✅ Combined with status filter
- ✅ Lowercase matching
- ✅ Single word matching

**Files Modified**:
1. `/backend/app/dsl/schema.py` - Added entity_name field
2. `/backend/app/dsl/executor.py` - Added .ilike() filtering (4 locations)
3. `/backend/app/nlp/prompts.py` - Added 4 examples + system prompt rules
4. `/backend/app/dsl/canonicalize.py` - Improved entity name preservation
5. `/backend/app/tests/test_named_entity_filtering.py` - NEW: 9 comprehensive tests

---

### 🔄 In Progress

- Running full QA test suite to verify Test 18 passes

---

### 📋 Pending

- Update answer builder for entity-specific language (optional enhancement)
- Document in QA_SYSTEM_ARCHITECTURE.md
- Update metricx_BUILD_LOG.md

---

### 🔮 Future Enhancements (Multi-Entity Comparison)

**User Requirement**: "Compare the CPC of last 7 days from X campaign to Y campaign"

This requires:
1. **Multiple entity_name filters** - Currently supports single name, need to support multiple
2. **Comparison mode** - Compare entity A vs entity B for the same metric
3. **Answer formatting** - Side-by-side comparison in natural language

**Implementation Approach** (Week 4+):
- Add `entity_names: List[str]` field (plural) for multi-entity queries
- Update executor to handle multiple name patterns
- Add comparison-specific answer formatting
- Few-shot examples for "compare X to Y" patterns

**Effort**: 1-2 days

---

## Problem Statement

Users cannot query specific campaigns/adsets/ads by name. Questions like:
- "Give me a breakdown of Holiday Sale campaign performance"
- "How is the Summer Sale campaign performing?"
- "Show me metrics for Lead Gen campaigns"

Currently fail or return wrong results because:
1. DSL only supports filtering by `entity_ids` (UUIDs), not by name
2. LLM cannot translate entity names to UUIDs
3. System either errors out or returns all campaigns instead

---

## Current State Analysis

### What Works
✅ Filter by entity level: `filters: {"level": "campaign"}`  
✅ Filter by status: `filters: {"status": "active"}`  
✅ Filter by provider: `filters: {"provider": "google"}`  
✅ Filter by entity_ids (UUIDs): `filters: {"entity_ids": ["uuid1", "uuid2"]}`

### What Doesn't Work
❌ Filter by entity name: `filters: {"entity_name": "Holiday Sale"}`  
❌ Partial name matching: "holiday" matching "Holiday Sale - Purchases"  
❌ Case-insensitive name matching  
❌ Multiple entity name patterns

### Example Failures

**Test 18**: "give me a breakdown of holiday campaign performance"
- **Current behavior**: Returns ERROR (empty DSL) or lists all campaigns
- **Expected**: Revenue/ROAS breakdown for "Holiday Sale - Purchases" campaign
- **Root cause**: No way to filter by entity name in DSL

---

## Solution Architecture

### Phase 1: Add entity_name Filter to DSL (Day 1 - 4 hours)

#### 1.1 Update DSL Schema
**File**: `backend/app/dsl/schema.py`

```python
class Filters(BaseModel):
    provider: Optional[ProviderEnum] = None
    level: Optional[LevelEnum] = None
    entity_ids: Optional[List[str]] = None
    status: Optional[Literal["active", "paused"]] = None
    
    # NEW: Named entity filtering
    entity_name: Optional[str] = Field(
        default=None,
        description="Filter by entity name (case-insensitive partial match). Example: 'holiday' matches 'Holiday Sale - Purchases'"
    )
```

**Why**: Enables name-based filtering in validated DSL structure

---

#### 1.2 Update Executor to Support Name Filtering
**File**: `backend/app/dsl/executor.py`

Add name filtering logic in both metrics and entities query execution:

```python
def _apply_filters(query, filters: Filters, workspace_id: str):
    """Apply all filters to a SQLAlchemy query."""
    
    # Existing filters...
    if filters.provider:
        query = query.filter(Entity.provider == filters.provider)
    if filters.level:
        query = query.filter(Entity.level == filters.level)
    if filters.status:
        query = query.filter(Entity.status == filters.status)
    if filters.entity_ids:
        query = query.filter(Entity.id.in_(filters.entity_ids))
    
    # NEW: Name filtering (case-insensitive, partial match)
    if filters.entity_name:
        # Use ILIKE for case-insensitive partial matching
        # "holiday" will match "Holiday Sale - Purchases"
        pattern = f"%{filters.entity_name}%"
        query = query.filter(Entity.name.ilike(pattern))
    
    return query
```

**Benefits**:
- Case-insensitive: "HOLIDAY" = "holiday" = "Holiday"
- Partial match: "Sale" matches "Holiday Sale - Purchases"
- SQL-safe: Uses SQLAlchemy's `.ilike()` (no injection risk)
- Works with all query types (metrics, entities, providers)

---

### Phase 2: Update NLP Translation (Day 1-2 - 3 hours)

#### 2.1 Add Few-Shot Examples
**File**: `backend/app/nlp/prompts.py`

Add to `FEW_SHOT_EXAMPLES`:

```python
# Named entity filtering examples
{
    "question": "Give me a breakdown of Holiday Sale campaign performance",
    "dsl": {
        "query_type": "metrics",
        "metric": "revenue",  # Default metric for "performance"
        "time_range": {"last_n_days": 7},
        "breakdown": "campaign",
        "filters": {"entity_name": "Holiday Sale"},  # NEW
        "top_n": 1
    }
},
{
    "question": "How is the Summer Sale campaign performing?",
    "dsl": {
        "query_type": "metrics",
        "metric": "roas",  # ROAS as performance indicator
        "time_range": {"last_n_days": 7},
        "breakdown": null,
        "filters": {
            "level": "campaign",
            "entity_name": "Summer Sale"  # NEW
        }
    }
},
{
    "question": "Show me all lead gen campaigns",
    "dsl": {
        "query_type": "entities",
        "filters": {
            "level": "campaign",
            "entity_name": "lead gen"  # Partial match
        },
        "top_n": 10
    }
},
{
    "question": "What's the CPA for Morning Audience adsets?",
    "dsl": {
        "query_type": "metrics",
        "metric": "cpa",
        "time_range": {"last_n_days": 7},
        "filters": {
            "level": "adset",
            "entity_name": "Morning Audience"  # NEW
        }
    }
}
```

---

#### 2.2 Update System Prompt
**File**: `backend/app/nlp/prompts.py` - `build_system_prompt()`

Add to FILTERS section:

```
FILTERS (optional, only if mentioned):
- provider: "google" | "meta" | "tiktok" | "other"
- level: "account" | "campaign" | "adset" | "ad"
- status: "active" | "paused"
- entity_ids: ["uuid1", "uuid2", ...]
- entity_name: string (NEW - filter by entity name, case-insensitive partial match)

ENTITY NAME FILTERING (NEW):
- Use when user mentions specific campaign/adset/ad names
- Extract the key identifying words (ignore "campaign", "adset", "ad" keywords)
- Examples:
  - "Holiday Sale campaign" → entity_name: "Holiday Sale"
  - "lead gen campaigns" → entity_name: "lead gen"
  - "Morning Audience adsets" → entity_name: "Morning Audience"
- Matching is case-insensitive and partial
- Don't include level keywords in entity_name (they go in level filter)
```

---

#### 2.3 Update Canonicalization
**File**: `backend/app/dsl/canonicalize.py`

Add pattern to preserve entity names:

```python
# Performance breakdown with entity names - keep entity name intact
(r'breakdown of (.+?) campaign performance', r'revenue breakdown for \1 campaign'),
(r'how is (.+?) campaign performing', r'show me revenue for \1 campaign'),
(r'(.+?) campaign performance', r'show me metrics for \1 campaign'),
```

**Why**: Ensures entity names are preserved and passed to LLM correctly

---

### Phase 3: Update Answer Generation (Day 2 - 2 hours)

#### 3.1 Handle Single Entity Results
**File**: `backend/app/answer/answer_builder.py`

When `entity_name` filter is used and returns single result, adjust language:

```python
def _extract_metrics_facts(self, dsl, result, window):
    facts = {
        "metric": dsl.metric,
        "value_raw": summary,
        "value_formatted": formatted_summary,
    }
    
    # NEW: Add entity context when filtering by name
    if dsl.filters and dsl.filters.entity_name:
        facts["entity_filter"] = dsl.filters.entity_name
        facts["is_single_entity_query"] = True
    
    return facts
```

Update prompts to use entity-specific language:
- "The Holiday Sale campaign generated $X revenue last week"
- "Your Summer Sale campaign has a ROAS of 4.5×"

---

### Phase 4: Testing & Validation (Day 3 - 2 hours)

#### 4.1 Unit Tests
**File**: `backend/app/tests/test_named_entity_filtering.py`

```python
def test_entity_name_exact_match():
    """Test exact entity name matching"""
    dsl = MetricQuery(
        metric="revenue",
        time_range={"last_n_days": 7},
        filters={"entity_name": "Holiday Sale - Purchases"}
    )
    result = execute(db, workspace_id, dsl)
    # Assert only Holiday Sale campaign included
    
def test_entity_name_partial_match():
    """Test partial name matching"""
    dsl = MetricQuery(
        metric="revenue",
        time_range={"last_n_days": 7},
        filters={"entity_name": "Sale"}  # Matches Holiday Sale, Summer Sale
    )
    result = execute(db, workspace_id, dsl)
    # Assert both Sale campaigns included
    
def test_entity_name_case_insensitive():
    """Test case-insensitive matching"""
    dsl = MetricQuery(
        metric="revenue",
        time_range={"last_n_days": 7},
        filters={"entity_name": "HOLIDAY SALE"}  # uppercase
    )
    result = execute(db, workspace_id, dsl)
    # Assert Holiday Sale campaign found
```

#### 4.2 Integration Tests

Test these queries in Swagger:
- ✅ "Give me a breakdown of Holiday Sale campaign performance"
- ✅ "How is the Summer Sale campaign performing?"
- ✅ "Show me all lead gen campaigns"
- ✅ "What's the CPA for Morning Audience adsets?"
- ✅ "Compare Google vs Meta for App Install campaigns"

---

## Impact Analysis

### Tests Fixed
- **Test 18**: "give me a breakdown of holiday campaign performance" ✅

### New Capabilities Enabled
1. ✅ Query specific campaigns by name
2. ✅ Filter metrics by entity name pattern
3. ✅ List entities matching name pattern
4. ✅ Combine name filters with other filters (status, provider, level)

### User Experience Improvements
- **Natural queries**: "How is Holiday Sale doing?" instead of needing UUIDs
- **Flexible matching**: "holiday", "Holiday Sale", "HOLIDAY" all work
- **Multi-match support**: "Sale campaigns" matches all campaigns with "Sale" in name

---

## Risks & Mitigations

### Risk 1: Ambiguous Names
**Problem**: "Sale" matches multiple campaigns  
**Mitigation**: System returns all matches with breakdown. User can refine query.

### Risk 2: No Matches
**Problem**: User misspells name  
**Mitigation**: Return helpful error: "No campaigns found matching 'Holyday'. Did you mean 'Holiday'?" (Future: fuzzy matching)

### Risk 3: Performance
**Problem**: ILIKE can be slow on large datasets  
**Mitigation**: Add index on Entity.name column if needed. Current scale (100s of entities) is fine.

---

## Future Enhancements (Out of Scope for Week 3)

### Fuzzy Matching
- "Holyday" → "Holiday" (typo tolerance)
- Uses: `pg_trgm` extension or Levenshtein distance
- **Effort**: 1 day

### Multi-Entity Patterns
- "Show me Holiday Sale and Summer Sale campaigns"
- Requires parsing multiple entity names
- **Effort**: 1 day

### Entity Name Autocomplete/Suggestions
- "No match for 'Holyday'. Similar campaigns: Holiday Sale, ..."
- **Effort**: 2 days

---

## Implementation Checklist

### Day 1 (4 hours)
- [ ] Add `entity_name` field to `Filters` model in `schema.py`
- [ ] Update `_apply_filters()` in `executor.py` with `.ilike()` logic
- [ ] Test executor changes with manual DSL
- [ ] Add 4 few-shot examples to `prompts.py`
- [ ] Update system prompt with entity_name guidance

### Day 2 (3 hours)
- [ ] Update canonicalization patterns
- [ ] Test LLM translation with new examples
- [ ] Update answer builder to handle entity-filtered queries
- [ ] Test end-to-end with Swagger UI

### Day 3 (2 hours)
- [ ] Write unit tests for name filtering
- [ ] Run full test suite (40 questions)
- [ ] Verify Test 18 now passes
- [ ] Document in QA_SYSTEM_ARCHITECTURE.md
- [ ] Update metricx_BUILD_LOG.md

---

## Success Criteria

✅ Test 18 passes: "give me a breakdown of holiday campaign performance"  
✅ Case-insensitive matching works  
✅ Partial matching works ("Sale" → "Holiday Sale")  
✅ No regressions on existing tests  
✅ Clean separation: DSL handles filtering, executor applies it  
✅ Documentation updated

---

**Total Effort**: 9 hours (2-3 days)  
**Expected Impact**: Fixes 1 test + enables natural entity-specific queries  
**Risk Level**: LOW (additive change, no breaking changes)

