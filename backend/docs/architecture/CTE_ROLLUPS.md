# Hierarchy rollups in metricx (plain-English guide)

This guide explains how metricx "rolls up" detailed ad data (ads and ad sets) into campaign-level insights using safe database helpers called CTEs. It also shows where this happens in the code and what to expect in answers and logs.

## What is a rollup?
- Your ad data is recorded at detailed levels (often the ad level).
- When you ask "How is the Holiday Sale campaign doing?", you expect totals at the campaign level (spend, revenue, ROAS, etc.).
- A rollup sums up the detailed rows (ads/adsets) under a campaign so you get fresh, accurate campaign totals.

## Why we do this
- Freshness: Campaign-level facts can be stale; children (adsets/ads) are fresher. We compute from children for accuracy.
- Consistency: One unified service performs calculations everywhere, so QA answers match dashboards.
- Safety: The AI only outputs a safe JSON (DSL). The backend validates and executes; queries are workspace-scoped.

## Where rollups happen in metricx

### 1) Resolving a named campaign/adset to its children
When a question references an entity by name (e.g., "Holiday Sale - Purchases"), we first resolve it to all of its descendant leaf entities (ads/adsets). This is done in the unified metrics service:

```530:579:backend/app/services/unified_metric_service.py
logger.info(f"[UNIFIED_METRICS] Resolving entity name: '{entity_name}'")

# Find the entity by name
entity = (
    self.db.query(self.E)
    .filter(self.E.workspace_id == workspace_id)
    .filter(self.E.name.ilike(f"%{entity_name}%"))
    .first()
)

if not entity:
    logger.warning(f"[UNIFIED_METRICS] Entity not found: '{entity_name}'")
    return None

logger.info(f"[UNIFIED_METRICS] Found entity: {entity.name} (ID: {entity.id}, Level: {entity.level})")

# If it's an ad (leaf level), return just the entity itself
if entity.level == "ad":
    logger.info(f"[UNIFIED_METRICS] Entity is ad level, returning itself only")
    return [str(entity.id)]

# Use hierarchy CTE to find all descendants
if entity.level == "campaign":
    mapping_cte = campaign_ancestor_cte(self.db)
    logger.info(f"[UNIFIED_METRICS] Using campaign hierarchy CTE")
elif entity.level == "adset":
    mapping_cte = adset_ancestor_cte(self.db)
    logger.info(f"[UNIFIED_METRICS] Using adset hierarchy CTE")
else:
    logger.warning(f"[UNIFIED_METRICS] Unknown entity level: {entity.level}")
    return [str(entity.id)]

# Find all leaf entities that roll up to this ancestor
descendants = (
    self.db.query(mapping_cte.c.leaf_id)
    .filter(mapping_cte.c.ancestor_id == entity.id)
    .all()
)

descendant_ids = [str(row.leaf_id) for row in descendants]
logger.info(f"[UNIFIED_METRICS] Found {len(descendant_ids)} descendants for {entity.name}")

# Exclude the parent entity itself from descendants
if str(entity.id) in descendant_ids:
    descendant_ids.remove(str(entity.id))
    logger.info(f"[UNIFIED_METRICS] Excluded parent entity {entity.id} from descendants")

logger.info(f"[UNIFIED_METRICS] Returning {len(descendant_ids)} descendant IDs for rollup")
return descendant_ids
```

In short: we find the campaign/adset by name, use a CTE to map leaves (ads) back to their ancestor, and collect all child IDs to include in the rollup for totals and comparisons.

### 2) The CTE helpers
These helpers build a lightweight, safe "map" from each leaf entity back to its ancestor.

- Map any entity (leaf) to its campaign ancestor:

```34:45:backend/app/dsl/hierarchy.py
def campaign_ancestor_cte(session):
    """
    Build a WITH RECURSIVE CTE that maps every entity (leaf) to its campaign ancestor (if exists).
    Returns: leaf_id, ancestor_id, ancestor_name
    """
```

- Map any entity (leaf) to its adset ancestor:

```131:141:backend/app/dsl/hierarchy.py
def adset_ancestor_cte(session):
    """
    Similar to campaign_ancestor_cte, but maps entities to their adset ancestor.
    Returns: leaf_id, ancestor_id, ancestor_name
    """
```

### 3) When a breakdown asks for the same level as the named entity
Sometimes users say "Break down the Holiday Sale campaign by campaign." That is not meaningful (you cannot break one campaign into more campaigns). We automatically switch to the next level down (adsets) so you see the parts that make up the campaign.

Here is the routing logic (campaign -> adset):

```704:729:backend/app/services/unified_metric_service.py
if named_entity.level == "campaign" and child_level == "adset":
    from app.dsl.hierarchy import adset_ancestor_cte
    adset_cte = adset_ancestor_cte(self.db)
    adset_alias = aliased(self.E)
    query = (
        self.db.query(
            adset_alias.name.label("group_name"),
            func.coalesce(func.sum(self.MF.spend), 0).label("spend"),
            func.coalesce(func.sum(self.MF.revenue), 0).label("revenue"),
            func.coalesce(func.sum(self.MF.clicks), 0).label("clicks"),
            func.coalesce(func.sum(self.MF.impressions), 0).label("impressions"),
            func.coalesce(func.sum(self.MF.conversions), 0).label("conversions"),
        )
        .select_from(self.MF)
        .join(self.E, self.E.id == self.MF.entity_id)
        .join(adset_cte, adset_cte.c.leaf_id == self.E.id)
        .join(adset_alias, adset_alias.id == adset_cte.c.ancestor_id)
        .filter(self.E.workspace_id == workspace_id)
        .filter(cast(self.MF.event_date, Date).between(start_date, end_date))
        .group_by(adset_alias.name)
    )
```

This unlocks meaningful single-entity breakdowns: a campaign's child adsets, or an adset's child ads.

## What you will see in answers and logs
- Answers: Asking for a "breakdown of <campaign> by campaign" will show its child adsets (the actual parts). You will see correct totals (ROAS, spend, revenue) and top items.
- Logs: We mark hierarchy steps clearly for verification.

Example log lines:
```text
[UNIFIED_METRICS] Using campaign hierarchy CTE
[UNIFIED_METRICS] Found 13 descendants for Holiday Sale - Purchases
[UNIFIED_METRICS] Excluded parent entity 1b70af... from descendants
[UNIFIED_METRICS] Routing named-entity same-level breakdown to child level: campaign->adset
```

See also: `backend/docs/HOW_TO_VIEW_LOGS.md` for how to tail and filter logs locally or in production.

## FAQ (non-technical)
- Does this change my stored data? No. We compute rollups at query-time using existing data.
- Is this safe for multi-tenant environments? Yes. All queries are workspace-scoped in the database.
- What about "this week vs last week"? We now support time-vs-time comparisons using the same safe service.

## Appendix: When we do not use rollups
- Provider breakdowns (Google vs Meta) group by platform, not the entity tree.
- Entities lists (e.g., "List my active campaigns") are listed directly (and shown as a numbered list when small).

---
If you have questions or want to validate behavior for your workspace, open the logs and look for `[UNIFIED_METRICS]` entries — they tell the story.
