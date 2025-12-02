'use client';

/**
 * Platform Spend Mix
 * ==================
 *
 * WHAT: Displays spend breakdown by ad platform (Google, Meta, etc.)
 *
 * WHY: Quick visual of where ad budget is being allocated.
 *
 * UPDATED: Now uses useQA hook for streaming + caching.
 *
 * REFERENCES:
 *   - hooks/useQA.js (data fetching)
 *   - lib/qaCache.js (caching layer)
 */

import { useMemo } from "react";
import { useQA } from "@/hooks/useQA";

// Helper to normalize provider labels (e.g., "ProviderEnum.meta" → "meta")
const normalizeProviderLabel = (label) => {
    if (!label) return label;
    const lowered = String(label).toLowerCase();
    if (lowered.includes("providerenum")) {
        return lowered.split(".").pop();
    }
    if (lowered.includes(".")) {
        return lowered.split(".").pop();
    }
    return lowered;
};

// Helper to get time string from timeframe
function getTimeString(timeframe) {
    switch (timeframe) {
        case 'today': return "today";
        case 'yesterday': return "yesterday";
        case 'last_7_days': return "last 7 days";
        case 'last_30_days': return "last 30 days";
        default: return "last 7 days";
    }
}

export default function PlatformSpendMix({ workspaceId, timeframe }) {
    const timeStr = getTimeString(timeframe);
    const question = `What is my spend by provider ${timeStr}?`;

    // Use the QA hook (streaming + caching)
    const { data, loading, error } = useQA({
        workspaceId,
        question,
        enabled: !!workspaceId,
        cacheTTL: 5 * 60 * 1000  // 5 minutes
    });

    // Process data into chart format
    const chartData = useMemo(() => {
        if (!data?.data?.breakdown) return [];

        const breakdown = data.data.breakdown;
        const total = breakdown.reduce((sum, item) => sum + item.value, 0);

        return breakdown.map(item => ({
            provider: normalizeProviderLabel(item.label),
            value: item.value,
            pct: total > 0 ? (item.value / total) * 100 : 0
        }));
    }, [data]);

    if (loading) {
        return (
            <div className="glass-panel p-6 rounded-3xl mb-2 h-[200px] flex items-center justify-center animate-pulse">
                <div className="w-full h-full bg-slate-100/50 rounded-xl"></div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="glass-panel p-6 rounded-3xl mb-2 h-[200px] flex items-center justify-center">
                <p className="text-red-500 text-sm">Failed to load: {error}</p>
            </div>
        );
    }

    if (!chartData || chartData.length === 0) {
        return (
            <div className="glass-panel p-6 rounded-3xl mb-2 h-[200px] flex items-center justify-center">
                <p className="text-slate-400 text-sm">No spend data available</p>
            </div>
        );
    }

    return (
        <div className="glass-panel p-6 rounded-3xl mb-2 h-[200px] flex items-center justify-center">
            <div className="flex items-end gap-12 h-32 w-full px-8 justify-center">
                {chartData.map((item) => {
                    const isGoogle = item.provider.toLowerCase().includes('google');
                    const colorClass = isGoogle
                        ? "from-blue-500 to-cyan-400 shadow-[0_0_15px_rgba(6,182,212,0.4)]"
                        : "from-blue-600 to-indigo-500 shadow-[0_0_15px_rgba(99,102,241,0.4)]";

                    return (
                        <div key={item.provider} className="flex flex-col items-center gap-3 group w-24">
                            <div className="w-full bg-slate-100 rounded-t-xl relative h-32 overflow-hidden shadow-inner">
                                <div
                                    className={`absolute bottom-0 left-0 w-full bg-gradient-to-t ${colorClass} transition-all duration-700`}
                                    style={{ height: `${Math.max(item.pct, 5)}%` }}
                                >
                                    <div className="absolute top-0 w-full h-[2px] bg-white/50"></div>
                                </div>
                            </div>
                            <span className="text-xs font-bold text-slate-500 tracking-wide text-center truncate w-full capitalize">
                                {item.provider} ({Math.round(item.pct)}%)
                            </span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
