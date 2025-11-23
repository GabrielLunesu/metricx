'use client'

import { usePathname } from "next/navigation";
import { LayoutDashboard, BarChart2, Sparkles, Wallet, Layers, Settings } from "lucide-react";
import { useEffect, useState } from "react";
import { currentUser, logout } from "../../../../lib/auth";
import features from "../../../../lib/features";
import { fetchWorkspaceInfo } from "../../../../lib/api";

export default function Sidebar() {
  const pathname = usePathname();
  const [user, setUser] = useState(null);
  const [workspace, setWorkspace] = useState(null);

  useEffect(() => {
    let mounted = true;

    // Fetch current user
    currentUser().then((u) => {
      if (!mounted) return;
      setUser(u);

      // Fetch workspace info if user has workspace_id
      if (u?.workspace_id) {
        fetchWorkspaceInfo(u.workspace_id)
          .then((ws) => mounted && setWorkspace(ws))
          .catch((err) => console.error("Failed to fetch workspace info:", err));
      }
    });

    return () => {
      mounted = false;
    };
  }, []);

  const navItems = [
    { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, active: pathname === "/dashboard" },
    { href: "/analytics", label: "Analytics", icon: BarChart2, active: pathname === "/analytics" },
    { href: "/copilot", label: "Copilot AI", icon: Sparkles, active: pathname?.startsWith('/copilot') },
    { href: "/finance", label: "Finance", icon: Wallet, active: pathname === "/finance" },
    { href: "/campaigns", label: "Campaigns", icon: Layers, active: pathname?.startsWith('/campaigns') },
    // Canvas feature flag check
    ...(features.canvas ? [{ href: "/canvas", label: "Canvas", icon: Layers, active: pathname === "/canvas" }] : []),
  ];

  return (
    <aside className="hidden md:flex flex-col w-[72px] h-full glass-panel z-50 items-center py-8 border-r border-white/50">
      {/* Logo Mark */}
      <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-cyan-400 to-blue-500 mb-10 shadow-glow-sm flex items-center justify-center text-white font-bold text-sm tracking-tight">
        {workspace?.name?.charAt(0)?.toUpperCase() || "A"}
      </div>

      {/* Nav Items */}
      <nav className="flex-1 flex flex-col gap-6 w-full items-center">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = item.active;

          return (
            <a
              key={item.href}
              href={item.href}
              className={`group relative p-3 rounded-xl transition-all ${isActive
                  ? 'text-cyan-600 bg-cyan-50/50 shadow-sm hover:scale-105'
                  : 'text-slate-400 hover:text-cyan-600 hover:bg-white/60'
                }`}
            >
              <Icon className="w-5 h-5" />
              <span className="absolute left-16 bg-slate-800 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50">
                {item.label}
              </span>
            </a>
          );
        })}
      </nav>

      {/* Settings / Logout */}
      <div className="mt-auto flex flex-col gap-4 items-center">
        <a
          href="/settings"
          className={`p-3 rounded-xl transition-all ${pathname === "/settings"
              ? 'text-cyan-600 bg-cyan-50/50 shadow-sm'
              : 'text-slate-400 hover:text-slate-600 hover:bg-white/60'
            }`}
        >
          <Settings className="w-5 h-5" />
        </a>

        {/* User Avatar / Logout Trigger */}
        {user && (
          <form action={async () => { await logout(); location.href = "/login"; }}>
            <button
              type="submit"
              className="w-8 h-8 rounded-full bg-gradient-to-br from-slate-200 to-slate-300 flex items-center justify-center text-slate-600 text-xs font-bold hover:ring-2 hover:ring-cyan-400 transition-all"
              title="Logout"
            >
              {user.email?.charAt(0)?.toUpperCase() || "U"}
            </button>
          </form>
        )}
      </div>
    </aside>
  );
}
