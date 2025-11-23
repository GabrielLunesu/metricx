// Dashboard-scoped layout. Provides the shell (sidebar + content area).
"use client";
import Sidebar from "./dashboard/components/Sidebar";
import FooterDashboard from "../../components/FooterDashboard";
import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { currentUser } from "../../lib/auth";

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

  // Don't render dashboard if not authenticated (will redirect)
  if (!authed) {
    return null;
  }

  return (
    <div className="min-h-screen w-full aurora-bg relative overflow-hidden text-slate-800 font-sans antialiased selection:bg-cyan-100 selection:text-cyan-900">

      {/* AdNavi Aurora Layer™ (Ambient Background Blobs) */}
      <div className="fixed top-0 left-0 w-full h-full overflow-hidden -z-10 pointer-events-none">
        <div className="absolute top-[-10%] left-[-5%] w-[50vw] h-[50vw] bg-cyan-300/40 rounded-full blur-[100px] animate-breathe"></div>
        <div className="absolute bottom-[-10%] right-[-5%] w-[60vw] h-[60vw] bg-blue-300/40 rounded-full blur-[100px] animate-breathe" style={{ animationDelay: '2s' }}></div>
        <div className="absolute top-[20%] right-[10%] w-[30vw] h-[30vw] bg-teal-200/50 rounded-full blur-[80px] animate-breathe" style={{ animationDelay: '4s' }}></div>
      </div>

      {/* Dashboard Shell */}
      <div className={`flex h-screen overflow-hidden ${immersive ? "" : ""}`}>
        {/* Sidebar */}
        {!immersive && <Sidebar />}

        {/* Main Content */}
        <main className={`flex-1 h-full overflow-y-auto overflow-x-hidden relative ${immersive ? "p-0" : ""}`}>
          <div className={immersive ? "w-full" : "max-w-[1600px] mx-auto p-4 md:p-8 space-y-8"}>
            {children}
            {!immersive && <div className="mt-12"><FooterDashboard /></div>}
          </div>
        </main>
      </div>
    </div>
  );
}
