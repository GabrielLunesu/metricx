/**
 * RudderStack Analytics Module - Frontend page tracking for GA4
 *
 * WHAT: Initializes RudderStack SDK and provides analytics functions
 * WHY: Track page views and user events, sent to GA4 via RudderStack
 *
 * REFERENCES:
 *   - Backend telemetry: backend/app/telemetry/analytics.py
 *   - OBSERVABILITY.md for architecture overview
 *   - https://www.rudderstack.com/docs/sources/event-streams/sdks/rudderstack-javascript-sdk/
 *
 * ENVIRONMENT VARIABLES (required):
 *   - NEXT_PUBLIC_RUDDERSTACK_WRITE_KEY: RudderStack source write key
 *   - NEXT_PUBLIC_RUDDERSTACK_DATA_PLANE_URL: RudderStack data plane URL
 */

import { RudderAnalytics } from "@rudderstack/analytics-js";

// Singleton instance
let analytics = null;
let initialized = false;

/**
 * Initialize RudderStack analytics SDK.
 *
 * WHAT: Loads and configures the RudderStack SDK
 * WHY: Must be called once before tracking events; safe to call multiple times
 *
 * @returns {boolean} True if initialization succeeded or was already done
 */
export function initAnalytics() {
  // Already initialized
  if (initialized && analytics) {
    return true;
  }

  const writeKey = process.env.NEXT_PUBLIC_RUDDERSTACK_WRITE_KEY;
  const dataPlaneUrl = process.env.NEXT_PUBLIC_RUDDERSTACK_DATA_PLANE_URL;

  // Check required env vars
  if (!writeKey || !dataPlaneUrl) {
    console.warn(
      "[Analytics] Missing NEXT_PUBLIC_RUDDERSTACK_WRITE_KEY or NEXT_PUBLIC_RUDDERSTACK_DATA_PLANE_URL. Page tracking disabled."
    );
    return false;
  }

  try {
    analytics = new RudderAnalytics();
    analytics.load(writeKey, dataPlaneUrl, {
      // Configuration options
      integrations: { All: true },
      // Automatically track page views on initial load (we handle route changes separately)
      sendAdblockPage: false,
    });

    initialized = true;
    console.log("[Analytics] RudderStack initialized successfully");
    return true;
  } catch (error) {
    console.error("[Analytics] Failed to initialize RudderStack:", error);
    return false;
  }
}

/**
 * Track a page view event.
 *
 * WHAT: Sends a page view event to RudderStack → GA4
 * WHY: Every page load should be tracked for analytics in GA4
 *
 * @param {string} path - The URL path (e.g., "/dashboard", "/analytics")
 * @param {string} [title] - Optional page title
 * @param {Object} [properties] - Additional properties to include
 *
 * @example
 * trackPageView("/dashboard", "Dashboard - metricx");
 * trackPageView("/analytics", "Analytics", { workspace_id: "123" });
 */
export function trackPageView(path, title, properties = {}) {
  if (!initialized || !analytics) {
    // Silently skip if not initialized (env vars not set)
    return;
  }

  try {
    analytics.page({
      path,
      title: title || document.title,
      url: window.location.href,
      referrer: document.referrer,
      ...properties,
    });
  } catch (error) {
    console.error("[Analytics] Failed to track page view:", error);
  }
}

/**
 * Identify a user for analytics attribution.
 *
 * WHAT: Associates a user ID with future events
 * WHY: Links page views and events to specific users in GA4
 *
 * @param {string} userId - The user's unique identifier (Clerk user ID)
 * @param {Object} [traits] - User traits (email, workspace_id, etc.)
 *
 * @example
 * identifyUser("user_123", { email: "user@example.com", workspace_id: "ws_456" });
 */
export function identifyUser(userId, traits = {}) {
  if (!initialized || !analytics) {
    return;
  }

  try {
    analytics.identify(userId, traits);
  } catch (error) {
    console.error("[Analytics] Failed to identify user:", error);
  }
}

/**
 * Track a custom event.
 *
 * WHAT: Sends a custom event to RudderStack → GA4
 * WHY: Track specific user actions beyond page views
 *
 * @param {string} eventName - The event name (e.g., "button_clicked", "form_submitted")
 * @param {Object} [properties] - Event properties
 *
 * @example
 * trackEvent("export_clicked", { format: "csv", page: "analytics" });
 */
export function trackEvent(eventName, properties = {}) {
  if (!initialized || !analytics) {
    return;
  }

  try {
    analytics.track(eventName, properties);
  } catch (error) {
    console.error("[Analytics] Failed to track event:", error);
  }
}

/**
 * Reset analytics state (e.g., on logout).
 *
 * WHAT: Clears user identity from analytics
 * WHY: Prevents user data from persisting after logout
 */
export function resetAnalytics() {
  if (!initialized || !analytics) {
    return;
  }

  try {
    analytics.reset();
  } catch (error) {
    console.error("[Analytics] Failed to reset:", error);
  }
}
