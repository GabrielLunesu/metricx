'use client'

import { usePathname } from "next/navigation";
import Link from "next/link";
import { LayoutDashboard, BarChart2, Sparkles, Wallet, Layers, Settings, User } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { currentUser, logout } from "../../../../lib/auth";
import features from "../../../../lib/features";
import { fetchWorkspaceInfo } from "../../../../lib/api";
import NavItem from "./NavItem";
import LogoMark from "./LogoMark";
import ProfileAvatar from "./ProfileAvatar";

export default function Sidebar() {
    const pathname = usePathname();
    const [user, setUser] = useState(null);
    const [workspace, setWorkspace] = useState(null);
    const [showLogout, setShowLogout] = useState(false);
    const avatarRef = useRef(null);

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
        // ...(features.canvas ? [{ href: "/canvas", label: "Canvas", icon: Layers, active: pathname === "/canvas" }] : []),
    ];

    const handleLogout = async () => {
        await logout();
        window.location.href = "/login";
    };

    useEffect(() => {
        setShowLogout(false);
    }, [pathname]);

    useEffect(() => {
        const handleClickOutside = (e) => {
            if (avatarRef.current && !avatarRef.current.contains(e.target)) {
                setShowLogout(false);
            }
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    return (
        <>
            <aside className="hidden md:flex fixed left-6 top-6 bottom-6 w-[72px] flex-col items-center py-8 glass-panel rounded-[24px] z-50 justify-between transition-all duration-300 hover:border-cyan-200/50">
                {/* Logo */}
                <LogoMark
                    initial={workspace?.name?.charAt(0)?.toUpperCase() || "AN"}
                    href="/dashboard"
                />

                {/* Nav */}
                <nav className="flex flex-col gap-6 w-full items-center">
                    {navItems.map((item) => (
                        <NavItem
                            key={item.href}
                            href={item.href}
                            label={item.label}
                            icon={item.icon}
                            isActive={item.active}
                        />
                    ))}
                </nav>

                {/* Bottom */}
                <div className="flex flex-col gap-6 items-center">
                    <a
                        href="/settings"
                        className={`p-3 rounded-xl transition-all duration-500 ${pathname === "/settings"
                            ? 'text-cyan-600 bg-cyan-50/50 ring-1 ring-cyan-100'
                            : 'text-slate-400 hover:text-slate-700 hover:rotate-90'
                            }`}
                    >
                        <Settings className="w-5 h-5" />
                    </a>

                    {/* User Avatar / Logout Trigger */}
                    {user && (
                        <div className="relative" ref={avatarRef}>
                            <button
                                type="button"
                                title="Profile"
                                onClick={() => setShowLogout((v) => !v)}
                                className="focus:outline-none"
                            >
                                <ProfileAvatar
                                    initial={user.email?.charAt(0)?.toUpperCase() || "U"}
                                    imageUrl="https://i.pravatar.cc/150?img=11"
                                />
                            </button>
                            {showLogout && (
                                <div className="absolute left-1/2 -translate-x-1/2 -top-14 bg-white shadow-lg rounded-xl border border-slate-100 px-3 py-2 text-sm whitespace-nowrap">
                                    <button
                                        className="text-slate-700 hover:text-red-500 transition-colors"
                                        onClick={(e) => { e.preventDefault(); handleLogout(); }}
                                    >
                                        Logout
                                    </button>
                                </div>
                            )}
                        </div>
                    )}
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
        </>
    );
}
