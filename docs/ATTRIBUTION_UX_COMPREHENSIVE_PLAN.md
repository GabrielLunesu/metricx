# Attribution UX - Comprehensive Plan

## The Vision

Transform Metricx from "just another dashboard" into **the source of truth for e-commerce attribution**. Users should feel confident that they know EXACTLY which ads are driving sales.

---

## Current State Analysis

### What's Working ✅
- Shopify OAuth → Pixel auto-installed
- Pixel captures: visitor_id, UTMs, gclid, fbclid, events
- Journey tracking with touchpoints
- checkout_token links pixel → orders
- Attribution records stored with provider/confidence
- Meta CAPI + Google Offline Conversions ready

### What's Missing ❌
1. **No visibility** - Users can't see if pixel is working
2. **No setup guidance** - Users don't know they need UTMs
3. **No pixel management** - Can't edit/reinstall pixel
4. **No attribution UI** - Data exists but invisible
5. **No data quality indicators** - Users can't trust the data
6. **No comparison view** - Can't see our data vs platform data

---

## The WOW Experience

### First-Time User Flow

```
1. User connects Shopify
   ↓
2. "Your Pixel is Active!" celebration screen
   - Shows pixel ID
   - Real-time event counter (0 → 1 → 2 as events come in)
   - "Waiting for first visitor..."
   ↓
3. Guided UTM Setup (modal/wizard)
   - "To track which ads drive sales, you need UTM parameters"
   - Platform-specific guides (Meta, Google, TikTok)
   - Copy-paste templates
   ↓
4. Dashboard shows Attribution Card
   - Real-time: "3 orders attributed today"
   - Breakdown by channel
   ↓
5. Analytics shows detailed attribution
   - Revenue by channel with confidence indicators
   - Top campaigns by attributed revenue
   - "Untracked" section showing what's missing
```

---

## Feature Specifications

### 1. Pixel Status & Health (Settings Page)

**Location**: Settings → Connections → Shopify card

**Components**:
```
┌─────────────────────────────────────────────────┐
│ 🟢 Pixel Status: Active                         │
│ ─────────────────────────────────────────────── │
│ Pixel ID: px_abc123...                          │
│ Installed: Nov 30, 2025                         │
│                                                 │
│ Last 24 Hours:                                  │
│ ├─ Page Views: 1,247                            │
│ ├─ Add to Cart: 89                              │
│ ├─ Checkouts Started: 34                        │
│ └─ Checkouts Completed: 12                      │
│                                                 │
│ Health: ████████░░ 82% events captured          │
│                                                 │
│ [Test Pixel] [Reinstall Pixel] [View Events]    │
└─────────────────────────────────────────────────┘
```

**API Endpoint**: `GET /workspaces/{id}/pixel/health`
```json
{
  "status": "active",
  "pixel_id": "px_abc123",
  "installed_at": "2025-11-30T10:00:00Z",
  "last_event_at": "2025-12-01T14:32:00Z",
  "events_24h": {
    "page_viewed": 1247,
    "product_viewed": 523,
    "product_added_to_cart": 89,
    "checkout_started": 34,
    "checkout_completed": 12
  },
  "health_score": 82,
  "issues": []
}
```

**Reinstall Flow**:
- Button triggers `DELETE` old pixel + `POST` new pixel
- Shows progress: "Removing old pixel..." → "Installing new pixel..." → "Done!"

---

### 2. UTM Setup Guide (New Page or Modal)

**Location**: Settings → Attribution Setup (new tab) OR First-time modal after Shopify connect

**Structure**:
```
┌─────────────────────────────────────────────────┐
│ 📊 Attribution Setup                            │
│                                                 │
│ To track which ads drive sales, add UTM         │
│ parameters to your ad URLs.                     │
│                                                 │
│ ┌─────────────────────────────────────────────┐ │
│ │ [Meta Ads] [Google Ads] [TikTok] [Manual]   │ │
│ └─────────────────────────────────────────────┘ │
│                                                 │
│ META ADS SETUP                                  │
│ ─────────────────────────────────────────────── │
│ 1. Go to Ads Manager → Campaign → Ad           │
│ 2. In "Website URL", add these parameters:      │
│                                                 │
│ ┌─────────────────────────────────────────────┐ │
│ │ ?utm_source=facebook                        │ │
│ │ &utm_medium=paid                            │ │
│ │ &utm_campaign={{campaign.name}}             │ │
│ │ &utm_content={{adset.name}}                 │ │
│ │ &utm_term={{ad.name}}                       │ │
│ │                                    [Copy]   │ │
│ └─────────────────────────────────────────────┘ │
│                                                 │
│ 💡 Pro tip: Meta automatically adds fbclid,    │
│    but UTMs give you campaign-level detail.    │
│                                                 │
│ [I've set up my UTMs ✓]                         │
└─────────────────────────────────────────────────┘
```

**Platform-Specific Templates**:

**Meta**:
```
?utm_source=facebook&utm_medium=paid&utm_campaign={{campaign.name}}&utm_content={{adset.name}}&utm_term={{ad.name}}
```

**Google**:
```
{lpurl}?utm_source=google&utm_medium=cpc&utm_campaign={campaign}&utm_content={adgroup}&utm_term={keyword}
```
Or use auto-tagging (gclid) which we resolve automatically.

**TikTok**:
```
?utm_source=tiktok&utm_medium=paid&utm_campaign=__CAMPAIGN_NAME__&utm_content=__AID_NAME__
```

---

### 3. Campaign Attribution Warnings

**Location**: Campaigns page → Each campaign row

**Visual**:
```
┌─────────────────────────────────────────────────────────────┐
│ Campaign                  │ Spend  │ Revenue │ ROAS │ ⚠️   │
├───────────────────────────┼────────┼─────────┼──────┼──────┤
│ Summer Sale 2025          │ $5,000 │ $15,000 │ 3.0x │ ✅   │
│ Brand Awareness           │ $2,000 │ $1,200  │ 0.6x │ ⚠️   │
│ └─ "No UTM tracking"      │        │         │      │      │
│ Retargeting - Cart        │ $1,500 │ $8,000  │ 5.3x │ ✅   │
│ New Product Launch        │ $3,000 │ $0      │ 0.0x │ ❌   │
│ └─ "0 attributed orders"  │        │         │      │      │
└─────────────────────────────────────────────────────────────┘
```

**Warning Types**:
1. ⚠️ **No UTM tracking** - Campaign has spend but no attributed orders with matching UTMs
2. ❌ **No attribution** - Campaign has 0 attributed orders
3. 🔄 **Low confidence** - Attributed via referrer only (not UTM/click ID)

**Tooltip on warning**:
> "This campaign has $2,000 in spend but we couldn't attribute any orders to it.
> Make sure your ad URLs include UTM parameters. [Setup Guide →]"

---

### 4. Attribution Dashboard Section

**Location**: Dashboard page (new card)

**Design**:
```
┌─────────────────────────────────────────────────┐
│ 📊 Revenue Attribution                          │
│ ─────────────────────────────────────────────── │
│                                                 │
│   [PIE CHART]         Meta Ads      $25,000 55%│
│      55%              Google Ads    $12,000 27%│
│    /    \             Direct        $5,000  11%│
│   27%   11%           Organic       $3,000   7%│
│       7%                                        │
│                                                 │
│ Attributed: $45,000 / $52,000 total (87%)      │
│ ████████████████░░░ 87% of revenue tracked     │
│                                                 │
│ [View Full Report →]                            │
└─────────────────────────────────────────────────┘
```

**Key Insight**: Show % of revenue that's attributed. If low, prompt UTM setup.

---

### 5. Analytics Attribution Section

**Location**: Analytics page → New "Attribution" tab or section

**Components**:

**A. Channel Performance Table**
```
┌─────────────────────────────────────────────────────────────────┐
│ Channel      │ Attributed  │ Orders │ Avg Order │ Confidence   │
│              │ Revenue     │        │ Value     │              │
├──────────────┼─────────────┼────────┼───────────┼──────────────┤
│ 🔵 Meta      │ $25,000     │ 82     │ $305      │ ████░ High   │
│ 🔴 Google    │ $12,000     │ 45     │ $267      │ █████ High   │
│ ⚪ Direct    │ $5,000      │ 20     │ $250      │ ███░░ Medium │
│ 🟢 Organic   │ $3,000      │ 12     │ $250      │ ██░░░ Low    │
│ ❓ Unknown   │ $7,000      │ 28     │ $250      │ -            │
└─────────────────────────────────────────────────────────────────┘
```

**B. Top Attributed Campaigns**
```
┌─────────────────────────────────────────────────────────────────┐
│ # │ Campaign               │ Channel │ Revenue  │ Match Type   │
├───┼────────────────────────┼─────────┼──────────┼──────────────┤
│ 1 │ Summer Sale 2025       │ Meta    │ $12,500  │ utm_campaign │
│ 2 │ Brand Search           │ Google  │ $8,200   │ gclid        │
│ 3 │ Retargeting - Cart     │ Meta    │ $6,800   │ fbclid       │
│ 4 │ Lookalike - Purchasers │ Meta    │ $4,200   │ utm_campaign │
│ 5 │ Product Listing Ads    │ Google  │ $3,800   │ gclid        │
└─────────────────────────────────────────────────────────────────┘
```

**C. Attribution Quality**
```
┌─────────────────────────────────────────────────┐
│ Attribution Quality Score: 78%                  │
│ ███████░░░                                      │
│                                                 │
│ ✅ High confidence: 67% of orders               │
│    (gclid, utm_campaign matches)                │
│                                                 │
│ ⚠️ Medium confidence: 18% of orders             │
│    (fbclid, utm_source matches)                 │
│                                                 │
│ ❌ Low confidence: 8% of orders                 │
│    (referrer only)                              │
│                                                 │
│ ❓ Unattributed: 7% of orders                   │
│    [Improve Attribution →]                      │
└─────────────────────────────────────────────────┘
```

---

### 6. Platform Data vs Our Data Comparison

**Location**: Analytics page → Toggle view

**Concept**: Show side-by-side: what Meta/Google reports vs what we attribute

```
┌─────────────────────────────────────────────────────────────────┐
│ Data Comparison                    [Platform] [Metricx] [Both] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ META ADS                                                        │
│ ┌─────────────────────┬─────────────────────┐                  │
│ │ Meta Reports        │ Metricx Attributes  │                  │
│ ├─────────────────────┼─────────────────────┤                  │
│ │ Conversions: 95     │ Attributed: 82      │                  │
│ │ Revenue: $28,500    │ Revenue: $25,000    │                  │
│ │ ROAS: 5.7x          │ ROAS: 5.0x          │                  │
│ └─────────────────────┴─────────────────────┘                  │
│                                                                 │
│ 💡 Why different? Meta counts view-through conversions.        │
│    Metricx only counts click-through with UTM/fbclid.          │
│                                                                 │
│ GOOGLE ADS                                                      │
│ ┌─────────────────────┬─────────────────────┐                  │
│ │ Google Reports      │ Metricx Attributes  │                  │
│ ├─────────────────────┼─────────────────────┤                  │
│ │ Conversions: 48     │ Attributed: 45      │                  │
│ │ Revenue: $12,800    │ Revenue: $12,000    │                  │
│ │ ROAS: 4.3x          │ ROAS: 4.0x          │                  │
│ └─────────────────────┴─────────────────────┘                  │
│                                                                 │
│ ✅ Close match! Google gclid tracking is highly accurate.       │
└─────────────────────────────────────────────────────────────────┘
```

---

### 7. Real-Time Attribution Feed (WOW Factor)

**Location**: Dashboard or dedicated "Live" view

**Concept**: Show attributions as they happen

```
┌─────────────────────────────────────────────────┐
│ 🔴 LIVE Attribution Feed                        │
├─────────────────────────────────────────────────┤
│                                                 │
│ Just now                                        │
│ 💰 $127.00 attributed to "Summer Sale" (Meta)  │
│    Match: utm_campaign • Confidence: High       │
│                                                 │
│ 2 minutes ago                                   │
│ 💰 $89.00 attributed to "Brand Search" (Google)│
│    Match: gclid • Confidence: High              │
│                                                 │
│ 5 minutes ago                                   │
│ 💰 $234.00 attributed to Direct Traffic         │
│    Match: none • Confidence: Low                │
│                                                 │
│ 8 minutes ago                                   │
│ 💰 $156.00 attributed to "Retargeting" (Meta)  │
│    Match: fbclid • Confidence: Medium           │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## Revenue Source Clarification

**Where does revenue come from?**

```
SHOPIFY                           METRICX
─────────                         ───────
orders/paid webhook      →        ShopifyOrder table
 ├─ total_price                    ├─ total_price
 ├─ currency                       ├─ currency
 ├─ checkout_token        ────────→├─ links to CustomerJourney
 └─ line_items                     └─ line_items

CustomerJourney           →        Attribution
 ├─ touchpoints (UTMs)             ├─ attributed_revenue
 └─ checkout_token         ────────→└─ links via journey
```

**Revenue displayed**:
- **Platform view**: Revenue from Entity sync (Meta/Google API)
- **Attribution view**: Revenue from Shopify orders, attributed to channels
- **Comparison**: Shows both side-by-side

---

## API Endpoints Needed

| Endpoint | Purpose |
|----------|---------|
| `GET /workspaces/{id}/pixel/health` | Pixel status, event counts, health score |
| `POST /workspaces/{id}/pixel/reinstall` | Delete + recreate pixel |
| `GET /workspaces/{id}/attribution/summary` | Revenue by channel |
| `GET /workspaces/{id}/attribution/campaigns` | Top campaigns by attributed revenue |
| `GET /workspaces/{id}/attribution/quality` | Confidence breakdown |
| `GET /workspaces/{id}/attribution/comparison` | Platform vs Metricx data |
| `GET /workspaces/{id}/attribution/feed` | Recent attributions (for live feed) |
| `GET /campaigns?include_attribution_status=true` | Add warning flags to campaigns |

---

## Implementation Phases

### Phase 1: Foundation (Backend)
1. ✅ Attribution data collection (done)
2. Create pixel health endpoint
3. Create attribution summary endpoint
4. Create attribution campaigns endpoint
5. Add attribution warnings to campaigns endpoint

### Phase 2: Settings UX
1. Pixel health card in Settings
2. UTM Setup Guide (new component)
3. Pixel reinstall flow

### Phase 3: Dashboard Integration
1. Attribution pie chart card
2. Attribution coverage indicator

### Phase 4: Analytics Deep Dive
1. Channel performance table
2. Top attributed campaigns
3. Attribution quality score
4. Platform comparison view

### Phase 5: WOW Features
1. Real-time attribution feed
2. Campaign warnings with tooltips
3. First-time user celebration/onboarding

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Attribution rate | >80% of orders attributed |
| High confidence | >60% of attributions are "high" |
| UTM adoption | >90% of ad campaigns have UTMs |
| User trust | Users reference Metricx data in decisions |

---

## Decisions Made ✅

1. **Attribution model selection**: ✅ Let users choose (first-click, last-click, linear)

2. **Attribution window**: ✅ Configurable (7, 14, 28, 30 days)

3. **Live feed**: ✅ PRIORITY - build it

4. **Platform comparison**: ✅ PRIORITY - build it

5. **Implementation order**:
   - Phase 1: Pixel Health (Settings)
   - Phase 2: Attribution Card (Dashboard)
   - Phase 3: Full Attribution Analytics
   - Phase 4: Live Feed + Platform Comparison
