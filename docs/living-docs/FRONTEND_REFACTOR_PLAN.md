# Frontend Refactor Plan: Ad Analytics First

**Created**: 2025-12-02
**Status**: Planning
**Goal**: Clean, unblocked experience for users without Shopify while preserving attribution as a premium enhancement

---

## The Vision (Summarized)

- **Primary**: Ad analytics works day 1 (Google/Meta data)
- **Secondary**: Attribution unlocks with Shopify connection
- **Future**: Customizable dashboards, rule engines, visual journey trees (WebGL/Three.js)

---

## Phase 1: Go-Live Essentials (Do First)

### 1.1 Create Workspace Status Endpoint

**Backend**: `backend/app/routers/workspaces.py`

```python
@router.get("/{workspace_id}/status")
def get_workspace_status(workspace_id: UUID, ...):
    """
    Returns connection status for conditional UI rendering.
    """
    connections = db.query(Connection).filter_by(workspace_id=workspace_id).all()

    return {
        "has_shopify": any(c.provider == "shopify" and c.status == "active" for c in connections),
        "has_ad_platform": any(c.provider in ["meta", "google", "tiktok"] and c.status == "active" for c in connections),
        "connected_platforms": [c.provider for c in connections if c.status == "active"],
        "attribution_ready": check_attribution_ready(workspace_id),  # pixel + recent events
    }
```

**Frontend**: `ui/lib/api.js`

```javascript
export async function fetchWorkspaceStatus({ workspaceId }) {
  const res = await fetch(`${BASE}/workspaces/${workspaceId}/status`, {
    method: "GET",
    credentials: "include",
  });
  if (!res.ok) throw new Error("Failed to fetch workspace status");
  return res.json();
}
```

**Why**: Single source of truth for UI conditionals. Cached at layout level.

---

### 1.2 Refactor Dashboard Page

**File**: `ui/app/(dashboard)/dashboard/page.jsx`

**Current** (lines 73-77):
```jsx
{/* Attribution Section - ALWAYS SHOWS */}
<div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mt-8">
  <AttributionCard workspaceId={user.workspace_id} timeframe={timeframe} />
  <LiveAttributionFeed workspaceId={user.workspace_id} />
</div>
```

**After**:
```jsx
{/* Attribution Section - Only if Shopify connected */}
{status?.has_shopify && (
  <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mt-8">
    <AttributionCard workspaceId={user.workspace_id} timeframe={timeframe} />
    <LiveAttributionFeed workspaceId={user.workspace_id} />
  </div>
)}
```

**Add status fetch**:
```jsx
const [status, setStatus] = useState(null);

useEffect(() => {
  if (user?.workspace_id) {
    fetchWorkspaceStatus({ workspaceId: user.workspace_id })
      .then(setStatus)
      .catch(console.error);
  }
}, [user?.workspace_id]);
```

---

### 1.3 Move Attribution Under Analytics

**Current Navigation**:
```
/dashboard
/dashboard/attribution  ← Standalone page
/analytics
```

**New Navigation**:
```
/dashboard
/analytics
/analytics/attribution  ← Subpage of Analytics
```

**Changes Required**:

1. **Move file**: `ui/app/(dashboard)/dashboard/attribution/page.jsx` → `ui/app/(dashboard)/analytics/attribution/page.jsx`

2. **Update Sidebar** (`ui/app/(dashboard)/components/shared/Sidebar.jsx`):

**Remove** (line 82):
```jsx
{ href: "/dashboard/attribution", label: "Attribution", icon: Target, active: pathname === "/dashboard/attribution" },
```

3. **Add Attribution Unlock Widget to Analytics Page** (`ui/app/(dashboard)/analytics/page.jsx`):

```jsx
{/* Attribution Unlock Widget */}
{status?.has_shopify ? (
  <Link href="/analytics/attribution" className="glass-panel p-4 rounded-2xl hover:ring-2 ring-cyan-200 transition-all cursor-pointer group">
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-xl bg-gradient-to-br from-emerald-500 to-cyan-500">
          <Target className="w-5 h-5 text-white" />
        </div>
        <div>
          <h3 className="font-medium text-neutral-900">Attribution Analytics</h3>
          <p className="text-sm text-neutral-500">See which channels drive your revenue</p>
        </div>
      </div>
      <ChevronRight className="w-5 h-5 text-neutral-400 group-hover:text-cyan-500 transition-colors" />
    </div>
  </Link>
) : (
  <div className="glass-panel p-4 rounded-2xl opacity-60">
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-xl bg-neutral-200">
          <Target className="w-5 h-5 text-neutral-400" />
        </div>
        <div>
          <h3 className="font-medium text-neutral-500">Attribution Analytics</h3>
          <p className="text-sm text-neutral-400">Connect Shopify to unlock</p>
        </div>
      </div>
      <Lock className="w-5 h-5 text-neutral-300" />
    </div>
  </Link>
)}
```

---

### 1.4 Refactor Campaign Warnings to Inline Icons

**File**: `ui/app/(dashboard)/campaigns/page.jsx`

**Remove** (line 187):
```jsx
<CampaignWarningsPanel workspaceId={workspaceId} />
```

**File**: `ui/app/(dashboard)/campaigns/components/CampaignRow.jsx`

**Add warning icon with hover tooltip**:
```jsx
{row.hasWarning && (
  <div className="relative group">
    <AlertTriangle className="w-4 h-4 text-amber-500" />
    {/* Hover tooltip */}
    <div className="absolute left-full ml-2 top-1/2 -translate-y-1/2 hidden group-hover:block z-50">
      <div className="bg-neutral-900 text-white text-xs px-3 py-2 rounded-lg whitespace-nowrap shadow-lg">
        {row.warningMessage || "Attribution issue detected"}
      </div>
    </div>
  </div>
)}
```

**Note**: Backend needs to include warning info in entity-performance response, or fetch separately.

---

### 1.5 Dynamic KPI Source Indicators

**File**: `ui/app/(dashboard)/dashboard/components/KPICard.jsx`

**Current**: Shows generic "source" text
**After**: Show actual platform icons

```jsx
function PlatformIndicator({ platforms, source }) {
  if (source === 'shopify') {
    return (
      <div className="flex items-center gap-1 text-xs text-emerald-600">
        <span className="text-sm">🛍️</span>
        <span>Verified</span>
      </div>
    );
  }

  // Show connected ad platforms
  return (
    <div className="flex items-center gap-1">
      {platforms?.includes('meta') && <span className="text-sm">📘</span>}
      {platforms?.includes('google') && <span className="text-sm">🔍</span>}
      {platforms?.includes('tiktok') && <span className="text-sm">🎵</span>}
    </div>
  );
}
```

---

## Phase 2: Clean Up Repo (Do Second)

### 2.1 Identify Unused Files

Run analysis to find:
- Components not imported anywhere
- API functions never called
- Dead routes
- Unused CSS/styles

```bash
# Find potentially unused components
grep -r "import.*from" ui/app --include="*.jsx" | \
  sed 's/.*from ["\x27]\(.*\)["\x27].*/\1/' | \
  sort | uniq -c | sort -n
```

### 2.2 Files to Review for Removal

Based on initial analysis:
- `ui/app/(dashboard)/canvas/` - Feature flagged, check if needed
- Old mock data files
- Duplicate utility functions
- Unused hooks

---

## Phase 3: Customizable Dashboard (Future)

### 3.1 User Dashboard Preferences

**Schema Addition**:
```sql
CREATE TABLE user_dashboard_config (
  user_id UUID REFERENCES users(id),
  workspace_id UUID REFERENCES workspaces(id),
  config JSONB DEFAULT '{
    "kpi_widgets": ["revenue", "roas", "spend", "conversions"],
    "layout": "default",
    "visible_sections": ["kpis", "chart", "insights", "creatives"]
  }'
);
```

### 3.2 Widget System

```jsx
// Future: Drag-and-drop dashboard widgets
const AVAILABLE_WIDGETS = {
  revenue: { label: "Revenue", component: RevenueWidget },
  roas: { label: "ROAS", component: RoasWidget },
  spend: { label: "Ad Spend", component: SpendWidget },
  conversions: { label: "Conversions", component: ConversionsWidget },
  leads: { label: "Leads", component: LeadsWidget },
  cpl: { label: "Cost per Lead", component: CplWidget },
  // ... more
};
```

---

## Phase 4: Visual Journey Tree (Future Vision)

### 4.1 UTM Flow Visualization

- WebGL/Three.js powered
- Shows user journey from ad click → conversion
- Interactive nodes at each stage
- Real-time data overlay

### 4.2 Session Behavior (SaaS Users)

- Track page visits, time on site
- Funnel visualization
- Works without Shopify (valuable for SaaS)

---

## Priority Order (What to Build Now)

| Priority | Task | Impact | Effort |
|----------|------|--------|--------|
| P0 | Workspace status endpoint | Unblocks all UI conditionals | Small |
| P0 | Hide attribution on dashboard (no Shopify) | Cleaner first impression | Small |
| P1 | Move attribution under analytics | Better IA | Medium |
| P1 | Inline campaign warning icons | Less noise | Medium |
| P2 | Dynamic platform indicators | Polish | Small |
| P2 | Repo cleanup | Maintainability | Medium |
| P3 | Customizable dashboard | User value | Large |
| P4 | Visual journey tree | Differentiation | Large |

---

## Files to Modify (Phase 1)

### Backend
- `backend/app/routers/workspaces.py` - Add status endpoint

### Frontend
- `ui/lib/api.js` - Add fetchWorkspaceStatus
- `ui/app/(dashboard)/dashboard/page.jsx` - Conditional attribution
- `ui/app/(dashboard)/components/shared/Sidebar.jsx` - Remove attribution nav
- `ui/app/(dashboard)/analytics/page.jsx` - Add attribution unlock widget
- `ui/app/(dashboard)/analytics/attribution/page.jsx` - Move from dashboard
- `ui/app/(dashboard)/campaigns/page.jsx` - Remove warning panel
- `ui/app/(dashboard)/campaigns/components/CampaignRow.jsx` - Add warning icon
- `ui/app/(dashboard)/dashboard/components/KPICard.jsx` - Dynamic indicators

---

## Success Criteria

1. New user with only Meta/Google connected sees:
   - Full dashboard with ad metrics
   - No attribution widgets
   - No "connect Shopify" empty states
   - Clean campaigns page

2. User with Shopify connected sees:
   - Everything above PLUS
   - Attribution section on dashboard
   - Attribution page accessible via Analytics
   - Warning icons on campaigns with issues

3. Repo is cleaner with unused files removed
