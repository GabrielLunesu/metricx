/**
 * Sidebar navigation component.
 *
 * WHAT: Main navigation sidebar for the dashboard
 * WHY: Users need consistent navigation across all pages
 *
 * CHANGES (2025-12-22):
 *   - Replaced Clerk UserButton with custom avatar popover
 *   - Added Profile button → /settings?tab=profile
 *   - Added Logout button using Clerk signOut
 *
 * CHANGES (2025-12-17):
 *   - Added free tier gating with lock icons on pro-only features
 *   - Added UpgradeModal for locked feature clicks
 *
 * CHANGES (2025-12-10):
 *   - Fixed workspace detection to use is_active field from API
 *   - Added toast notifications for switch errors
 *
 * CHANGES (2025-12-09):
 *   - Migrated from custom auth to Clerk authentication
 *   - Replaced custom logout with Clerk's UserButton
 *
 * CHANGES (2025-12-02):
 *   - Removed standalone Attribution nav item (moved under Analytics)
 *   - Attribution is now accessed via Analytics page unlock widget
 *
 * REFERENCES:
 *   - docs/living-docs/FRONTEND_REFACTOR_PLAN.md
 *   - docs-arch/living-docs/BILLING.md (free tier gating)
 *   - https://clerk.com/docs/components/user/user-button
 */
'use client'

import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { LayoutDashboard, BarChart2, Sparkles, Wallet, Layers, Settings, User, LogOut } from "lucide-react";
import { useEffect, useState } from "react";
import { useUser, useClerk } from "@clerk/nextjs";
import { toast } from "sonner";
import { Popover, PopoverContent, PopoverTrigger } from "../../../../components/ui/popover";
import { Button } from "../../../../components/ui/button";
import { fetchWorkspaces, switchWorkspace } from "../../../../lib/api";
import { getBillingStatus } from "../../../../lib/workspace";
import NavItem from "./NavItem";
import { UpgradeModal } from "../../../../components/UpgradeModal";


export default function Sidebar() {
    const pathname = usePathname();
    const router = useRouter();
    const { user } = useUser();
    const { signOut } = useClerk();
    const [workspace, setWorkspace] = useState(null);
    const [workspaces, setWorkspaces] = useState([]);
    const [billingTier, setBillingTier] = useState(null);
    const [upgradeModal, setUpgradeModal] = useState({ open: false, feature: null });
    const [userMenuOpen, setUserMenuOpen] = useState(false);

    useEffect(() => {
        let mounted = true;

        const init = async () => {
            try {
                // Fetch workspaces and billing status in parallel
                const [wsData, billingData] = await Promise.all([
                    fetchWorkspaces(),
                    getBillingStatus(),
                ]);
                if (!mounted) return;

                const list = wsData.workspaces || [];
                setWorkspaces(list);

                // Set current workspace (first one is active by default)
                if (list.length > 0) {
                    // Find active workspace or default to first
                    const active = list.find(w => w.is_active) || list[0];
                    setWorkspace(active);
                }

                // Set billing tier for feature gating
                if (billingData?.billing?.billing_tier) {
                    setBillingTier(billingData.billing.billing_tier);
                }
            } catch (err) {
                console.error("Sidebar init failed:", err);
            }
        };

        init();

        return () => {
            mounted = false;
        };
    }, []);

    const handleSwitchWorkspace = async (workspaceId) => {
        if (workspaceId === workspace?.id) return;
        try {
            await switchWorkspace(workspaceId);
            toast.success("Workspace switched");
            window.location.reload(); // Reload to refresh context
        } catch (err) {
            console.error("Failed to switch workspace:", err);
            toast.error("Failed to switch workspace");
        }
    };

    // Navigation items - Attribution removed (now accessed via Analytics page)
    // WHY: Ad analytics first, attribution second (only for Shopify users)
    // requiresPaid: true = locked for free tier users
    const navItems = [
        { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, active: pathname === "/dashboard", requiresPaid: false },
        { href: "/analytics", label: "Analytics", icon: BarChart2, active: pathname?.startsWith("/analytics"), requiresPaid: true },
        { href: "/copilot", label: "Copilot AI", icon: Sparkles, active: pathname?.startsWith('/copilot'), requiresPaid: true },
        { href: "/finance", label: "Finance", icon: Wallet, active: pathname === "/finance", requiresPaid: true },
        { href: "/campaigns", label: "Campaigns", icon: Layers, active: pathname?.startsWith('/campaigns'), requiresPaid: true },
    ];

    // Handler for locked nav item clicks
    const handleLockedClick = (featureLabel) => {
        setUpgradeModal({ open: true, feature: featureLabel });
    };







    return (
        <>
            <aside className="hidden md:flex fixed left-6 top-6 bottom-6 w-[72px] flex-col items-center py-8 glass-panel rounded-[24px] z-50 justify-between transition-all duration-300 hover:border-cyan-200/50">
                {/* Logo / Workspace Switcher */}
                <div className="relative group/ws">
                    <button
                        className="w-10 h-10 flex items-center justify-center rounded-xl bg-gradient-to-br from-slate-800 to-slate-900 text-white shadow-xl shadow-slate-300/50 mb-8 cursor-pointer relative overflow-hidden transition-transform active:scale-95"
                    >
                        {/* Shimmer effect */}
                        <div className="absolute inset-0 bg-gradient-to-tr from-transparent via-white/20 to-transparent rotate-45 translate-y-full group-hover/ws:-translate-y-full transition-transform duration-700"></div>

                        <span className="font-bold text-xs tracking-tighter relative z-10">
                            {workspace?.name?.charAt(0)?.toUpperCase() || "AN"}
                        </span>

                        {/* Dropdown Indicator */}
                        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-0 h-0 border-l-[4px] border-l-transparent border-r-[4px] border-r-transparent border-b-[4px] border-b-white/30 mb-1"></div>
                    </button>

                    {/* Dropdown Menu */}
                    <div className="absolute left-full top-0 ml-4 w-64 bg-white rounded-2xl shadow-xl border border-slate-100 p-2 opacity-0 invisible group-hover/ws:opacity-100 group-hover/ws:visible transition-all duration-200 -translate-x-2 group-hover/ws:translate-x-0 z-50">
                        <div className="px-3 py-2 border-b border-slate-50 mb-1">
                            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Switch Workspace</p>
                        </div>

                        <div className="max-h-64 overflow-y-auto space-y-1">
                            {workspaces.map((ws) => (
                                <button
                                    key={ws.id}
                                    onClick={() => handleSwitchWorkspace(ws.id)}
                                    className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors flex items-center justify-between ${ws.id === workspace?.id
                                        ? "bg-cyan-50 text-cyan-700 font-medium"
                                        : "text-slate-600 hover:bg-slate-50"
                                        }`}
                                >
                                    <span className="truncate">{ws.name}</span>
                                    {ws.id === workspace?.id && (
                                        <div className="w-1.5 h-1.5 rounded-full bg-cyan-500"></div>
                                    )}
                                </button>
                            ))}
                        </div>

                        <div className="mt-2 pt-2 border-t border-slate-50">
                            <Link
                                href="/settings?tab=workspaces"
                                className="w-full text-left px-3 py-2 rounded-lg text-sm text-slate-500 hover:text-slate-800 hover:bg-slate-50 transition-colors flex items-center gap-2"
                            >
                                <Settings className="w-4 h-4" />
                                Workspace Settings
                            </Link>
                        </div>
                    </div>
                </div>

                {/* Nav */}
                <nav className="flex flex-col gap-6 w-full items-center">
                    {navItems.map((item) => {
                        const isLocked = item.requiresPaid && billingTier === 'free';
                        return (
                            <NavItem
                                key={item.href}
                                href={item.href}
                                label={item.label}
                                icon={item.icon}
                                isActive={item.active}
                                isLocked={isLocked}
                                onLockedClick={handleLockedClick}
                            />
                        );
                    })}
                </nav>

                {/* Bottom */}
                <div className="flex flex-col gap-6 items-center">
                    <Link
                        href="/settings"
                        className={`p-3 rounded-xl transition-all duration-500 ${pathname === "/settings"
                            ? 'text-cyan-600 bg-cyan-50/50 ring-1 ring-cyan-100'
                            : 'text-slate-400 hover:text-slate-700 hover:rotate-90'
                            }`}
                    >
                        <Settings className="w-5 h-5" />
                    </Link>

                    {/* User Profile Menu */}
                    <Popover open={userMenuOpen} onOpenChange={setUserMenuOpen}>
                        <PopoverTrigger asChild>
                            <button className="w-8 h-8 rounded-full ring-2 ring-offset-2 ring-cyan-200/50 hover:ring-cyan-300 transition-all overflow-hidden bg-slate-100 flex items-center justify-center">
                                {user?.imageUrl ? (
                                    <img src={user.imageUrl} alt="Profile" className="w-full h-full object-cover" />
                                ) : (
                                    <User className="w-4 h-4 text-slate-400" />
                                )}
                            </button>
                        </PopoverTrigger>
                        <PopoverContent side="right" align="end" className="z-[100] w-auto p-2 bg-white border border-slate-200 shadow-lg">
                            <div className="flex gap-2">
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="flex items-center gap-2"
                                    onClick={() => {
                                        setUserMenuOpen(false);
                                        router.push('/settings?tab=profile');
                                    }}
                                >
                                    <User className="w-4 h-4" />
                                    Profile
                                </Button>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="flex items-center gap-2 text-red-600 hover:text-red-700 hover:bg-red-50"
                                    onClick={() => signOut({ redirectUrl: '/' })}
                                >
                                    <LogOut className="w-4 h-4" />
                                    Logout
                                </Button>
                            </div>
                        </PopoverContent>
                    </Popover>
                </div>
            </aside>

            {/* Mobile Bottom Nav (Glass Pebbles) */}
            <nav className="md:hidden fixed bottom-4 left-4 right-4 bg-white/80 backdrop-blur-2xl rounded-2xl shadow-[0_10px_40px_-10px_rgba(0,0,0,0.1)] border border-white/50 p-2 flex justify-around items-center z-[60] h-[72px]">
                <Link
                    href="/dashboard"
                    className={`flex flex-col items-center justify-center w-12 h-12 rounded-xl ${pathname === "/dashboard" ? "text-cyan-600 bg-cyan-50" : "text-slate-400 hover:bg-slate-50 transition-colors"
                        }`}
                >
                    <LayoutDashboard className="w-5 h-5" />
                </Link>
                <Link
                    href="/analytics"
                    className={`flex flex-col items-center justify-center w-12 h-12 rounded-xl ${pathname === "/analytics" ? "text-cyan-600 bg-cyan-50" : "text-slate-400 hover:bg-slate-50 transition-colors"
                        }`}
                >
                    <BarChart2 className="w-5 h-5" />
                </Link>

                {/* Center Action */}
                <Link
                    href="/copilot"
                    className="relative -translate-y-4 group active:scale-95 transition-transform duration-150"
                    aria-label="Open Copilot"
                >
                    <div className="w-12 h-12 rounded-full bg-gradient-to-tr from-cyan-400 via-sky-500 to-blue-700 flex items-center justify-center text-white shadow-[0_20px_45px_-12px_rgba(14,165,233,0.7)] ring-4 ring-white/70 backdrop-blur-md relative overflow-hidden">
                        <div className="absolute inset-0 bg-white/15 blur-xl scale-100 animate-pulse" />
                        <div className="absolute inset-0 rounded-full border border-white/30 opacity-70 animate-[ping_2.5s_ease-in-out_infinite]" />
                        <Sparkles className="w-7 h-7 relative z-10 drop-shadow-[0_0_12px_rgba(255,255,255,0.85)]" />
                    </div>
                </Link>

                <Link
                    href="/finance"
                    className={`flex flex-col items-center justify-center w-12 h-12 rounded-xl ${pathname === "/finance" ? "text-cyan-600 bg-cyan-50" : "text-slate-400 hover:bg-slate-50 transition-colors"
                        }`}
                >
                    <Wallet className="w-5 h-5" />
                </Link>
                <Link
                    href="/settings"
                    className={`flex flex-col items-center justify-center w-12 h-12 rounded-xl ${pathname === "/settings" ? "text-cyan-600 bg-cyan-50" : "text-slate-400 hover:bg-slate-50 transition-colors"
                        }`}
                >
                    <User className="w-5 h-5" />
                </Link>
            </nav>

            {/* Upgrade Modal for locked features */}
            <UpgradeModal
                open={upgradeModal.open}
                onClose={() => setUpgradeModal({ open: false, feature: null })}
                feature={upgradeModal.feature}
            />
        </>
    );
}
