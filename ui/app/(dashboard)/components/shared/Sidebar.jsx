'use client'

import { usePathname } from "next/navigation";
import Link from "next/link";
import { LayoutDashboard, BarChart2, Sparkles, Wallet, Layers, Settings, User } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { currentUser, logout } from "../../../../lib/auth";
import features from "../../../../lib/features";
import { fetchWorkspaceInfo, fetchWorkspaces, switchWorkspace } from "../../../../lib/api";
import NavItem from "./NavItem";
import LogoMark from "./LogoMark";
import ProfileAvatar from "./ProfileAvatar";

export default function Sidebar() {
    const pathname = usePathname();
    const [user, setUser] = useState(null);
    const [workspace, setWorkspace] = useState(null);
    const [workspaces, setWorkspaces] = useState([]);
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

            // Fetch all workspaces
            fetchWorkspaces()
                .then((data) => mounted && setWorkspaces(data.workspaces || []))
                .catch((err) => console.error("Failed to fetch workspaces:", err));
        });

        return () => {
            mounted = false;
        };
    }, []);

    const handleSwitchWorkspace = async (workspaceId) => {
        if (workspaceId === workspace?.id) return;
        try {
            await switchWorkspace(workspaceId);
            window.location.reload(); // Reload to refresh context
        } catch (err) {
            console.error("Failed to switch workspace:", err);
        }
    };

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
                            <button className="w-full text-left px-3 py-2 rounded-lg text-sm text-slate-500 hover:text-slate-800 hover:bg-slate-50 transition-colors flex items-center gap-2">
                                <span className="text-lg leading-none">+</span>
                                Create Workspace
                            </button>
                        </div>
                    </div>
                </div>

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
                                <div className="absolute left-full bottom-0 ml-4 bg-white shadow-lg rounded-xl border border-slate-100 px-3 py-2 text-sm whitespace-nowrap z-50">
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
