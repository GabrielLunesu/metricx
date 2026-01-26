/**
 * Sidebar navigation component.
 *
 * WHAT: Main navigation sidebar for the dashboard
 * WHY: Users need consistent navigation across all pages
 *
 * CHANGES (2025-12-30):
 *   - New design: responsive width (w-20 lg:w-72)
 *   - New styling: soft glass background, neutral colors
 *   - Navigation: black active state, show labels on lg screens
 *   - User profile: avatar + name + plan badge on lg screens
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
 * REFERENCES:
 *   - docs/living-docs/FRONTEND_REFACTOR_PLAN.md
 *   - docs-arch/living-docs/BILLING.md (free tier gating)
 */
'use client'

import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { LayoutDashboard, BarChart2, Sparkles, Wallet, Layers, Settings, User, LogOut, Users, ChevronDown, Bot } from "lucide-react";
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
        { href: "/agents", label: "Agents", icon: Bot, active: pathname?.startsWith('/agents'), requiresPaid: true },
        { href: "/finance", label: "Finance", icon: Wallet, active: pathname === "/finance", requiresPaid: true },
        { href: "/campaigns", label: "Campaigns", icon: Layers, active: pathname?.startsWith('/campaigns'), requiresPaid: true },
    ];

    // Handler for locked nav item clicks
    const handleLockedClick = (featureLabel) => {
        setUpgradeModal({ open: true, feature: featureLabel });
    };







    // Get plan display name
    const getPlanName = () => {
        if (!billingTier) return null;
        if (billingTier === 'free') return 'Free Plan';
        if (billingTier === 'pro') return 'Pro Plan';
        return billingTier.charAt(0).toUpperCase() + billingTier.slice(1);
    };

    return (
        <>
            {/* Desktop Sidebar - Responsive width */}
            <aside className="hidden md:flex fixed left-0 top-0 bottom-0 w-20 lg:w-72 sidebar-glass flex-col py-6 px-3 lg:px-5 z-50 justify-between transition-all duration-300">
                {/* Top Section: Logo + Workspace Selector */}
                <div className="space-y-5">
                    {/* Logo */}
                    <div className="px-2 lg:px-3">
                        {/* Full logo for expanded state */}
                        <Image
                            src="/logo.png"
                            alt="Metricx"
                            width={160}
                            height={42}
                            className="hidden lg:block h-12 w-auto"
                            priority
                        />
                        {/* Icon only for collapsed state */}
                        <div className="lg:hidden w-11 h-11 flex items-center justify-center rounded-xl bg-neutral-900 text-white mx-auto">
                            <span className="font-semibold text-lg">M</span>
                        </div>
                    </div>

                    {/* Workspace Selector */}
                    <div className="relative group/ws">
                        <button className="w-full flex items-center gap-3 px-2 lg:px-3 py-2.5 rounded-xl hover:bg-white/60 transition-all duration-200">
                            <div className="w-9 h-9 rounded-lg bg-neutral-100 flex items-center justify-center text-neutral-700 text-sm font-semibold flex-shrink-0 border border-neutral-200/50">
                                {workspace?.name?.charAt(0)?.toUpperCase() || 'W'}
                            </div>
                            <div className="hidden lg:flex flex-1 items-center justify-between min-w-0">
                                <div className="flex flex-col items-start min-w-0">
                                    <span className="text-[11px] text-neutral-400 uppercase tracking-wider">Workspace</span>
                                    <span className="text-sm font-medium text-neutral-800 truncate">
                                        {workspace?.name || 'Select workspace'}
                                    </span>
                                </div>
                                <ChevronDown className="w-4 h-4 text-neutral-400 flex-shrink-0" />
                            </div>
                        </button>

                        {/* Dropdown Menu */}
                        <div className="absolute left-full top-0 ml-2 lg:left-0 lg:top-full lg:ml-0 lg:mt-1 w-64 bg-white rounded-xl shadow-xl border border-neutral-100 p-2 opacity-0 invisible group-hover/ws:opacity-100 group-hover/ws:visible transition-all duration-200 z-50">
                            <div className="px-3 py-2 border-b border-neutral-50 mb-1">
                                <p className="text-xs font-medium text-neutral-400 uppercase tracking-wider">Switch Workspace</p>
                            </div>

                            <div className="max-h-64 overflow-y-auto space-y-1">
                                {workspaces.map((ws) => (
                                    <button
                                        key={ws.id}
                                        onClick={() => handleSwitchWorkspace(ws.id)}
                                        className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors flex items-center justify-between ${ws.id === workspace?.id
                                            ? "bg-neutral-100 text-neutral-900 font-medium"
                                            : "text-neutral-600 hover:bg-neutral-50"
                                            }`}
                                    >
                                        <span className="truncate">{ws.name}</span>
                                        {ws.id === workspace?.id && (
                                            <div className="w-1.5 h-1.5 rounded-full bg-neutral-900"></div>
                                        )}
                                    </button>
                                ))}
                            </div>

                            <div className="mt-2 pt-2 border-t border-neutral-50">
                                <Link
                                    href="/settings?tab=workspaces"
                                    className="w-full text-left px-3 py-2 rounded-lg text-sm text-neutral-500 hover:text-neutral-800 hover:bg-neutral-50 transition-colors flex items-center gap-2"
                                >
                                    <Settings className="w-4 h-4" />
                                    Workspace Settings
                                </Link>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Nav */}
                <nav className="flex flex-col gap-1 flex-1 mt-4 px-1">
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

                {/* Bottom - User Profile */}
                <div className="flex flex-col gap-2 pt-6 border-t border-neutral-100">
                    <Popover open={userMenuOpen} onOpenChange={setUserMenuOpen}>
                        <PopoverTrigger asChild>
                            <button className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-white/60 transition-all duration-300">
                                <div className="w-9 h-9 rounded-full bg-neutral-200 border border-white flex items-center justify-center overflow-hidden">
                                    {user?.imageUrl ? (
                                        <img src={user.imageUrl} alt="Profile" className="w-full h-full object-cover" />
                                    ) : (
                                        <span className="text-neutral-500 text-xs font-medium">
                                            {user?.firstName?.charAt(0)?.toUpperCase() || 'U'}
                                        </span>
                                    )}
                                </div>
                                <div className="hidden lg:block text-left">
                                    <div className="text-sm font-medium text-neutral-900">
                                        {user?.firstName || 'User'}
                                    </div>
                                    <div className="text-xs text-neutral-400">
                                        {getPlanName()}
                                    </div>
                                </div>
                            </button>
                        </PopoverTrigger>
                        <PopoverContent side="right" align="end" className="z-[100] w-48 p-2 bg-white border border-neutral-200 shadow-lg rounded-xl">
                            <div className="flex flex-col gap-1">
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="w-full justify-start flex items-center gap-2 text-neutral-700 hover:text-neutral-900 hover:bg-neutral-50"
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
                                    className="w-full justify-start flex items-center gap-2 text-neutral-700 hover:text-neutral-900 hover:bg-neutral-50"
                                    onClick={() => {
                                        setUserMenuOpen(false);
                                        router.push('/settings');
                                    }}
                                >
                                    <Settings className="w-4 h-4" />
                                    Settings
                                </Button>
                                <div className="h-px bg-neutral-100 my-1" />
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="w-full justify-start flex items-center gap-2 text-red-600 hover:text-red-700 hover:bg-red-50"
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

            {/* Mobile Bottom Nav - New design */}
            <nav className="md:hidden fixed bottom-4 left-4 right-4 bg-white/80 backdrop-blur-2xl rounded-2xl shadow-[0_10px_40px_-10px_rgba(0,0,0,0.08)] border border-neutral-200/40 p-2 flex justify-around items-center z-[60] h-[68px]">
                <Link
                    href="/dashboard"
                    className={`flex flex-col items-center justify-center w-12 h-12 rounded-xl transition-all duration-300 ${pathname === "/dashboard"
                        ? "text-white bg-neutral-900 shadow-lg shadow-neutral-900/20"
                        : "text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900"
                        }`}
                >
                    <LayoutDashboard className="w-5 h-5" />
                </Link>
                <Link
                    href="/analytics"
                    className={`flex flex-col items-center justify-center w-12 h-12 rounded-xl transition-all duration-300 ${pathname?.startsWith("/analytics")
                        ? "text-white bg-neutral-900 shadow-lg shadow-neutral-900/20"
                        : "text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900"
                        }`}
                >
                    <BarChart2 className="w-5 h-5" />
                </Link>

                {/* Center Action - Copilot */}
                <Link
                    href="/copilot"
                    className="relative -translate-y-3 group active:scale-95 transition-transform duration-150"
                    aria-label="Open Copilot"
                >
                    <div className="w-14 h-14 rounded-full bg-neutral-900 flex items-center justify-center text-white shadow-xl shadow-neutral-900/30 ring-4 ring-white relative overflow-hidden">
                        <Sparkles className="w-6 h-6 relative z-10" />
                    </div>
                </Link>

                <Link
                    href="/finance"
                    className={`flex flex-col items-center justify-center w-12 h-12 rounded-xl transition-all duration-300 ${pathname === "/finance"
                        ? "text-white bg-neutral-900 shadow-lg shadow-neutral-900/20"
                        : "text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900"
                        }`}
                >
                    <Wallet className="w-5 h-5" />
                </Link>
                <Link
                    href="/settings"
                    className={`flex flex-col items-center justify-center w-12 h-12 rounded-xl transition-all duration-300 ${pathname === "/settings"
                        ? "text-white bg-neutral-900 shadow-lg shadow-neutral-900/20"
                        : "text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900"
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
