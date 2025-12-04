'use client';

/**
 * AI Insights Panel
 * =================
 *
 * WHAT: Displays AI-generated insights about performance drops and opportunities.
 *
 * WHY: Provides quick, actionable insights without requiring manual analysis.
 *
 * UPDATED: Now uses lightweight /qa/insights endpoint (no visual generation).
 *
 * REFERENCES:
 *   - lib/api.js (fetchInsights)
 *   - backend/app/routers/qa.py (POST /qa/insights)
 */

import { useEffect, useState, useCallback } from "react";
import { Sparkles, AlertTriangle, Zap, Loader2, RefreshCw } from "lucide-react";
import { fetchInsights } from "@/lib/api";

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

export default function AiInsightsPanel({ workspaceId, timeframe, metricsData }) {
    const [insights, setInsights] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const timeStr = getTimeString(timeframe);

    // Fetch insights
    const fetchAllInsights = useCallback(async () => {
        if (!workspaceId) return;

        setLoading(true);
        setError(null);

        const questions = [
            { question: `What is my biggest performance drop ${timeStr}?`, type: 'warning' },
            { question: `What is my best performing area ${timeStr}?`, type: 'opportunity' }
        ];

        try {
            const results = await Promise.all(
                questions.map(async ({ question, type }) => {
                    try {
                        const result = await fetchInsights({
                            workspaceId,
                            question,
                            metricsData: metricsData || null
                        });
                        return { type, text: result.answer, error: null };
                    } catch (err) {
                        console.error(`[AiInsightsPanel] Failed to fetch insight:`, err);
                        return { type, text: null, error: err.message };
                    }
                })
            );

            // Filter out failed results
            const validInsights = results.filter(r => r.text && !r.error);
            setInsights(validInsights);

            // Check if all failed
            if (validInsights.length === 0 && results.some(r => r.error)) {
                setError(results.find(r => r.error)?.error || 'Failed to load insights');
            }
        } catch (err) {
            console.error('[AiInsightsPanel] Fetch failed:', err);
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, [workspaceId, timeStr, metricsData]);

    // Fetch on mount and when dependencies change
    useEffect(() => {
        fetchAllInsights();
    }, [fetchAllInsights]);

    if (loading) {
        return (
            <div className="lg:col-span-1 flex flex-col gap-4">
                <div className="flex items-center gap-2 mb-1">
                    <Sparkles className="w-4 h-4 text-purple-500" />
                    <h3 className="text-sm font-medium text-slate-700">Insights</h3>
                    <span className="text-[10px] px-1.5 py-0.5 bg-rose-100 text-rose-600 rounded-full font-medium ml-1">Live Analysis</span>
                    <Loader2 className="w-3 h-3 text-purple-400 animate-spin ml-auto" />
                </div>
                <div className="glass-panel p-5 rounded-[20px] h-32 animate-pulse bg-slate-100/50"></div>
                <div className="glass-panel p-5 rounded-[20px] h-32 animate-pulse bg-slate-100/50"></div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="lg:col-span-1 flex flex-col gap-4">
                <div className="flex items-center gap-2 mb-1">
                    <Sparkles className="w-4 h-4 text-purple-500" />
                    <h3 className="text-sm font-medium text-slate-700">Insights</h3>
                    <span className="text-[10px] px-1.5 py-0.5 bg-rose-100 text-rose-600 rounded-full font-medium ml-1">Live Analysis</span>
                    <button
                        onClick={fetchAllInsights}
                        className="ml-auto p-1 hover:bg-slate-100 rounded transition-colors"
                        title="Retry"
                    >
                        <RefreshCw className="w-3 h-3 text-slate-400" />
                    </button>
                </div>
                <div className="glass-panel p-5 rounded-[20px] text-slate-500 text-sm text-center">
                    Unable to load insights. Click refresh to try again.
                </div>
            </div>
        );
    }

    if (insights.length === 0) {
        return (
            <div className="lg:col-span-1 flex flex-col gap-4">
                <div className="flex items-center gap-2 mb-1">
                    <Sparkles className="w-4 h-4 text-purple-500" />
                    <h3 className="text-sm font-medium text-slate-700">Insights</h3>
                    <span className="text-[10px] px-1.5 py-0.5 bg-rose-100 text-rose-600 rounded-full font-medium ml-1">Live Analysis</span>
                    <button
                        onClick={fetchAllInsights}
                        className="ml-auto p-1 hover:bg-slate-100 rounded transition-colors"
                        title="Refresh insights"
                    >
                        <RefreshCw className="w-3 h-3 text-slate-400" />
                    </button>
                </div>
                <div className="glass-panel p-5 rounded-[20px] text-slate-400 text-sm text-center">
                    No insights generated.
                </div>
            </div>
        );
    }

    return (
        <div className="lg:col-span-1 flex flex-col gap-4">
            <div className="flex items-center gap-2 mb-1">
                <Sparkles className="w-4 h-4 text-purple-500" />
                <h3 className="text-sm font-medium text-slate-700">Insights</h3>
                <span className="text-[10px] px-1.5 py-0.5 bg-rose-100 text-rose-600 rounded-full font-medium ml-1">Live Analysis</span>
                <button
                    onClick={fetchAllInsights}
                    className="ml-auto p-1 hover:bg-slate-100 rounded transition-colors"
                    title="Refresh insights"
                >
                    <RefreshCw className="w-3 h-3 text-slate-400" />
                </button>
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
