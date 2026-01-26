/**
 * Metricx Web Pixel Extension
 *
 * WHAT: Captures customer journey events from Shopify storefront for attribution.
 * WHY: Enables connecting ad spend to revenue by tracking visitor journeys.
 *
 * REFERENCES:
 *   - docs/living-docs/ATTRIBUTION_ENGINE.md
 *   - Shopify Web Pixels API: https://shopify.dev/docs/api/web-pixels-api
 */

import { register } from '@shopify/web-pixels-extension';

register(async ({ analytics, browser, settings, init }) => {
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
    } catch (e) {
      // Ignore parse errors
    }
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
    }).catch(() => {
      // Silently fail - don't block user experience
    });
  };

  // ─── EVENT DATA MAPPERS ───
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
});
