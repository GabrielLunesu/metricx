"use client";
import { Toaster } from "sonner";

/**
 * Centralized client-side providers.
 * WHY: keeps the root layout lean while enabling toasts and future context (theme, auth).
 */
export default function AppProviders({ children }) {
  return (
    <>
      {children}
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
