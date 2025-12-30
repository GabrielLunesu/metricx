'use client'

import Link from "next/link";
import { Lock } from "lucide-react";

/**
 * NavItem - Reusable navigation item with new Metricx v3.0 design
 * 
 * WHAT: Navigation item component for the sidebar
 * WHY: Consistent navigation styling across the app
 * 
 * FEATURES:
 *   - Black background when active, neutral-500 when inactive
 *   - Shows label text on lg: breakpoint
 *   - Locked state for free tier (shows lock icon, prevents navigation)
 *   - Smooth transitions and hover effects
 *
 * CHANGES (2025-12-30):
 *   - New design: black active state, neutral colors
 *   - Responsive: icon-only on small, icon+label on lg
 *   - Updated hover effects
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
        <Link
            href={isLocked ? "#" : href}
            onClick={handleClick}
            className={`
                group flex items-center gap-4 px-4 py-3.5 rounded-xl transition-all duration-300
                ${isLocked
                    ? 'text-neutral-300 cursor-not-allowed'
                    : isActive
                        ? 'bg-neutral-900 text-white shadow-xl shadow-neutral-900/10'
                        : 'text-neutral-500 hover:bg-white/60 hover:text-neutral-900'
                }
            `}
        >
            <div className="relative">
                <Icon className="w-5 h-5" />
                {isLocked && (
                    <div className="absolute -top-1.5 -right-1.5 w-4 h-4 bg-amber-100 rounded-full flex items-center justify-center ring-2 ring-white">
                        <Lock className="w-2.5 h-2.5 text-amber-600" />
                    </div>
                )}
            </div>
            <span className="hidden lg:block text-sm font-medium">{label}</span>
            
            {/* Pro badge for locked items - visible on lg */}
            {isLocked && (
                <span className="hidden lg:inline-flex ml-auto px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded text-[9px] font-bold">
                    PRO
                </span>
            )}
        </Link>
    );
}
