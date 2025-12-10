/**
 * Dashboard Shell - Client-side layout with sidebar and animations.
 *
 * WHAT: Handles sidebar, route animations, and layout variations
 * WHY: Separated from layout.jsx because this needs client-side hooks (usePathname)
 *
 * Layout Variations:
 * - Normal: Sidebar + scrollable content area
 * - Immersive (/canvas): Full-screen, no sidebar
 * - Copilot (/copilot): Full-height, no overflow scroll
 *
 * REFERENCES:
 *   - ui/app/(dashboard)/layout.jsx (parent server component)
 *   - ui/app/(dashboard)/components/shared/Sidebar.jsx
 */
"use client";

import { Sidebar, AuroraBackground } from "./components/shared";
import FooterDashboard from "../../components/FooterDashboard";
import { usePathname } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";

export default function DashboardShell({ children }) {
  const pathname = usePathname();

  // Route-based layout variations
  const immersive = pathname === "/canvas";
  const isCopilot = pathname === "/copilot";

  const contentClass = immersive || isCopilot
    ? "w-full h-full"
    : "max-w-[1600px] mx-auto p-4 md:p-8 space-y-8";

  return (
    <div className="min-h-screen w-full aurora-bg relative overflow-hidden text-slate-800 font-sans antialiased selection:bg-cyan-100 selection:text-cyan-900">
      {/* metricx Aurora Layer */}
      <AuroraBackground />

      {/* Dashboard Shell */}
      <div className="flex h-screen overflow-hidden">
        {/* Sidebar - hidden in immersive mode */}
        {!immersive && <Sidebar />}

        {/* Main Content */}
        <main
          className={`
            flex-1 h-full overflow-x-hidden relative
            ${!isCopilot ? 'overflow-y-auto' : 'overflow-hidden'}
            ${immersive || isCopilot ? "p-0" : "md:pl-[90px]"}
          `}
        >
          <div className={contentClass}>
            <AnimatePresence mode="wait">
              <motion.div
                key={pathname}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.3, ease: "easeOut" }}
                className="h-full"
              >
                {children}
                {!immersive && !isCopilot && (
                  <div className="mt-12">
                    <FooterDashboard />
                  </div>
                )}
              </motion.div>
            </AnimatePresence>
          </div>
        </main>
      </div>
    </div>
  );
}
