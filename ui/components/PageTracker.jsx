/**
 * PageTracker - Automatic page view tracking for Next.js App Router
 *
 * WHAT: Tracks page views on every route change automatically
 * WHY: Sends page view events to RudderStack → GA4 for analytics
 *
 * USAGE: Include once in your app's providers (see providers.jsx)
 *
 * REFERENCES:
 *   - lib/analytics.js for analytics functions
 *   - docs-arch/living-docs/OBSERVABILITY.MD for architecture
 */

"use client";

import { useEffect, useRef } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import { initAnalytics, trackPageView } from "@/lib/analytics";

/**
 * PageTracker Component
 *
 * WHAT: Initializes analytics and tracks page views on route changes
 * WHY: Provides automatic page view tracking for the entire application
 *
 * HOW IT WORKS:
 * 1. On mount: Initializes RudderStack SDK
 * 2. On initial load: Tracks the first page view
 * 3. On route change: Detects pathname changes and tracks new page views
 *
 * @returns {null} Renders nothing - purely for side effects
 */
export default function PageTracker() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const isInitialized = useRef(false);
  const previousPath = useRef(null);

  // Initialize analytics on mount
  useEffect(() => {
    if (!isInitialized.current) {
      initAnalytics();
      isInitialized.current = true;
    }
  }, []);

  // Track page views on route changes
  useEffect(() => {
    // Build full path with query params
    const search = searchParams?.toString();
    const fullPath = search ? `${pathname}?${search}` : pathname;

    // Skip if same path (prevents double-tracking)
    if (previousPath.current === fullPath) {
      return;
    }

    // Track the page view
    trackPageView(fullPath);
    previousPath.current = fullPath;

    // Debug log in development
    if (process.env.NODE_ENV === "development") {
      console.log("[PageTracker] Page view:", fullPath);
    }
  }, [pathname, searchParams]);

  // This component renders nothing
  return null;
}
