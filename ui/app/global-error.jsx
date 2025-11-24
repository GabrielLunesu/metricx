"use client";
import { useEffect } from "react";
import Link from "next/link";
import { AlertTriangle, RefreshCw } from "lucide-react";

/**
 * Global safety net for React render errors.
 * WHAT: Prevents the white screen of death by showing a friendly fallback.
 * WHY: Gives users a path to recover (retry) or navigate elsewhere.
 */
export default function GlobalError({ error, reset }) {
  useEffect(() => {
    console.error("Global render error", error);
  }, [error]);

  return (
    <html>
      <body className="min-h-screen bg-gradient-to-b from-white via-cyan-50 to-white text-neutral-900 flex items-center justify-center px-6">
        <div className="max-w-xl w-full bg-white/80 backdrop-blur border border-cyan-100 shadow-xl rounded-3xl p-8 space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-cyan-100 text-cyan-700 flex items-center justify-center">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs uppercase font-semibold text-cyan-700 tracking-wide">System status</p>
              <h1 className="text-xl font-bold">Something went wrong</h1>
            </div>
          </div>

          <p className="text-sm text-neutral-600 leading-relaxed">
            We hit an unexpected error while rendering this screen. Your data is safe. You can retry the page or jump back to the dashboard.
          </p>

          <div className="flex flex-wrap gap-3">
            <button
              onClick={reset}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-cyan-600 text-white text-sm font-semibold hover:bg-cyan-700 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              Try again
            </button>
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-neutral-200 text-neutral-800 text-sm font-semibold hover:bg-neutral-50 transition-colors"
            >
              Return to dashboard
            </Link>
          </div>

          <p className="text-[11px] text-neutral-400">
            If this keeps happening, please reach out to support so we can take a closer look.
          </p>
        </div>
      </body>
    </html>
  );
}
