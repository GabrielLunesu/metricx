"use client";

import { Suspense } from "react";
import { Toaster } from "sonner";
import { Analytics } from "@vercel/analytics/next";
import PageTracker from "@/components/PageTracker";

/**
 * Centralized client-side providers.
 *
 * WHAT: Wraps the entire app with client-side providers and global components
 * WHY: Keeps the root layout lean while enabling toasts, analytics, and future context
 *
 * INCLUDES:
 * - Toaster: Toast notifications via sonner
 * - PageTracker: Automatic page view tracking to RudderStack → GA4
 * - Analytics: Vercel Analytics for page views and web vitals
 *
 * REFERENCES:
 *   - components/PageTracker.jsx for page view tracking
 *   - lib/analytics.js for RudderStack integration
 *   - https://vercel.com/docs/analytics
 */
export default function AppProviders({ children }) {
  return (
    <>
      {children}

      {/* Vercel Analytics - automatic page views & web vitals */}
      <Analytics />

      {/* RudderStack page tracking → GA4 */}
      <Suspense fallback={null}>
        <PageTracker />
      </Suspense>

      <Toaster
        position="top-right"
        richColors
        closeButton
        expand
        toastOptions={{
          duration: 4000,
          style: {
            borderRadius: "16px",
            border: "1px solid rgba(0,0,0,0.06)",
          },
        }}
      />
    </>
  );
}
