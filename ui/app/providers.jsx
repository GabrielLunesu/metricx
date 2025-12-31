"use client";

import { Suspense } from "react";
import { Toaster } from "sonner";
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
 *
 * REFERENCES:
 *   - components/PageTracker.jsx for page view tracking
 *   - lib/analytics.js for RudderStack integration
 */
export default function AppProviders({ children }) {
  return (
    <>
      {children}

      {/* Page view tracking - wrapped in Suspense for useSearchParams */}
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
