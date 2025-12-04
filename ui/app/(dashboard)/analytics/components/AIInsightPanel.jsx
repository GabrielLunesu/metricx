'use client';

/**
 * AI Insight Panel (Analytics)
 * ============================
 *
 * WHAT: Displays AI-generated analytics insight.
 *
 * WHY: Provides quick, actionable summary without manual analysis.
 *
 * REFERENCES:
 *   - lib/api.js (fetchInsights)
 *   - backend/app/routers/qa.py (POST /qa/insights)
 */

import { useEffect, useState, useCallback } from "react";
import { Sparkles, Loader2, RefreshCw } from "lucide-react";
import { fetchInsights } from "@/lib/api";

function getTimeString(timeframe) {
    switch (timeframe) {
        case 'today': return "today";
        case 'yesterday': return "yesterday";
        case 'last_7_days': return "last 7 days";
        case 'last_30_days': return "last 30 days";
        default: return "this period";
    }
}

export default function AIInsightPanel({ workspaceId, timeframe = 'last_7_days' }) {
    const [insight, setInsight] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const timeStr = getTimeString(timeframe);

    const fetchInsight = useCallback(async () => {
        if (!workspaceId) return;

        setLoading(true);
        setError(null);

        try {
            const result = await fetchInsights({
                workspaceId,
                question: `Give me a brief performance summary for ${timeStr}. Focus on spend, revenue, ROAS, and any notable trends.`
            });
            setInsight(result.answer);
        } catch (err) {
            console.error('[AIInsightPanel] Failed:', err);
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, [workspaceId, timeStr]);

    useEffect(() => {
        fetchInsight();
    }, [fetchInsight]);

    return (
        <div className="mx-8 mb-8">
            <div className="glass-card rounded-3xl p-8 border border-cyan-200/60 shadow-lg relative overflow-hidden">
                <div className="absolute -right-20 -top-20 w-40 h-40 bg-cyan-400 rounded-full blur-[80px] opacity-10 aura-glow"></div>

                <div className="flex items-start gap-4 relative z-10">
                    <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-cyan-400 to-cyan-600 flex items-center justify-center flex-shrink-0 shadow-lg shadow-cyan-500/30">
                        <Sparkles className="w-6 h-6 text-white" strokeWidth={1.5} />
                    </div>

                    <div className="flex-1">
                        <div className="flex items-center gap-2 mb-3">
                            <h3 className="text-xl font-semibold gradient-text">metricx Insight</h3>
                            {loading && <Loader2 className="w-4 h-4 text-cyan-500 animate-spin" />}
                            {!loading && (
                                <button
                                    onClick={fetchInsight}
                                    className="p-1 hover:bg-cyan-100 rounded transition-colors"
                                    title="Refresh insight"
                                >
                                    <RefreshCw className="w-3 h-3 text-cyan-500" />
                                </button>
                            )}
                        </div>

                        {loading && (
                            <div className="h-16 animate-pulse bg-slate-100 rounded-lg"></div>
                        )}

                        {error && (
                            <p className="text-base font-light text-neutral-500 leading-relaxed">
                                Unable to generate insight. Click refresh to try again.
                            </p>
                        )}

                        {!loading && !error && insight && (
                            <p className="text-base font-light text-neutral-700 leading-relaxed">
                                {insight}
                            </p>
                        )}

                        {!loading && !error && !insight && !workspaceId && (
                            <p className="text-base font-light text-neutral-500 leading-relaxed">
                                Connect your workspace to see AI insights.
                            </p>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
