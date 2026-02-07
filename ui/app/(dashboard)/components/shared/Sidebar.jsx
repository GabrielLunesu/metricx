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
import { useEffect, useState, useCallback } from "react";
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

            {/* Mobile FAB + Sheet Navigation */}
            <MobileNav
                pathname={pathname}
                navItems={navItems}
                billingTier={billingTier}
                onLockedClick={handleLockedClick}
                workspace={workspace}
            />

            {/* Upgrade Modal for locked features */}
            <UpgradeModal
                open={upgradeModal.open}
                onClose={() => setUpgradeModal({ open: false, feature: null })}
                feature={upgradeModal.feature}
            />
        </>
    );
}

/**
 * MobileNav - Horizontally scrollable bottom icon dock
 *
 * WHAT: Fixed bottom bar with scrollable icon buttons
 * WHY: Native-feeling navigation always visible on mobile, scrollable for nice UX
 */
function MobileNav({ pathname, navItems, billingTier, onLockedClick }) {
    const router = useRouter();

    // All navigation items for the dock
    const dockItems = [
        ...navItems,
        { href: "/settings", label: "Settings", icon: Settings, active: pathname === "/settings", requiresPaid: false },
    ];

    const handleNavClick = (item) => {
        const isLocked = item.requiresPaid && billingTier === 'free';
        if (isLocked) {
            onLockedClick(item.label);
            return;
        }
        router.push(item.href);
    };

    return (
        <nav className="md:hidden fixed bottom-0 left-0 right-0 z-[70] mobile-dock-enter safe-area-bottom">
            <div className="bg-white border-t border-neutral-200/60 shadow-[0_-2px_10px_rgba(0,0,0,0.04)]">
                <div className="flex items-center overflow-x-auto no-scrollbar px-3 h-14 gap-1">
                    {dockItems.map((item) => {
                        const Icon = item.icon;
                        const isActive = item.active;
                        const isLocked = item.requiresPaid && billingTier === 'free';

                        return (
                            <button
                                key={item.href}
                                onClick={() => handleNavClick(item)}
                                aria-label={item.label}
                                className="relative flex-shrink-0 flex items-center justify-center w-12 h-10 transition-transform duration-150 active:scale-90"
                            >
                                <div className={`
                                    flex items-center justify-center w-10 h-10 rounded-2xl transition-all duration-150
                                    ${isActive
                                        ? 'bg-neutral-900 text-white'
                                        : 'text-neutral-400'
                                    }
                                `}>
                                    <Icon className="w-[18px] h-[18px]" />
                                </div>
                                {isLocked && (
                                    <div className="absolute top-0.5 right-0.5 w-1.5 h-1.5 rounded-full bg-amber-400" />
                                )}
                            </button>
                        );
                    })}
                </div>
            </div>
        </nav>
    );
}
