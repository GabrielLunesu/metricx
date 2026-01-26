# Metricx Attribution Engine

**Version**: 1.10.0
**Last Updated**: 2025-12-02
**Status**: Phase 1-3 Complete - Full Attribution Page + Settings Clarity + CAPI Testing

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Components](#components)
4. [Database Schema](#database-schema)
5. [Health Monitoring](#health-monitoring)
6. [Implementation Progress](#implementation-progress)
7. [Testing](#testing)
8. [Known Limitations & Future Work](#known-limitations--future-work)

---

## Overview

The Attribution Engine is the core system that connects marketing spend to revenue. It tracks customer journeys from first ad click through purchase, enabling accurate ROI calculation for ad campaigns.

### Why This Matters

Without attribution, merchants can see:
- How much they spent on ads
- How much revenue they made

But they **cannot** see:
- Which campaigns drove which sales
- True ROAS per campaign/ad
- Customer acquisition cost by channel

The Attribution Engine bridges this gap.

### Core Capabilities

| Capability | Description | Status |
|------------|-------------|--------|
| **Journey Tracking** | Track visitors across sessions via Shopify Web Pixel | ✅ Complete |
| **UTM Attribution** | Match UTM parameters to providers (meta, google, etc.) | ✅ Complete |
| **Order Attribution** | Link orders to journeys via checkout_token | ✅ Complete |
| **Click ID Resolution** | Resolve gclid/fbclid to actual ads | ✅ Complete |
| **Multi-Touch Models** | First-click, last-click, linear attribution | 🔲 Week 4 |
| **Server-Side CAPI** | Send conversions back to Meta/Google | ✅ Complete |
| **Attribution Windows** | Configurable 7/14/28/30 day windows | 🔲 Week 4 |

### Key Design Decisions

1. **Shopify Web Pixel Extension** (not custom pixel)
   - Not blocked by ad blockers (first-party Shopify script)
   - Full access to checkout events
   - Built-in privacy compliance (GDPR/CCPA)
   - No Safari ITP cookie limitations
   - Zero merchant setup required

2. **Dual Data Sources** (Pixel + Webhooks)
   - Pixel: Customer journey, UTMs, click IDs, visitor ID
   - Webhooks: Full order details, line items, customer data
   - Merged by checkout_token/order_id

3. **Click ID Resolution** (not just UTM matching)
   - Query Google Ads API with gclid to get actual campaign/ad (highest priority)
   - Use Meta CAPI for fbclid event matching
   - Fall back to UTM matching when click IDs unavailable

4. **Attribution Triggers on orders/paid** (not checkout_completed)
   - Avoids running attribution on abandoned checkouts
   - Webhooks have final order state
   - Pixel checkout_completed just prepares journey data

5. **Event Sourcing Ready**
   - PixelEvents stored as immutable log
   - Journey state can be recomputed if attribution logic changes
   - Never lose raw data

---

## Architecture

### System Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    METRICX ATTRIBUTION ENGINE                                    │
└─────────────────────────────────────────────────────────────────────────────────┘

    SHOPIFY STORE                           METRICX INFRASTRUCTURE
    ─────────────                           ──────────────────────

    ┌─────────────────────────────────────┐
    │         Shopify Storefront          │
    │                                     │
    │  ┌───────────────────────────────┐  │
    │  │   Metricx Web Pixel Extension │  │     ┌─────────────────────────────────────┐
    │  │   (Sandboxed by Shopify)      │  │     │           FastAPI Backend           │
    │  │                               │  │     │                                     │
    │  │  Selective event subscription │  │     │  ┌─────────────────────────────┐   │
    │  │  (only events we need)        │──┼────►│  │  POST /v1/pixel-events      │   │
    │  │                               │  │     │  │                             │   │
    │  │  Events captured:             │  │     │  │  • Validate workspace_id    │   │
    │  │  • page_viewed                │  │     │  │  • Dedupe by event_id       │   │
    │  │  • product_viewed             │  │     │  │  • Store journey events     │   │
    │  │  • product_added_to_cart      │  │     │  │  • Update customer journey  │   │
    │  │  • checkout_started           │  │     │  │  • Track touchpoints        │   │
    │  │  • checkout_completed         │  │     │  └─────────────────────────────┘   │
    │  │    (prepares journey data)    │  │     │                                     │
    │  │                               │  │     │  NOTE: Attribution NOT triggered    │
    │  └───────────────────────────────┘  │     │  on checkout_completed - only on    │
    └─────────────────────────────────────┘     │  orders/paid webhook!               │
                                                │                                     │
    ┌─────────────────────────────────────┐     │                                     │
    │         Shopify Server              │     │  ┌─────────────────────────────┐   │
    │                                     │     │  │  POST /webhooks/shopify     │   │
    │  orders/paid webhook ───────────────┼────►│  │  (ATTRIBUTION TRIGGER)      │   │
    │                                     │     │  │                             │   │
    │  (Contains full order details:      │     │  │  • Verify HMAC              │   │
    │   line items, customer, totals,     │     │  │  • Store order + line items │   │
    │   landing_site with UTMs,           │     │  │  • Link to journey via      │   │
    │   checkout_token)                   │     │  │    checkout_token           │   │
    └─────────────────────────────────────┘     │  │  • Queue attribution job    │   │
                                                │  └─────────────────────────────┘   │
                                                │                                     │
                                                │  ┌─────────────────────────────┐   │
                                                │  │  Attribution Worker (RQ)    │   │
                                                │  │  Idempotent job processing  │   │
                                                │  │  Key: attribution:{order}:{model}
                                                │  │                             │   │
                                                │  │  1. Find journey by         │   │
                                                │  │     checkout_token/email    │   │
                                                │  │  2. Get touchpoints within  │   │
                                                │  │     attribution window      │   │
                                                │  │  3. Resolve click IDs       │   │
                                                │  │     (gclid first!)          │   │
                                                │  │  4. Match UTMs to entities  │   │
                                                │  │  5. Apply attribution model │   │
                                                │  │  6. Store attribution       │   │
                                                │  │  7. Send CAPI conversions   │   │
                                                │  │     (with event_id dedup)   │   │
                                                │  └─────────────────────────────┘   │
                                                │                                     │
                                                └─────────────────────────────────────┘

                                                              │
                    ┌─────────────────────────────────────────┼─────────────────────────────────────────┐
                    │                                         │                                         │
                    ▼                                         ▼                                         ▼
           ┌─────────────────┐                       ┌─────────────────┐                       ┌─────────────────┐
           │   PostgreSQL    │                       │   Meta CAPI     │                       │  Google Ads API │
           │                 │                       │                 │                       │                 │
           │  • journeys     │                       │  • Send         │                       │  • Resolve      │
           │  • touchpoints  │                       │    conversions  │                       │    gclid        │
           │  • attributions │                       │  • event_id     │                       │  • Offline      │
           │  • pixel_events │                       │    deduplication│                       │    conversions  │
           └─────────────────┘                       └─────────────────┘                       └─────────────────┘
```

### Data Flow

```
1. VISITOR ARRIVES (with UTM/click ID)
   │
   ├─► Web Pixel checks consent (analyticsAllowed/marketingAllowed)
   │
   ├─► If allowed: captures visitor_id, UTMs, fbclid/gclid, landing_page
   │
   ├─► Backend dedupes by event_id (client-generated UUID)
   │
   ├─► Backend creates/updates CustomerJourney
   │
   └─► Backend adds JourneyTouchpoint (if has attribution data)

2. VISITOR BROWSES
   │
   ├─► Web Pixel captures: page_viewed, product_viewed, cart events
   │
   └─► Backend stores PixelEvents (immutable log for event sourcing)

3. VISITOR STARTS CHECKOUT
   │
   ├─► Web Pixel fires: checkout_started, checkout_completed
   │
   ├─► Backend links journey to checkout_token
   │
   └─► NO attribution job yet (order not confirmed)

4. ORDER PAID (webhook - THIS triggers attribution)
   │
   ├─► Shopify fires: orders/paid webhook
   │
   ├─► Backend stores ShopifyOrder with checkout_token
   │
   ├─► Backend finds CustomerJourney by checkout_token
   │
   └─► Backend queues attribution job (idempotent key: order_id + model)

5. ATTRIBUTION RUNS
   │
   ├─► Filter touchpoints by attribution window (order_date - touched_at <= window)
   │
   ├─► PRIORITY 1: Resolve gclid via Google Ads API (highest confidence)
   │
   ├─► PRIORITY 2: Match utm_campaign to Entity names
   │
   ├─► PRIORITY 3: Match utm_content to adset/ad names
   │
   ├─► PRIORITY 4: fbclid confirms Meta source (for CAPI matching)
   │
   ├─► PRIORITY 5: utm_source → provider mapping
   │
   ├─► PRIORITY 6: Referrer inference
   │
   ├─► FALLBACK: Classify as direct/organic/unknown
   │   - No referrer + no UTMs → direct
   │   - Referrer = google.com/bing.com → organic search
   │   - Otherwise → unknown
   │
   ├─► Apply attribution model (first_click, last_click, linear)
   │
   ├─► Store Attribution record (INSERT ON CONFLICT DO UPDATE)
   │
   └─► Send conversion to Meta CAPI / Google Offline (with event_id for dedup)
```

### Why Shopify Web Pixel Extension?

| Aspect | Custom Pixel | Shopify Web Pixel Extension |
|--------|--------------|----------------------------|
| **Ad Blockers** | Blocked by 30%+ users | Not blocked (first-party) |
| **Safari ITP** | Cookies limited to 7 days | Shopify handles cookies |
| **Checkout Access** | Sandboxed, can't access | Full checkout events |
| **Event Coverage** | Brittle detection | Official analytics.subscribe |
| **Privacy** | Manual GDPR handling | Built-in consent management |
| **Merchant Setup** | Manual script tag | Automatic with app install |
| **Reliability** | Script might not load | Shopify infrastructure |

---

## Components

### 1. Shopify Web Pixel Extension

**Location**: `extensions/metricx-pixel/`

**Purpose**: Capture customer journey events from Shopify storefront.

**Required OAuth Scopes**: `write_pixels`, `read_customer_events`

**Files**:
```
extensions/metricx-pixel/
├── shopify.extension.toml    # Extension configuration
└── src/
    └── index.js              # Event subscription logic
```

**shopify.extension.toml**:
```toml
type = "web_pixel_extension"
name = "metricx-pixel"
runtime_context = "strict"

[customer_privacy]
analytics = true
marketing = true
preferences = false
sale_of_data = "enabled"

[settings]
type = "object"

[settings.fields.workspaceId]
name = "Workspace ID"
description = "Your Metricx workspace ID"
type = "single_line_text_field"
validations = [
  { name = "min", value = "1" }
]

[settings.fields.apiEndpoint]
name = "API Endpoint"
description = "Metricx API endpoint"
type = "single_line_text_field"
validations = [
  { name = "min", value = "1" }
]
```

**src/index.js**:
```javascript
import { register } from '@shopify/web-pixels-extension';

register(async ({ analytics, browser, settings, init }) => {
  'use strict';

  const { workspaceId, apiEndpoint } = settings;
  const endpoint = apiEndpoint || 'https://api.metricx.ai/v1/pixel-events';

  // ─── RESPECT PRIVACY/CONSENT ───
  // In strict mode, Shopify handles consent. Events only fire if allowed.
  // But we can also check explicitly:
  const analyticsAllowed = init.customerPrivacy?.analyticsProcessingAllowed;
  const marketingAllowed = init.customerPrivacy?.marketingAllowed;

  if (!analyticsAllowed && !marketingAllowed) {
    // User has not consented - don't track
    return;
  }

  // ─── VISITOR ID MANAGEMENT ───
  // NOTE: In strict mode, cookie API is simplified - no options object
  let visitorId = await browser.cookie.get('_mx_id');

  if (!visitorId) {
    visitorId = 'mx_' + Date.now().toString(36) + Math.random().toString(36).substr(2, 8);
    // Strict mode: browser.cookie.set(name, value) - no options
    await browser.cookie.set('_mx_id', visitorId);
  }

  // ─── CAPTURE ATTRIBUTION ───
  const url = new URL(init.context.document.location.href);
  const params = url.searchParams;

  // Keep attribution cookie small (only essential fields)
  const attribution = {
    s: params.get('utm_source'),      // source
    m: params.get('utm_medium'),      // medium
    c: params.get('utm_campaign'),    // campaign
    t: params.get('utm_content'),     // content
    fb: params.get('fbclid'),
    gc: params.get('gclid'),
    tt: params.get('ttclid'),
    lp: url.pathname,                 // landing page
    ts: Date.now()                    // timestamp (compact)
  };

  // Only store if we have attribution data
  const hasNewAttribution = attribution.s || attribution.fb ||
                            attribution.gc || attribution.tt;

  if (hasNewAttribution) {
    await browser.cookie.set('_mx_attr', JSON.stringify(attribution));
  }

  // Get stored attribution
  let storedAttr = null;
  const cookieAttr = await browser.cookie.get('_mx_attr');
  if (cookieAttr) {
    try {
      const parsed = JSON.parse(cookieAttr);
      // Expand back to full names for API
      storedAttr = {
        utm_source: parsed.s,
        utm_medium: parsed.m,
        utm_campaign: parsed.c,
        utm_content: parsed.t,
        fbclid: parsed.fb,
        gclid: parsed.gc,
        ttclid: parsed.tt,
        landing_page: parsed.lp,
        landed_at: new Date(parsed.ts).toISOString()
      };
    } catch (e) {}
  }

  // Use current attribution if new, otherwise stored
  const finalAttr = hasNewAttribution ? {
    utm_source: attribution.s,
    utm_medium: attribution.m,
    utm_campaign: attribution.c,
    utm_content: attribution.t,
    fbclid: attribution.fb,
    gclid: attribution.gc,
    ttclid: attribution.tt,
    landing_page: attribution.lp,
    landed_at: new Date(attribution.ts).toISOString()
  } : storedAttr;

  // ─── GENERATE EVENT ID FOR DEDUPLICATION ───
  const generateEventId = () => {
    return 'evt_' + Date.now().toString(36) + Math.random().toString(36).substr(2, 8);
  };

  // ─── SEND EVENT ───
  const sendEvent = (eventName, eventData) => {
    const eventId = generateEventId();

    fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // Skip ngrok interstitial page for local development
        'ngrok-skip-browser-warning': 'true'
      },
      body: JSON.stringify({
        workspace_id: workspaceId,
        visitor_id: visitorId,
        event_id: eventId,  // For server-side deduplication
        event: eventName,
        data: eventData,
        attribution: finalAttr,
        context: {
          url: init.context.document.location.href,
          referrer: init.context.document.referrer
        },
        ts: new Date().toISOString()
      }),
      keepalive: true
    }).catch(() => {});
  };

  // ─── SUBSCRIBE TO SPECIFIC EVENTS (not all_events) ───
  // Only subscribe to events we actually use
  const eventsToTrack = [
    'page_viewed',
    'product_viewed',
    'product_added_to_cart',
    'checkout_started',
    'checkout_completed'
  ];

  eventsToTrack.forEach(eventName => {
    analytics.subscribe(eventName, (event) => {
      sendEvent(event.name, mapEventData(event.name, event.data));
    });
  });

  function mapEventData(name, data) {
    switch (name) {
      case 'page_viewed':
        return {
          path: data.context?.document?.location?.pathname,
          title: data.context?.document?.title
        };

      case 'product_viewed':
        return {
          product_id: data.productVariant?.product?.id,
          variant_id: data.productVariant?.id,
          title: data.productVariant?.product?.title,
          price: data.productVariant?.price?.amount,
          currency: data.productVariant?.price?.currencyCode
        };

      case 'product_added_to_cart':
        return {
          product_id: data.cartLine?.merchandise?.product?.id,
          variant_id: data.cartLine?.merchandise?.id,
          quantity: data.cartLine?.quantity,
          price: data.cartLine?.merchandise?.price?.amount,
          currency: data.cartLine?.merchandise?.price?.currencyCode
        };

      case 'checkout_started':
        return {
          checkout_token: data.checkout?.token,
          value: data.checkout?.totalPrice?.amount,
          currency: data.checkout?.totalPrice?.currencyCode,
          item_count: data.checkout?.lineItems?.length
        };

      case 'checkout_completed':
        return {
          checkout_token: data.checkout?.token,
          order_id: data.checkout?.order?.id,
          value: data.checkout?.totalPrice?.amount,
          currency: data.checkout?.totalPrice?.currencyCode,
          item_count: data.checkout?.lineItems?.length
        };

      default:
        return {};
    }
  }
});
```

---

### 2. Pixel Events Endpoint

**Location**: `backend/app/routers/pixel_events.py`

**Purpose**: Receive events from Web Pixel, store journey data with deduplication.

**Endpoint**: `POST /v1/pixel-events`

**Request Schema**:
```python
class PixelEventRequest(BaseModel):
    workspace_id: str
    visitor_id: str
    event_id: Optional[str] = None  # Client-generated UUID for deduplication
    event: str  # page_viewed, checkout_completed, etc.
    data: Optional[Dict[str, Any]] = {}
    attribution: Optional[Attribution] = None
    context: Optional[EventContext] = None
    ts: Optional[str] = None
```

**Key Logic**:
```python
@router.post("/pixel-events")
async def receive_pixel_event(payload: PixelEventRequest, ...):
    # 1. Validate workspace exists
    workspace = db.query(Workspace).filter_by(id=payload.workspace_id).first()
    if not workspace:
        raise HTTPException(400, "Invalid workspace")

    # 2. Deduplicate by event_id (idempotency)
    if payload.event_id:
        existing = db.query(PixelEvent).filter_by(
            workspace_id=payload.workspace_id,
            event_id=payload.event_id
        ).first()
        if existing:
            return {"status": "duplicate", "event_id": str(existing.id)}

    # 3. Store PixelEvent (immutable log)
    event = PixelEvent(
        workspace_id=payload.workspace_id,
        visitor_id=payload.visitor_id,
        event_id=payload.event_id,
        event_type=payload.event,
        event_data=payload.data,
        # ... attribution fields ...
    )
    db.add(event)

    # 4. Get or create CustomerJourney
    journey = _get_or_create_journey(db, workspace_id, payload.visitor_id, payload.attribution)

    # 5. Add touchpoint if has attribution data
    if _is_attribution_touchpoint(payload.event, payload.attribution):
        touchpoint = JourneyTouchpoint(...)
        db.add(touchpoint)

    # 6. Link checkout_token to journey (for webhook merge)
    if payload.event == "checkout_completed" and payload.data.get("checkout_token"):
        journey.checkout_token = payload.data["checkout_token"]

    db.commit()

    # NOTE: Do NOT trigger attribution here!
    # Attribution is triggered by orders/paid webhook

    return {"status": "ok", "event_id": str(event.id)}
```

---

### 3. Shopify Webhook Handler

**Location**: `backend/app/routers/shopify_webhooks.py`

**Purpose**: Receive order data from Shopify, merge with pixel journey, **trigger attribution**.

**Endpoint**: `POST /webhooks/shopify/orders`

**Key Logic**:
```python
@router.post("/orders")
async def receive_order(request: Request, background_tasks: BackgroundTasks, ...):
    # 1. Verify HMAC signature
    if not verify_shopify_hmac(body, hmac_header):
        raise HTTPException(401, "Invalid signature")

    # 2. Parse order data
    payload = json.loads(body)
    checkout_token = payload.get("checkout_token")

    # 3. Store ShopifyOrder with checkout_token
    order = ShopifyOrder(
        workspace_id=connection.workspace_id,
        shopify_order_id=payload["id"],
        checkout_token=checkout_token,  # IMPORTANT: For journey linking
        total_price=Decimal(payload["total_price"]),
        currency=payload.get("currency", "USD"),
        # ... other fields ...
    )
    db.merge(order)  # Upsert
    db.commit()

    # 4. Queue attribution job (THIS is where attribution happens)
    # Use idempotent key to prevent duplicate processing
    job_key = f"attribution:{order.id}:last_click"

    background_tasks.add_task(
        queue_attribution_job,
        order_id=str(order.id),
        workspace_id=str(connection.workspace_id),
        job_key=job_key
    )

    return {"status": "ok"}
```

---

### 4. Attribution Service

**Location**: `backend/app/services/attribution_service.py`

**Purpose**: Core attribution logic - match orders to campaigns with proper priority.

**Attribution Priority** (CORRECTED - gclid is highest):
```
1. gclid Resolution → Google Ads API (HIGHEST confidence)
   - Query Google Ads API to get campaign/ad from click ID
   - Returns exact entity that was clicked

2. UTM Campaign → Entity Name (high confidence)
   - Normalize and fuzzy match utm_campaign to campaign.name

3. UTM Content → Adset/Ad Name (high confidence)
   - Match utm_content to adset.name or ad.name

4. fbclid → Meta Provider (medium confidence)
   - Can't resolve to specific ad, but confirms Meta source
   - Used for CAPI event matching

5. utm_source → Provider (low confidence)
   - Map "facebook", "google", etc. to provider

6. Referrer → Provider (low confidence)
   - Infer provider from referring domain

7. No attribution → Classify correctly:
   - No referrer + no UTMs → "direct"
   - Referrer is google.com/bing.com/etc → "organic"
   - Otherwise → "unknown"
```

**Attribution with Window Enforcement**:
```python
def attribute_order(
    self,
    order: ShopifyOrder,
    model: str = "last_click",
    window_days: int = 30  # Configurable per workspace
) -> AttributionResult:
    """
    Attribute an order to a campaign/ad.

    Args:
        order: The Shopify order to attribute
        model: Attribution model (first_click, last_click, linear)
        window_days: Only consider touchpoints within this window

    Returns:
        AttributionResult with entity, confidence, match_type
    """
    # Find journey by checkout_token or customer_email
    journey = self._find_journey(order)

    if not journey:
        return self._classify_unattributed(order)

    # Apply attribution window
    cutoff = order.order_created_at - timedelta(days=window_days)

    valid_touchpoints = [
        tp for tp in journey.touchpoints
        if tp.touched_at >= cutoff
    ]

    if not valid_touchpoints:
        return self._classify_unattributed(order)

    # Select touchpoint based on model
    if model == "last_click":
        touchpoint = valid_touchpoints[-1]
    elif model == "first_click":
        touchpoint = valid_touchpoints[0]
    else:
        # For linear, we'll create multiple attributions
        return self._linear_attribution(valid_touchpoints, order)

    # Run attribution priority chain
    return self._attribute_touchpoint(touchpoint, order.workspace_id)


def _attribute_touchpoint(self, tp: JourneyTouchpoint, workspace_id: UUID) -> AttributionResult:
    """
    Attribute a single touchpoint using priority chain.
    """
    # PRIORITY 1: gclid (highest confidence)
    if tp.gclid:
        entity = self.click_resolution.resolve_gclid(tp.gclid, workspace_id)
        if entity:
            return AttributionResult(
                entity_id=entity.id,
                provider=entity.provider,
                entity_level=entity.level,
                match_type="gclid",
                confidence="high"
            )
        # Even if we can't resolve to entity, we know it's Google
        return AttributionResult(
            entity_id=None,
            provider="google",
            entity_level=None,
            match_type="gclid",
            confidence="medium"
        )

    # PRIORITY 2: utm_campaign → Entity name
    if tp.utm_campaign:
        entity = self._match_utm_campaign(tp.utm_campaign, workspace_id)
        if entity:
            return AttributionResult(
                entity_id=entity.id,
                provider=entity.provider,
                entity_level="campaign",
                match_type="utm_campaign",
                confidence="high"
            )

    # PRIORITY 3: utm_content → Adset/Ad name
    if tp.utm_content:
        entity = self._match_utm_content(tp.utm_content, workspace_id)
        if entity:
            return AttributionResult(
                entity_id=entity.id,
                provider=entity.provider,
                entity_level=entity.level,
                match_type="utm_content",
                confidence="high"
            )

    # PRIORITY 4: fbclid → Meta
    if tp.fbclid:
        return AttributionResult(
            entity_id=None,
            provider="meta",
            entity_level=None,
            match_type="fbclid",
            confidence="medium"
        )

    # PRIORITY 5: utm_source → Provider
    if tp.utm_source:
        provider = self._normalize_provider(tp.utm_source)
        if provider:
            return AttributionResult(
                entity_id=None,
                provider=provider,
                entity_level=None,
                match_type="utm_source",
                confidence="low"
            )

    # PRIORITY 6: Referrer
    if tp.referrer:
        provider = self._infer_from_referrer(tp.referrer)
        if provider:
            return AttributionResult(
                entity_id=None,
                provider=provider,
                entity_level=None,
                match_type="referrer",
                confidence="low"
            )

    # Shouldn't reach here if touchpoint has attribution data
    return AttributionResult(
        entity_id=None,
        provider="unknown",
        entity_level=None,
        match_type="none",
        confidence="none"
    )


def _classify_unattributed(self, order: ShopifyOrder) -> AttributionResult:
    """
    Classify orders with no valid touchpoints.
    Distinguish between direct, organic, and unknown.
    """
    # Check order's landing_site (from webhook)
    landing_site = order.landing_site or ""
    referring_site = order.referring_site or ""

    # Direct: No referrer, no UTMs, no click IDs
    if not referring_site and not order.utm_source and not order.gclid and not order.fbclid:
        return AttributionResult(
            entity_id=None,
            provider="direct",
            entity_level=None,
            match_type="none",
            confidence="none"
        )

    # Organic search: Referrer is a search engine
    search_engines = ["google.com", "bing.com", "yahoo.com", "duckduckgo.com", "baidu.com"]
    if any(se in referring_site.lower() for se in search_engines):
        if not order.gclid:  # Not a paid click
            return AttributionResult(
                entity_id=None,
                provider="organic",
                entity_level=None,
                match_type="referrer",
                confidence="low"
            )

    # Unknown: Has referrer but can't classify
    return AttributionResult(
        entity_id=None,
        provider="unknown",
        entity_level=None,
        match_type="none",
        confidence="none"
    )
```

---

### 5. Conversions API Service

**Location**: `backend/app/services/conversions_api_service.py`

**Purpose**: Send conversions back to ad platforms for optimization.

**Key Features**:
- Only send for final order states (paid/completed)
- Include event_id for deduplication
- Refunds handled separately (out of scope for v1)

**Pixel Assignment Requirement**:

Pixels in Meta are owned at the **Business Manager level**, not the Ad Account level.
For CAPI to work, the pixel must be assigned to the ad account:

1. Go to [Meta Business Settings → Data Sources → Pixels](https://business.facebook.com/settings/data-sources/pixels)
2. Select your pixel
3. Click **Add Assets** → **Ad Accounts**
4. Select the ad account you connected to metricx
5. Click **Add**

If no pixel is assigned, the `/connections/{id}/meta-pixels` endpoint returns empty,
and the UI shows instructions for assignment.

**Meta CAPI**:
```python
async def send_meta_conversion(self, order: ShopifyOrder, attribution: Attribution):
    """
    Send purchase event to Meta Conversions API.

    Only called for paid orders, not abandoned checkouts.
    """
    # Generate event_id for client+server deduplication
    event_id = f"order_{order.shopify_order_id}"

    event = {
        "event_name": "Purchase",
        "event_time": int(order.order_created_at.timestamp()),
        "event_id": event_id,  # IMPORTANT: For deduplication
        "action_source": "website",
        "user_data": {
            "em": hash_sha256(order.customer_email) if order.customer_email else None,
            "fbc": order.fbclid,  # Facebook Click ID
            "fbp": order.pixel_visitor_id,  # Facebook Pixel ID from cookie
            "client_ip_address": order.ip_hash,
            "client_user_agent": order.user_agent,
        },
        "custom_data": {
            "currency": order.currency,
            "value": float(order.total_price),
            "order_id": str(order.shopify_order_id),
        }
    }

    await self.meta_client.send_event(
        pixel_id=connection.pixel_id,
        access_token=connection.access_token,
        events=[event]
    )

    logger.info(
        "[CAPI] Sent Meta conversion",
        order_id=str(order.shopify_order_id),
        event_id=event_id
    )
```

---

### 6. Meta CAPI Test Endpoint

**Location**: `backend/app/routers/attribution.py`

**Purpose**: Allow users to verify CAPI integration without making a real purchase.

**Endpoint**: `POST /workspaces/{workspace_id}/meta-capi/test`

**Request Schema**:
```python
class MetaCAPITestRequest(BaseModel):
    test_event_code: str  # From Meta Events Manager → Test Events tab
    value: float = 99.99  # Test purchase value
    currency: str = "USD"
```

**Response Schema**:
```python
class MetaCAPITestResponse(BaseModel):
    success: bool
    message: str
    pixel_id: Optional[str]
    events_received: Optional[int]
    error: Optional[str]
```

**Usage**:
```bash
# 1. Get test event code from Meta Events Manager → Test Events
# 2. Call the endpoint
curl -X POST "https://api.metricx.ai/workspaces/{id}/meta-capi/test" \
  -H "Content-Type: application/json" \
  -d '{"test_event_code": "TEST12345"}'

# 3. Check Meta Events Manager - event should appear within seconds
```

**Key Logic**:
- Finds Meta connection with configured pixel (prefers connections with `meta_pixel_id` set)
- Uses connection's OAuth access token
- Sends test Purchase event with unique event_id
- Returns success/failure with Meta's response

**Why Test Events?**:
- Test events don't affect ad optimization or reporting
- Visible immediately in Meta Events Manager
- Validates entire CAPI pipeline (token, pixel ID, API connectivity)
- Users can verify setup before relying on real attribution data

---

## Database Schema

### Tables

```sql
-- Customer Journeys (tracks visitors across sessions)
-- NOTE: Journey 1:N Orders (one visitor can make multiple purchases over time)
CREATE TABLE customer_journeys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id),

    -- Identity
    visitor_id TEXT NOT NULL,
    customer_email TEXT,
    shopify_customer_id BIGINT,

    -- For linking to orders
    checkout_token TEXT,  -- Most recent checkout (for webhook merge)

    -- First touch attribution (captured on first visit)
    first_touch_source TEXT,
    first_touch_medium TEXT,
    first_touch_campaign TEXT,
    first_touch_entity_id UUID REFERENCES entities(id),

    -- Last touch (updated on each touchpoint)
    last_touch_source TEXT,
    last_touch_medium TEXT,
    last_touch_campaign TEXT,
    last_touch_entity_id UUID REFERENCES entities(id),

    -- Journey state
    first_seen_at TIMESTAMPTZ NOT NULL,
    last_seen_at TIMESTAMPTZ NOT NULL,
    touchpoint_count INT DEFAULT 0,

    -- Conversion tracking
    total_orders INT DEFAULT 0,
    total_revenue DECIMAL(12,2) DEFAULT 0,
    first_order_at TIMESTAMPTZ,
    last_order_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT uq_journey_visitor UNIQUE(workspace_id, visitor_id)
);

-- Journey Touchpoints (each marketing interaction)
CREATE TABLE journey_touchpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    journey_id UUID NOT NULL REFERENCES customer_journeys(id) ON DELETE CASCADE,

    -- Event info
    event_type TEXT NOT NULL,

    -- Attribution params
    utm_source TEXT,
    utm_medium TEXT,
    utm_campaign TEXT,
    utm_content TEXT,
    utm_term TEXT,
    fbclid TEXT,
    gclid TEXT,
    ttclid TEXT,

    -- Resolved entity (if matched)
    entity_id UUID REFERENCES entities(id),
    provider TEXT,

    -- Context
    landing_page TEXT,
    referrer TEXT,

    touched_at TIMESTAMPTZ NOT NULL
);

-- Pixel Events (immutable raw event log - for event sourcing)
CREATE TABLE pixel_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id),
    visitor_id TEXT NOT NULL,
    event_id TEXT,  -- Client-generated UUID for deduplication
    event_type TEXT NOT NULL,
    event_data JSONB DEFAULT '{}',

    -- Attribution
    utm_source TEXT,
    utm_medium TEXT,
    utm_campaign TEXT,
    utm_content TEXT,
    utm_term TEXT,
    fbclid TEXT,
    gclid TEXT,
    ttclid TEXT,
    landing_page TEXT,

    -- Context
    url TEXT,
    referrer TEXT,
    ip_hash TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Shopify Orders (with checkout_token for journey linking)
-- NOTE: Add checkout_token to existing table
ALTER TABLE shopify_orders ADD COLUMN IF NOT EXISTS checkout_token TEXT;

-- Attributions (final attribution records)
CREATE TABLE attributions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id),

    -- Links
    journey_id UUID REFERENCES customer_journeys(id),
    shopify_order_id UUID REFERENCES shopify_orders(id),

    -- Attribution result
    entity_id UUID REFERENCES entities(id),
    provider TEXT NOT NULL,  -- meta, google, tiktok, direct, organic, unknown
    entity_level TEXT,  -- campaign, adset, ad (NULL if no entity match)

    -- Match info
    match_type TEXT NOT NULL,  -- gclid, utm_campaign, utm_content, fbclid, utm_source, referrer, none
    confidence TEXT NOT NULL,  -- high, medium, low, none
    attribution_model TEXT NOT NULL DEFAULT 'last_click',
    attribution_window_days INT DEFAULT 30,

    -- Revenue (stored in order's original currency)
    attributed_revenue DECIMAL(12,2),
    attribution_credit DECIMAL(5,4) DEFAULT 1.0,  -- For multi-touch (0.0-1.0)
    currency TEXT NOT NULL DEFAULT 'USD',

    -- Timestamps
    order_created_at TIMESTAMPTZ,
    attributed_at TIMESTAMPTZ DEFAULT NOW(),

    -- Idempotency
    CONSTRAINT uq_attribution UNIQUE(shopify_order_id, attribution_model)
);

-- Indexes
CREATE INDEX idx_journeys_workspace ON customer_journeys(workspace_id);
CREATE INDEX idx_journeys_visitor ON customer_journeys(workspace_id, visitor_id);
CREATE INDEX idx_journeys_checkout ON customer_journeys(workspace_id, checkout_token)
    WHERE checkout_token IS NOT NULL;
CREATE INDEX idx_journeys_email ON customer_journeys(workspace_id, customer_email)
    WHERE customer_email IS NOT NULL;

CREATE INDEX idx_touchpoints_journey ON journey_touchpoints(journey_id, touched_at);
CREATE INDEX idx_touchpoints_gclid ON journey_touchpoints(gclid) WHERE gclid IS NOT NULL;
CREATE INDEX idx_touchpoints_fbclid ON journey_touchpoints(fbclid) WHERE fbclid IS NOT NULL;

CREATE INDEX idx_pixel_events_workspace ON pixel_events(workspace_id, created_at DESC);
CREATE INDEX idx_pixel_events_visitor ON pixel_events(workspace_id, visitor_id, created_at DESC);
CREATE INDEX idx_pixel_events_dedup ON pixel_events(workspace_id, event_id)
    WHERE event_id IS NOT NULL;

CREATE INDEX idx_shopify_orders_checkout ON shopify_orders(workspace_id, checkout_token)
    WHERE checkout_token IS NOT NULL;

CREATE INDEX idx_attributions_workspace ON attributions(workspace_id, order_created_at DESC);
CREATE INDEX idx_attributions_entity ON attributions(entity_id, order_created_at DESC);
CREATE INDEX idx_attributions_provider ON attributions(workspace_id, provider, order_created_at DESC);

-- Add web_pixel_id to connections table
ALTER TABLE connections ADD COLUMN IF NOT EXISTS web_pixel_id TEXT;
```

### Entity Relationships

```
Workspace 1:N CustomerJourney
CustomerJourney 1:N JourneyTouchpoint
CustomerJourney 1:N ShopifyOrder (one visitor lifetime, many orders)
ShopifyOrder 1:N Attribution (one per model: first_click, last_click, linear)
Attribution N:1 Entity (the attributed campaign/ad, can be NULL)
JourneyTouchpoint N:1 Entity (resolved touchpoint, can be NULL)
```

### Multi-Currency Note

For v1, we store metrics in the order's original currency and aggregate per currency.
Future enhancement: Add base currency conversion with FX rates.

---

## Health Monitoring

### Health Checks

| Check | Frequency | Alert Condition | Severity |
|-------|-----------|-----------------|----------|
| **Pixel events received** | 5 min | No events from workspace in 1 hour | Warning |
| **Webhook received** | 5 min | No webhooks from active store in 6 hours | Warning |
| **Attribution rate** | Hourly | <50% of orders attributed | Critical |
| **Pixel/webhook sync** | Hourly | >20% of orders missing pixel event | Warning |
| **CAPI success rate** | Hourly | >10% of CAPI calls failing | Critical |
| **gclid resolution rate** | Daily | >50% of gclid lookups failing | Warning |

### Health Check Implementation

```python
# app/services/health_monitor.py

class AttributionHealthMonitor:
    """
    Monitor health of attribution pipeline.
    """

    async def check_pixel_health(self, workspace_id: UUID) -> tuple[str, str]:
        """Check if pixel is sending events."""
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)

        count = db.query(PixelEvent).filter(
            PixelEvent.workspace_id == workspace_id,
            PixelEvent.created_at >= one_hour_ago
        ).count()

        if count == 0:
            return "failing", "No pixel events in last hour"
        return "healthy", f"{count} events in last hour"

    async def check_attribution_rate(self, workspace_id: UUID) -> tuple[str, str]:
        """Check percentage of orders with attribution."""
        last_24h = datetime.utcnow() - timedelta(hours=24)

        total_orders = db.query(ShopifyOrder).filter(
            ShopifyOrder.workspace_id == workspace_id,
            ShopifyOrder.order_created_at >= last_24h
        ).count()

        if total_orders == 0:
            return "no_data", "No orders in last 24 hours"

        attributed = db.query(Attribution).filter(
            Attribution.workspace_id == workspace_id,
            Attribution.order_created_at >= last_24h,
            Attribution.confidence != "none"
        ).count()

        rate = attributed / total_orders

        if rate < 0.3:
            return "failing", f"Only {rate:.0%} of orders attributed"
        elif rate < 0.5:
            return "degraded", f"Only {rate:.0%} of orders attributed"

        return "healthy", f"{rate:.0%} of orders attributed"

    async def check_capi_health(self, workspace_id: UUID) -> tuple[str, str]:
        """Check CAPI success rate."""
        last_hour = datetime.utcnow() - timedelta(hours=1)

        # Check CAPI call logs (need to add logging)
        # ...

        return "healthy", "CAPI working normally"
```

### Logging Standards

All attribution components use structured logging:

```python
logger.info(
    "[ATTRIBUTION] Order attributed",
    order_id=str(order.id),
    workspace_id=str(workspace_id),
    provider=result.provider,
    match_type=result.match_type,
    confidence=result.confidence,
    entity_id=str(result.entity_id) if result.entity_id else None,
    latency_ms=latency
)
```

**Log Markers**:
- `[PIXEL]`: Pixel event ingestion
- `[WEBHOOK]`: Shopify webhook handling
- `[ATTRIBUTION]`: Attribution processing
- `[JOURNEY]`: Customer journey updates
- `[CAPI]`: Conversions API calls
- `[HEALTH]`: Health check results

---

## Implementation Progress

### Week 1: Shopify Web Pixel Extension ✅ COMPLETE

| Task | Status | Notes |
|------|--------|-------|
| Create extension scaffold | ✅ | `shopify-app/metricx/extensions/metricx-pixel/` |
| Configure shopify.extension.toml | ✅ | Privacy settings, workspaceId, apiEndpoint fields |
| Implement index.js with consent checks | ✅ | Respects analyticsAllowed/marketingAllowed |
| Use correct cookie API (strict mode) | ✅ | No options object in strict mode |
| Add event_id for deduplication | ✅ | Client-generated UUID per event |
| Subscribe to specific events (not all) | ✅ | page_viewed, product_viewed, cart, checkout |
| Backend /v1/pixel-events endpoint | ✅ | `backend/app/routers/pixel_events.py` with idempotency |
| Pixel activation service | ✅ | `backend/app/services/pixel_activation_service.py` |
| Add OAuth scopes | ✅ | write_pixels, read_customer_events added to Shopify Partners |
| Integrate activation with OAuth | ✅ | Pixel activated on shop connect via GraphQL |
| Database migrations | ✅ | `20251130_000001_add_attribution_tables.py` |
| Deploy extension | ✅ | Deployed via `shopify app deploy` (v7) |
| CORS for sandboxed iframe | ✅ | Wildcard `*` origin + ngrok header support |
| End-to-end test | ✅ | Pixel → Backend flow verified working |

### Week 2: Attribution Core ✅ COMPLETE

| Task | Status | Notes |
|------|--------|-------|
| Database migrations | ✅ | journeys, touchpoints, attributions (done in Week 1) |
| Add checkout_token to shopify_orders | ✅ | For journey linking |
| CustomerJourney model | ✅ | SQLAlchemy model with relationships |
| JourneyTouchpoint model | ✅ | SQLAlchemy model |
| Attribution model | ✅ | SQLAlchemy model with unique constraint |
| Journey service | ✅ | Created in pixel_events.py |
| Attribution service with priority | ✅ | gclid > utm_campaign > fbclid > utm_source > referrer |
| orders/paid webhook handler | ✅ | `POST /webhooks/shopify/orders/paid` |
| Webhook subscription service | ✅ | Auto-subscribes on OAuth connect |
| Direct/organic classification | ✅ | Proper fallback logic in webhook |

### Week 3: Click Resolution + CAPI ✅ COMPLETE

| Task | Status | Notes |
|------|--------|-------|
| Meta CAPI service | ✅ | `backend/app/services/meta_capi_service.py` |
| CAPI integration with attribution | ✅ | Fires on meta-attributed orders |
| event_id deduplication | ✅ | Uses `order_{order_id}` prefix |
| Google Click Resolution | ✅ | `backend/app/services/gclid_resolution_service.py` |
| Click ID caching | ✅ | Redis cache with 7-day TTL |
| Meta Pixel OAuth integration | ✅ | Pixels fetched during OAuth, saved to connection |
| Google Offline Conversions | ✅ | `backend/app/services/google_conversions_service.py` |

### Week 4: Attribution UX - Phase 1 ✅ COMPLETE

| Task | Status | Notes |
|------|--------|-------|
| Pixel Health API | ✅ | `GET /workspaces/{id}/pixel/health` |
| Pixel Reinstall API | ✅ | `POST /workspaces/{id}/pixel/reinstall` |
| Attribution Summary API | ✅ | `GET /workspaces/{id}/attribution/summary` |
| Attribution Campaigns API | ✅ | `GET /workspaces/{id}/attribution/campaigns` |
| Attribution Feed API | ✅ | `GET /workspaces/{id}/attribution/feed` |
| Campaign Warnings API | ✅ | `GET /workspaces/{id}/attribution/warnings` |
| Pixel Health Card (Settings) | ✅ | `ui/app/(dashboard)/settings/components/PixelHealthCard.jsx` |
| Attribution Card (Dashboard) | ✅ | `ui/app/(dashboard)/dashboard/components/AttributionCard.jsx` |
| Live Attribution Feed | ✅ | `ui/app/(dashboard)/dashboard/components/LiveAttributionFeed.jsx` |
| UTM Setup Guide | ✅ | `ui/app/(dashboard)/settings/components/UTMSetupGuide.jsx` |
| Campaign Warnings Panel | ✅ | `ui/app/(dashboard)/campaigns/components/CampaignWarningsPanel.jsx` |
| Frontend API Functions | ✅ | Added to `ui/lib/api.js` |

### Week 5: Dashboard KPIs with Smart Data Source ✅ COMPLETE

| Task | Status | Notes |
|------|--------|-------|
| Dashboard KPIs endpoint | ✅ | `GET /workspaces/{id}/dashboard/kpis` |
| Shopify-first revenue | ✅ | Uses Shopify orders when connected |
| Platform fallback | ✅ | Falls back to MetricFact for SaaS users |
| Attribution-based conversions | ✅ | Counts ad-attributed orders (excludes direct/organic) |
| ROAS computation | ✅ | revenue/spend with daily sparkline |
| KpiStrip frontend update | ✅ | Uses new endpoint with data_source indicator |
| API function | ✅ | `fetchDashboardKpis()` in api.js |

### Week 6: Attribution Page + Settings Clarity + CAPI Testing ✅ COMPLETE

| Task | Status | Notes |
|------|--------|-------|
| Dedicated Attribution Page | ✅ | `/dashboard/attribution` with full overview |
| Sidebar Navigation | ✅ | Attribution link added under Dashboard |
| Pixel Health Card Clarity | ✅ | Renamed to "Shopify Tracking Pixel" with explanation |
| Health Score Explanation | ✅ | Tooltip + contextual text explaining 0-100 score |
| Meta CAPI Status Indicator | ✅ | Shows "Configured" / "Not configured" per connection |
| KPI Strip (Revenue, Orders, Rate, AOV) | ✅ | Top metrics with trend indicators |
| Revenue by Channel Chart | ✅ | Pie chart + breakdown list |
| Top Campaigns Bar Chart | ✅ | Horizontal bar chart of top 5 |
| Live Attribution Feed | ✅ | Real-time feed on page |
| Campaign Warnings Panel | ✅ | Issues with tracking |
| Timeframe Selector | ✅ | 7, 14, 30, 90 days |
| Meta CAPI Test Endpoint | ✅ | `POST /workspaces/{id}/meta-capi/test` |
| ConnectionOut meta_pixel_id | ✅ | Fixed schema to include pixel ID in response |
| Pixel Assignment UX | ✅ | Instructions for assigning pixel to ad account |

### Week 7: Attribution UX - Phase 3 (Future)

| Task | Status | Notes |
|------|--------|-------|
| Multi-model support | 🔲 | first_click, last_click, linear |
| Attribution windows config | 🔲 | 7/14/28/30 day per workspace |
| Platform comparison | 🔲 | Platform vs Metricx data (side-by-side) |
| Smoke tests | 🔲 | Full pipeline tests |
| Contract tests | 🔲 | Realistic webhook/pixel payloads |

---

## Testing

### Smoke Tests

```python
# tests/smoke/test_attribution_pipeline.py

class TestPixelEndpoint:
    """Pixel event ingestion."""

    async def test_page_view_accepted(self, client, test_workspace):
        response = await client.post("/v1/pixel-events", json={
            "workspace_id": str(test_workspace.id),
            "visitor_id": "mx_test123",
            "event_id": "evt_unique_123",
            "event": "page_viewed",
            "attribution": {"utm_source": "meta", "utm_campaign": "summer_sale"}
        })
        assert response.status_code == 200

    async def test_duplicate_event_rejected(self, client, db, test_workspace):
        """Test idempotency via event_id."""
        event_id = "evt_duplicate_test"

        # First request succeeds
        response1 = await client.post("/v1/pixel-events", json={
            "workspace_id": str(test_workspace.id),
            "visitor_id": "mx_test",
            "event_id": event_id,
            "event": "page_viewed"
        })
        assert response1.status_code == 200
        assert response1.json()["status"] == "ok"

        # Second request is deduplicated
        response2 = await client.post("/v1/pixel-events", json={
            "workspace_id": str(test_workspace.id),
            "visitor_id": "mx_test",
            "event_id": event_id,
            "event": "page_viewed"
        })
        assert response2.json()["status"] == "duplicate"


class TestAttribution:
    """Attribution matching."""

    async def test_gclid_highest_priority(self, db, test_workspace):
        """gclid should be resolved before UTM matching."""
        # Create campaign
        campaign = Entity(
            workspace_id=test_workspace.id,
            name="Summer Sale",
            external_id="google_campaign_123",
            level="campaign",
            provider="google"
        )
        db.add(campaign)
        db.commit()

        # Journey with both gclid AND utm_campaign
        # gclid should win
        journey = CustomerJourney(...)
        touchpoint = JourneyTouchpoint(
            journey_id=journey.id,
            gclid="test_gclid_123",
            utm_campaign="different_campaign",  # Should be ignored
            touched_at=datetime.utcnow()
        )

        # Mock gclid resolution to return the campaign
        service = AttributionService(db)
        service.click_resolution.resolve_gclid = Mock(return_value=campaign)

        result = service._attribute_touchpoint(touchpoint, test_workspace.id)

        assert result.match_type == "gclid"
        assert result.entity_id == campaign.id

    async def test_attribution_window_enforced(self, db, test_workspace):
        """Touchpoints outside window should be ignored."""
        # Create journey with old touchpoint
        journey = CustomerJourney(...)
        old_touchpoint = JourneyTouchpoint(
            journey_id=journey.id,
            utm_source="meta",
            touched_at=datetime.utcnow() - timedelta(days=45)  # Outside 30-day window
        )

        order = ShopifyOrder(
            order_created_at=datetime.utcnow(),
            ...
        )

        service = AttributionService(db)
        result = service.attribute_order(order, window_days=30)

        # Should be direct/organic/unknown, not attributed to meta
        assert result.provider in ["direct", "organic", "unknown"]

    async def test_direct_vs_organic_classification(self, db, test_workspace):
        """Test correct classification of unattributed orders."""
        service = AttributionService(db)

        # Direct: No referrer, no UTMs
        order_direct = ShopifyOrder(
            referring_site="",
            landing_site="/products/test",
            ...
        )
        result = service._classify_unattributed(order_direct)
        assert result.provider == "direct"

        # Organic: Google referrer, no gclid
        order_organic = ShopifyOrder(
            referring_site="https://www.google.com/search?q=test",
            gclid=None,
            ...
        )
        result = service._classify_unattributed(order_organic)
        assert result.provider == "organic"


class TestWebhookMerge:
    """Webhook and pixel data merge via checkout_token."""

    async def test_journey_linked_by_checkout_token(self, db, client, test_workspace):
        """Order webhook should find journey by checkout_token."""
        checkout_token = "test_checkout_abc123"

        # Pixel sends checkout_completed with token
        await client.post("/v1/pixel-events", json={
            "workspace_id": str(test_workspace.id),
            "visitor_id": "mx_buyer",
            "event": "checkout_completed",
            "data": {"checkout_token": checkout_token},
            "attribution": {"utm_source": "meta", "fbclid": "fb_123"}
        })

        # Verify journey has checkout_token
        journey = db.query(CustomerJourney).filter_by(
            visitor_id="mx_buyer"
        ).first()
        assert journey.checkout_token == checkout_token

        # Webhook comes in with same token
        # ... simulate webhook with checkout_token ...

        # Attribution should find the journey and use pixel attribution data
```

### Contract Tests

```python
# tests/contract/test_shopify_payloads.py

"""
Contract tests with realistic Shopify payloads.
Ensures our handlers work with actual Shopify data structures.
"""

REALISTIC_ORDER_WEBHOOK = {
    "id": 5678901234,
    "order_number": "1001",
    "checkout_token": "abc123def456",
    "total_price": "149.99",
    "subtotal_price": "139.99",
    "currency": "USD",
    "financial_status": "paid",
    "landing_site": "/?utm_source=meta&utm_campaign=summer_sale&fbclid=abc123",
    "referring_site": "https://l.facebook.com/",
    "customer": {
        "id": 12345,
        "email": "customer@example.com",
        "first_name": "John",
        "last_name": "Doe"
    },
    "line_items": [
        {
            "id": 111,
            "product_id": 222,
            "variant_id": 333,
            "title": "Test Product",
            "quantity": 2,
            "price": "69.99"
        }
    ],
    "created_at": "2025-11-30T12:00:00Z"
}

class TestOrderWebhookContract:
    async def test_realistic_order_payload(self, client, test_shop):
        """Test with realistic Shopify order payload."""
        response = await client.post(
            "/webhooks/shopify/orders",
            json=REALISTIC_ORDER_WEBHOOK,
            headers={
                "X-Shopify-Hmac-SHA256": compute_hmac(REALISTIC_ORDER_WEBHOOK),
                "X-Shopify-Shop-Domain": test_shop.shop_domain,
                "X-Shopify-Topic": "orders/paid"
            }
        )
        assert response.status_code == 200

        # Verify order stored correctly
        order = db.query(ShopifyOrder).filter_by(
            shopify_order_id=5678901234
        ).first()
        assert order is not None
        assert order.checkout_token == "abc123def456"
        assert order.utm_source == "meta"
        assert order.fbclid == "abc123"
```

---

## Known Limitations & Future Work

### V1 Limitations (Accepted)

| Limitation | Impact | Future Fix |
|------------|--------|------------|
| **Single currency per order** | Can't aggregate across currencies | Add base currency + FX conversion |
| **No refund handling** | Attributed revenue not adjusted | Update attribution on refund webhook |
| **No view-through attribution** | Only click-based | Integrate impression data from ad APIs |
| **No cross-device tracking** | Mobile → Desktop not linked | Use email/customer_id for linking |
| **30-day max window** | Some long sales cycles not captured | Make configurable per workspace |

### Event Sourcing (V2 Consideration)

Current architecture stores journey state + immutable pixel events.
For V2, consider full event sourcing:

```
Current (V1):
─────────────
PixelEvent (immutable log) + CustomerJourney (mutable state)

Problem: If attribution logic changes, hard to recompute historical data.


Event Sourcing (V2):
────────────────────
PixelEvent (immutable log) → Derive journey state on read

Benefits:
- Replay events with new attribution logic
- Debug by looking at event sequence
- Never lose data
- Recompute historical attributions with new models
```

### UI Notes

When building the attribution dashboard:
- Show attribution at all levels: Channel → Campaign → Adset → Ad → Creative
- Always display attribution model + window next to revenue metrics
- Show confidence level (high/medium/low/none)
- Highlight discrepancies between platform-reported and attributed revenue

---

## Environment Variables

```bash
# Pixel endpoint (where web pixel sends events)
PIXEL_ENDPOINT=https://api.metricx.ai/v1/pixel-events

# Meta Conversions API
META_PIXEL_ID=xxx
META_CAPI_ACCESS_TOKEN=xxx

# Google Ads (for gclid resolution + offline conversions)
GOOGLE_ADS_DEVELOPER_TOKEN=xxx
GOOGLE_ADS_LOGIN_CUSTOMER_ID=xxx

# Attribution settings
DEFAULT_ATTRIBUTION_MODEL=last_click
DEFAULT_ATTRIBUTION_WINDOW_DAYS=30
```

---

## References

- [Shopify Web Pixels API](https://shopify.dev/docs/api/web-pixels-api)
- [Shopify Standard Events](https://shopify.dev/docs/api/web-pixels-api/standard-events)
- [Shopify Customer Privacy API](https://shopify.dev/docs/api/web-pixels-api/customer-privacy)
- [Meta Conversions API](https://developers.facebook.com/docs/marketing-api/conversions-api)
- [Google Ads Offline Conversions](https://developers.google.com/google-ads/api/docs/conversions/upload-clicks)
- [Google Click View](https://developers.google.com/google-ads/api/reference/rpc/latest/ClickView)

---

## Changelog

### v1.10.0 (2025-12-02) - Meta CAPI Testing + Pixel Configuration UX
**Added CAPI test endpoint and improved pixel assignment guidance.**

New Features:
- **Meta CAPI Test Endpoint** - `POST /workspaces/{id}/meta-capi/test` for verifying CAPI integration
- **Test Event Code Support** - Send test events visible in Meta Events Manager
- **ConnectionOut Schema Fix** - Added `meta_pixel_id` field so pixel config status shows correctly
- **Improved Pixel Assignment UX** - Clear instructions when no pixel is assigned to ad account
- **Business Settings Link** - Direct link to Meta Business Settings → Data Sources → Pixels

Testing CAPI:
1. Go to Meta Events Manager → Your Pixel → Test Events
2. Copy the test event code (e.g., `TEST12345`)
3. Call `POST /workspaces/{id}/meta-capi/test` with `{"test_event_code": "TEST12345"}`
4. Watch the event appear in Meta Events Manager

Files Added:
- Test endpoint in `backend/app/routers/attribution.py`

Files Modified:
- `backend/app/schemas.py` - Added `meta_pixel_id` to `ConnectionOut`
- `ui/app/(dashboard)/settings/components/MetaPixelSelector.jsx` - Improved no-pixel instructions
- `ui/components/MetaAccountSelectionModal.jsx` - Added pixel assignment guidance

Why This Matters:
- Users couldn't verify CAPI was working without making a real purchase
- Pixel config status showed "Not configured" even after saving (schema missing field)
- Users were confused when no pixels appeared (pixels live at Business Manager level, must be assigned to ad accounts)

---

### v1.9.0 (2025-12-02) - Attribution Page + Settings Clarity
**Full dedicated Attribution page and improved Settings UX for pixel clarity.**

New Features:
- **Dedicated Attribution Page** - `/dashboard/attribution` with unified view
- **Sidebar Navigation** - Attribution link with Target icon under Dashboard
- **Improved Pixel Health Card** - Renamed to "Shopify Tracking Pixel" with explanation
- **Health Score Explanation** - Tooltip showing calculation (base + events + checkouts - issues)
- **Contextual Health Text** - Dynamic explanation based on score and events
- **Meta CAPI Status** - Shows configuration status per Meta connection in Settings

Attribution Page Components:
- KPI Strip: Attributed Revenue, Orders, Attribution Rate, Avg Order Value
- Revenue by Channel: Pie chart with breakdown list (Meta, Google, Direct, Organic, etc.)
- Top Campaigns: Horizontal bar chart of top 5 campaigns by attributed revenue
- Live Attribution Feed: Real-time feed with auto-refresh
- Campaign Warnings: Alerts for campaigns with tracking issues
- Timeframe Selector: 7, 14, 30, 90 day options

Files Added:
- `ui/app/(dashboard)/dashboard/attribution/page.jsx` - Full attribution page

Files Modified:
- `ui/app/(dashboard)/settings/components/PixelHealthCard.jsx` - Clarity improvements
- `ui/app/(dashboard)/settings/components/ConnectionsTab.jsx` - Meta CAPI status
- `ui/app/(dashboard)/components/shared/Sidebar.jsx` - Attribution nav item

Why This Matters:
- Users had scattered attribution components with no unified view
- "Pixel Health" was confusing (Shopify Web Pixel vs Meta Pixel)
- Health score (e.g., 70%) was unexplained
- Meta CAPI configuration status was hidden

User Journey:
1. Dashboard → See KPI strip with attribution data
2. Dashboard → Attribution → Full attribution overview
3. Settings → Connections → See Shopify Tracking Pixel health with explanation
4. Settings → Connections → See Meta CAPI status per connection

### v1.8.0 (2025-12-02) - Dashboard KPIs Router Fix
**Fixed dashboard KPIs endpoint registration.**

### v1.7.0 (2025-12-02) - Dashboard KPIs with Smart Data Source
**Triple Whale-style KPIs: Shopify orders as source of truth with SaaS fallback.**

New Features:
- **Dashboard KPIs endpoint** - `GET /workspaces/{id}/dashboard/kpis`
- **Shopify-first revenue** - Uses `shopify_orders.total_price` when Shopify connected
- **Platform fallback** - Falls back to `metric_facts.revenue` for SaaS users without Shopify
- **Attribution-based conversions** - Counts attributions excluding direct/organic/unknown
- **ROAS computation** - Daily sparkline from revenue/spend per day
- **Data source indicator** - Response includes `data_source: "shopify" | "platform"`

Why This Matters:
- Platform-reported revenue is often inflated (attribution window differences)
- Shopify orders are the actual source of truth for e-commerce merchants
- SaaS users without Shopify still see their platform metrics
- Isolated endpoint for production safety (doesn't affect existing /kpis)

Files Added:
- `backend/app/routers/dashboard_kpis.py` - New isolated endpoint

Files Modified:
- `backend/app/main.py` - Added router registration
- `ui/lib/api.js` - Added `fetchDashboardKpis()` function
- `ui/app/(dashboard)/dashboard/components/KpiStrip.jsx` - Updated to use new endpoint

Response Shape:
```json
{
  "kpis": [
    {"key": "revenue", "value": 2100.00, "prev": 1800.00, "delta_pct": 0.167, "sparkline": [...]},
    {"key": "roas", "value": 3.5, "prev": 3.2, "delta_pct": 0.094, "sparkline": [...]},
    {"key": "spend", "value": 600.00, "prev": 562.50, "delta_pct": 0.067, "sparkline": [...]},
    {"key": "conversions", "value": 12, "prev": 10, "delta_pct": 0.2, "sparkline": [...]}
  ],
  "data_source": "shopify",
  "has_shopify": true
}
```

Data Source Logic:
1. Check if workspace has active Shopify connection
2. If YES (e-commerce): Revenue from shopify_orders, conversions from attributions
3. If NO (SaaS): Revenue from metric_facts.revenue, conversions from metric_facts.conversions
4. Spend: Always from metric_facts (ad platforms)
5. ROAS: Computed from revenue/spend regardless of source

### v1.6.0 (2025-12-01) - Google Offline Conversions
**Complete CAPI loop - both Meta and Google now receive purchase data.**

New Features:
- **Google Offline Conversions service** - Uploads purchase conversions to Google Ads
- Automatic conversion upload for Google-attributed orders
- `google_conversion_action_id` setting on connections
- Settings endpoints for conversion action ID management
- Integration with attribution flow (fires on Google-attributed orders)

Files Added:
- `backend/app/services/google_conversions_service.py` - Full Google conversions implementation
- `backend/alembic/versions/20251201_000001_add_google_conversion_action_id.py` - Migration

Files Modified:
- `backend/app/models.py` - Added `google_conversion_action_id` column
- `backend/app/routers/connections.py` - Added PATCH/GET endpoints for conversion action ID
- `backend/app/routers/shopify_webhooks.py` - Integrated Google conversions upload

How Google Offline Conversions Work:
1. Order attributed to Google (via gclid or UTMs)
2. Service looks up Google connection and conversion_action_id
3. Uploads conversion via ConversionUploadService API
4. Google uses data for Smart Bidding optimization

Prerequisites:
- Conversion Action must exist in Google Ads account
- Set `google_conversion_action_id` via settings API or env var
- gclid must be captured within 90 days of click

Environment Variables:
- `GOOGLE_CONVERSION_ACTION_ID` - Fallback conversion action ID
- `GOOGLE_DEVELOPER_TOKEN` - Required for API access

### v1.5.0 (2025-12-01) - Google Click Resolution + Meta OAuth Pixel
**High-confidence attribution via gclid lookup and improved Meta integration.**

New Features:
- **gclid Resolution Service** - Queries Google Ads API ClickView to resolve gclid to actual campaign/ad
- Automatic Entity matching from resolved campaign data
- Redis caching for resolved gclid data (7-day TTL)
- Meta Pixel fetched during OAuth and saved to connection
- Meta OAuth accepts pixel_id selection with ad account selection

Files Added:
- `backend/app/services/gclid_resolution_service.py` - Full gclid resolution implementation

Files Modified:
- `backend/app/routers/shopify_webhooks.py` - Integrated gclid resolution in attribution flow
- `backend/app/routers/meta_oauth.py` - Added pixel fetching and selection

How gclid Resolution Works:
1. When attribution runs with gclid, service queries Google Ads API
2. Uses ClickView resource with date filter (click_view requires single-day query)
3. Tries landing date + adjacent days for timezone tolerance
4. Returns campaign_id, campaign_name, ad_group_id, ad_group_name, ad_id
5. Results cached in Redis to avoid repeated API calls

Constraints:
- ClickView requires single-day filter (can't query by gclid alone)
- Only last 90 days of click data available from Google
- Requires active Google Ads connection with valid refresh token

Environment Variables:
- `GOOGLE_DEVELOPER_TOKEN` - Required for Google Ads API
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` - OAuth credentials
- `REDIS_URL` - Required for gclid caching

Dependencies:
- `google-ads>=28.0.0` - Google deprecates old API versions; keep SDK updated
- Error `501 GRPC target method can't be resolved` means SDK is outdated

### v1.4.0 (2025-11-30) - Meta CAPI Integration
**Server-side conversion tracking for Meta ads.**

New Features:
- Meta Conversions API (CAPI) service for sending purchase events
- Automatic CAPI fire for Meta-attributed orders
- event_id deduplication with order ID prefix
- SHA256 hashing for PII (email, phone)
- Support for fbclid matching
- Test event code support for debugging in Events Manager

Files Added:
- `backend/app/services/meta_capi_service.py` - Full CAPI implementation

Environment Variables:
- `META_PIXEL_ID` - Required: Your Meta Pixel ID
- `META_CAPI_ACCESS_TOKEN` - Optional: Override connection token
- `META_CAPI_TEST_EVENT_CODE` - Optional: Test event code for debugging

Flow:
1. Order paid → Attribution created (provider=meta)
2. CAPI fires Purchase event to Meta
3. Event deduped with browser pixel via event_id

### v1.3.0 (2025-11-30) - Week 2 Complete ✅ TESTED END-TO-END
**Attribution engine fully implemented with orders/paid webhook.**

**End-to-End Test Successful:**
```
✅ Pixel captures UTMs (utm_source=meta, utm_campaign=attribution_test)
✅ Touchpoints created for journey
✅ checkout_token linked to journey on checkout_completed
✅ orders/paid webhook received from Shopify
✅ Journey found by checkout_token
✅ Attribution record created (provider=meta, match_type=utm_campaign)
```

New Features:
- `orders/paid` webhook handler triggers attribution on payment
- Orders linked to journeys via `checkout_token`
- Attribution stored with provider, match_type, confidence
- Webhook auto-subscription on OAuth connect (requires NGROK_URL for local dev)
- Direct/organic/unknown classification for unattributed orders

Attribution Flow:
1. Visitor lands with UTMs → pixel creates journey + touchpoints
2. Visitor completes checkout → pixel links checkout_token to journey
3. Order paid → webhook finds journey by checkout_token
4. Attribution runs → stores provider/match_type/confidence
5. Journey stats updated (total_orders, total_revenue)

Files Added/Modified:
- `backend/app/routers/shopify_webhooks.py` - Added orders/paid handler with attribution logic
- `backend/app/services/webhook_subscription_service.py` - New service for webhook registration
- `backend/app/routers/shopify_oauth.py` - Added webhook subscription on connect

Attribution Priority Chain:
1. gclid → Google (high confidence)
2. utm_campaign → inferred provider (high)
3. fbclid → Meta (medium)
4. utm_source → inferred provider (low)
5. referrer → organic/social/unknown (low)
6. No data → direct/unknown

Environment Variables Required:
- `NGROK_URL` - HTTPS ngrok URL for local webhook testing (e.g., `https://xxx.ngrok-free.dev`)

### v1.2.0 (2025-11-30) - Week 1 Complete
**Web Pixel Extension fully implemented and tested end-to-end.**

New Features:
- Shopify Web Pixel Extension deployed (v7)
- Pixel auto-activates on OAuth connect via GraphQL `webPixelCreate`
- Customer journeys created and updated per visitor
- Touchpoints recorded when attribution data (UTM/click IDs) present
- Event deduplication via client-generated `event_id`

Backend Changes:
- `POST /v1/pixel-events` endpoint with full CORS support
- `PixelCORSMiddleware` handles sandboxed iframe origin (`null`)
- Added `ngrok-skip-browser-warning` header support for local dev
- Fixed journey flush before touchpoint creation (`db.flush()`)
- Database migration: `20251130_000001_add_attribution_tables.py`

Files Added/Modified:
- `shopify-app/metricx/extensions/metricx-pixel/` - Full pixel extension
- `backend/app/routers/pixel_events.py` - Events endpoint
- `backend/app/services/pixel_activation_service.py` - GraphQL activation
- `backend/app/routers/shopify_oauth.py` - Pixel activation on connect
- `backend/app/routers/connections.py` - Shopify table cleanup on delete
- `backend/app/main.py` - CORS middleware for pixel endpoint

### v1.1.0 (2025-11-30)
- Fixed cookie API for Shopify strict mode (no options object)
- Added checkout_token to shopify_orders for journey linking
- Added event_id for pixel event deduplication
- Added attribution window enforcement in service
- Added health monitoring section
- Added OAuth scope requirements (write_pixels, read_customer_events)
- Fixed attribution priority (gclid is highest, not UTM)
- Added direct/organic/unknown classification
- Clarified journey 1:N orders relationship
- Added contract tests section
- Added multi-currency note
- Added CAPI event_id for deduplication
- Attribution now triggers on orders/paid, not checkout_completed

### v1.0.0 (2025-11-30)
- Initial specification
- Shopify Web Pixel Extension architecture
- Attribution service design
- Database schema
- Implementation plan
