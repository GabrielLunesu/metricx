// Dashboard-scoped layout. Provides the shell (sidebar + content area).
"use client";
import { Sidebar, AuroraBackground } from "./components/shared";
import FooterDashboard from "../../components/FooterDashboard";
import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { currentUser } from "../../lib/auth";
import { AnimatePresence, motion } from "framer-motion";


export default function DashboardLayout({ children }) {
  const [authed, setAuthed] = useState(null);
  const router = useRouter();
  const pathname = usePathname();
  const immersive = pathname === "/canvas";

  useEffect(() => {
    let mounted = true;
    currentUser().then((u) => {
      if (!mounted) return;
      const isAuthed = Boolean(u);
      setAuthed(isAuthed);

      // Redirect to login if not authenticated
      if (!isAuthed) {
        router.push("/login");
      }
    });
    return () => {
      mounted = false;
    };
  }, [router]);

  // Show loading state while checking auth
  if (authed === null) {
    return (
      <div className="min-h-screen grid place-items-center p-6 aurora-bg">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-slate-600">Loading...</p>
        </div>
      </div>
    );
  }

  const isCopilot = pathname === "/copilot";

  // Don't render dashboard if not authenticated (will redirect)
  if (!authed) {
    return null;
  }

  const contentClass = immersive || isCopilot ? "w-full h-full" : "max-w-[1600px] mx-auto p-4 md:p-8 space-y-8";

  return (
    <div className="min-h-screen w-full aurora-bg relative overflow-hidden text-slate-800 font-sans antialiased selection:bg-cyan-100 selection:text-cyan-900">

      {/* AdNavi Aurora Layer™ */}
      <AuroraBackground />

      {/* Dashboard Shell */}
      <div className={`flex h-screen overflow-hidden ${immersive ? "" : ""}`}>
        {/* Sidebar */}
        {!immersive && <Sidebar />}

        {/* Main Content - Add left padding when sidebar is visible */}
        <main className={`flex-1 h-full ${!isCopilot ? 'overflow-y-auto' : 'overflow-hidden'} overflow-x-hidden relative ${immersive || isCopilot ? "p-0" : "md:pl-[90px]"}`}>
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
                {!immersive && !isCopilot && <div className="mt-12"><FooterDashboard /></div>}
              </motion.div>
            </AnimatePresence>
          </div>
        </main>
      </div>
    </div>
  );
}
