'use client';

/**
 * HeroHeader - Centered hero section for the dashboard
 * 
 * WHAT: Displays personalized greeting, live updates badge, and subtitle
 * WHY: Welcome users with a clean, focused header that sets the tone
 * 
 * CHANGES (2025-12-30):
 *   - New centered layout design
 *   - Added Live Updates badge with green pulsing dot
 *   - New typography: large hero text with tracking-tighter
 *   - Removed inline search bar (moved to separate component)
 *
 * REFERENCES:
 *   - Metricx v3.0 design system
 */

import { useMemo } from "react";

/**
 * Format relative time (e.g., "2 min ago", "1 hour ago")
 */
function formatRelativeTime(isoString) {
    if (!isoString) return null;

    try {
        const dateStr = isoString.includes('Z') || isoString.includes('+') ? isoString : isoString + 'Z';
        const date = new Date(dateStr);
        const now = new Date();
        const diffMs = now - date;
        const diffSec = Math.floor(diffMs / 1000);
        const diffMin = Math.floor(diffSec / 60);
        const diffHours = Math.floor(diffMin / 60);
        const diffDays = Math.floor(diffHours / 24);

        if (diffSec < 60) return "just now";
        if (diffMin < 60) return `${diffMin} min ago`;
        if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
        if (diffDays === 1) return "yesterday";
        return `${diffDays} days ago`;
    } catch {
        return null;
    }
}

export default function HeroHeader({ user, lastSyncedAt, actions }) {
    const name = user?.name || "there";
    const displayName = name.charAt(0).toUpperCase() + name.slice(1);

    const relativeTime = useMemo(() => formatRelativeTime(lastSyncedAt), [lastSyncedAt]);

    return (
        <header className="flex flex-col items-center justify-center mb-8 max-w-4xl mx-auto text-center">
            {/* Live Updates Badge */}
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/50 border border-neutral-200/60 mb-6 backdrop-blur-sm">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></div>
                <span className="text-[10px] font-semibold text-neutral-500 uppercase tracking-widest">
                    {relativeTime ? `Updated ${relativeTime}` : 'Live'}
                </span>
            </div>

            {/* Hero Title */}
            <h1 className="text-5xl lg:text-7xl font-medium text-neutral-900 tracking-tighter mb-4 text-glow">
                Let's crush it, {displayName}
            </h1>

            {/* Subtitle */}
            <p className="text-xl text-neutral-400 font-light tracking-tight">
                Your daily performance overview is ready.
            </p>

            {/* Timeframe selector (subtle, positioned below subtitle) */}
            {actions && (
                <div className="mt-6">
                    {actions}
                </div>
            )}
        </header>
    );
}
