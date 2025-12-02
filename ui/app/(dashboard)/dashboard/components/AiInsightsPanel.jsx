'use client';

/**
 * AI Insights Panel
 * =================
 *
 * WHAT: Displays AI-generated insights about performance drops and opportunities.
 *
 * WHY: Provides quick, actionable insights without requiring manual analysis.
 *
 * UPDATED: Now uses useQAMultiple hook for streaming + caching.
 *
 * REFERENCES:
 *   - hooks/useQA.js (data fetching)
 *   - lib/qaCache.js (caching layer)
 */

import { useMemo } from "react";
import { Sparkles, AlertTriangle, Zap, Loader2 } from "lucide-react";
import { useQAMultiple } from "@/hooks/useQA";

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

export default function AiInsightsPanel({ workspaceId, timeframe }) {
    // Build queries for parallel fetch
    const timeStr = getTimeString(timeframe);

    const queries = useMemo(() => {
        if (!workspaceId) return [];
        return [
            { workspaceId, question: `What is my biggest performance drop ${timeStr}?` },
            { workspaceId, question: `What is my best performing area ${timeStr}?` }
        ];
    }, [workspaceId, timeStr]);

    // Use the multi-query hook (streaming + caching)
    const { results, loading, errors } = useQAMultiple(queries, {
        enabled: !!workspaceId,
        cacheTTL: 5 * 60 * 1000  // 5 minutes
    });

    // Process results into insights
    const insights = useMemo(() => {
        if (!results || results.length === 0) return [];

        const newInsights = [];

        // Result 1: Performance drop (warning)
        if (results[0]?.answer) {
            newInsights.push({
                type: 'warning',
                text: results[0].answer
            });
        }

        // Result 2: Best performing (opportunity)
        if (results[1]?.answer) {
            newInsights.push({
                type: 'opportunity',
                text: results[1].answer
            });
        }

        return newInsights;
    }, [results]);

    // Check for any errors
    const hasError = errors.some(e => e !== null);
    const errorMessage = errors.find(e => e !== null);

    if (loading) {
        return (
            <div className="lg:col-span-1 flex flex-col gap-4">
                <div className="flex items-center gap-2 mb-1">
                    <Sparkles className="w-4 h-4 text-purple-500" />
                    <h3 className="text-sm font-medium text-slate-700">AI Insights</h3>
                    <Loader2 className="w-3 h-3 text-purple-400 animate-spin ml-auto" />
                </div>
                <div className="glass-panel p-5 rounded-[20px] h-32 animate-pulse bg-slate-100/50"></div>
                <div className="glass-panel p-5 rounded-[20px] h-32 animate-pulse bg-slate-100/50"></div>
            </div>
        );
    }

    if (hasError) {
        return (
            <div className="lg:col-span-1 flex flex-col gap-4">
                <div className="flex items-center gap-2 mb-1">
                    <Sparkles className="w-4 h-4 text-purple-500" />
                    <h3 className="text-sm font-medium text-slate-700">AI Insights</h3>
                </div>
                <div className="glass-panel p-5 rounded-[20px] text-red-500 text-sm text-center">
                    Failed to load insights: {errorMessage}
                </div>
            </div>
        );
    }

    if (insights.length === 0) {
        return (
            <div className="lg:col-span-1 flex flex-col gap-4">
                <div className="flex items-center gap-2 mb-1">
                    <Sparkles className="w-4 h-4 text-purple-500" />
                    <h3 className="text-sm font-medium text-slate-700">AI Insights</h3>
                </div>
                <div className="glass-panel p-5 rounded-[20px] text-slate-400 text-sm text-center">
                    No insights available for this period.
                </div>
            </div>
        );
    }

    return (
        <div className="lg:col-span-1 flex flex-col gap-4">
            <div className="flex items-center gap-2 mb-1">
                <Sparkles className="w-4 h-4 text-purple-500" />
                <h3 className="text-sm font-medium text-slate-700">AI Insights</h3>
            </div>

            {insights.map((insight, index) => (
                <div
                    key={index}
                    className={`glass-panel p-5 rounded-[20px] border-l-4 ${insight.type === 'warning' ? 'border-l-amber-400' : 'border-l-emerald-400'} relative hover:bg-white/80 transition-colors cursor-pointer group animate-slide-in`}
                    style={{ animationDelay: `${(index + 1) * 0.1}s` }}
                >
                    {insight.type === 'warning' && (
                        <div className="absolute top-4 right-4">
                            <div className="w-1.5 h-1.5 bg-amber-400 rounded-full "></div>
                        </div>
                    )}
                    <div className="flex gap-3">
                        <div className={`${insight.type === 'warning' ? 'bg-amber-100' : 'bg-emerald-100'} p-2 rounded-lg h-fit`}>
                            {insight.type === 'warning' ? (
                                <AlertTriangle className="w-4 h-4 text-amber-600" />
                            ) : (
                                <Zap className="w-4 h-4 text-emerald-600" />
                            )}
                        </div>
                        <div>
                            <p className="text-xs font-medium text-slate-800 leading-relaxed">
                                {insight.text}
                            </p>

                        </div>
                    </div>
                </div>
            ))}
        </div>
    );
}
