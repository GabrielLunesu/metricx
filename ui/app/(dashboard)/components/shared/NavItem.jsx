'use client'

import { Lock } from "lucide-react";

/**
 * NavItem - Reusable navigation item with glassmorphism effects
 * Features:
 * - Glassmorphic hover effects
 * - Smooth transitions and scale animations
 * - Tooltip on hover
 * - Active state styling
 * - Locked state for free tier (shows lock icon, prevents navigation)
 *
 * REFERENCES:
 *   - Free tier gating: docs-arch/living-docs/BILLING.md
 */
export default function NavItem({ href, label, icon: Icon, isActive, isLocked, onLockedClick }) {
    const handleClick = (e) => {
        if (isLocked) {
            e.preventDefault();
            if (onLockedClick) {
                onLockedClick(label);
            }
        }
    };

    return (
        <div className="group relative flex justify-center w-full">
            {/* Glow effect on hover - dimmed when locked */}
            <div className={`absolute inset-0 bg-gradient-to-r from-cyan-400/20 to-blue-400/20 blur-md opacity-0 group-hover:opacity-100 transition-opacity rounded-full ${isLocked ? 'from-slate-300/20 to-slate-400/20' : ''}`}></div>

            <a
                href={isLocked ? "#" : href}
                onClick={handleClick}
                className={`relative p-3 rounded-xl transition-all duration-300 group-hover:scale-110 ${isLocked
                        ? 'text-slate-300 cursor-not-allowed'
                        : isActive
                            ? 'text-cyan-600 bg-cyan-50/50 ring-1 ring-cyan-100 shadow-inner'
                            : 'text-slate-400 hover:text-cyan-600 hover:bg-white/60'
                    }`}
            >
                <Icon className="w-5 h-5" />
                {isLocked && (
                    <div className="absolute -top-1 -right-1 w-4 h-4 bg-amber-100 rounded-full flex items-center justify-center ring-2 ring-white">
                        <Lock className="w-2.5 h-2.5 text-amber-600" />
                    </div>
                )}
            </a>

            {/* Tooltip - shows "Pro" badge when locked */}
            <div className="absolute left-16 top-2 px-3 py-1 glass-panel rounded-lg text-[10px] font-medium text-slate-600 opacity-0 group-hover:opacity-100 transition-all duration-300 translate-x-2 group-hover:translate-x-0 pointer-events-none whitespace-nowrap z-50 flex items-center gap-1.5">
                {label}
                {isLocked && (
                    <span className="px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded text-[8px] font-bold">PRO</span>
                )}
            </div>
        </div>
    );
}
