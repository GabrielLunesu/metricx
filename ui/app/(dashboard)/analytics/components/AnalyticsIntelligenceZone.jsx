/**
 * Analytics Intelligence Zone
 * ===========================
 *
 * WHAT: AI-generated insights panel for the analytics page.
 *
 * WHY: Provides quick, actionable insights without manual analysis.
 *
 * REFERENCES:
 *   - lib/api.js (fetchInsights)
 *   - backend/app/routers/qa.py (POST /qa/insights)
 */
"use client";
import { useEffect, useState } from "react";
import { fetchInsights } from "@/lib/api";
import { renderMarkdownLite } from "@/lib/markdown";
import { Zap, Sparkles, RefreshCw, Loader2 } from "lucide-react";

export default function AnalyticsIntelligenceZone({
    workspaceId,
    selectedProvider,
    timeFilters,
    campaignId,
    campaignName
}) {
    const [insight, setInsight] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const fetchInsight = async () => {
        if (!workspaceId) return;

        setLoading(true);
        setError(null);

        // Generate a prompt for the AI to give actionable insights
        const providerText = selectedProvider === 'all' ? 'all platforms' : selectedProvider;
        const campaignText = campaignName ? ` for campaign "${campaignName}"` : '';
        const question = `Analyze performance for ${providerText}${campaignText} over the last ${timeFilters.rangeDays} days. Identify 1 critical warning (e.g. budget leak, high CPA), 1 scaling opportunity (e.g. high ROAS creative), and 1 general observation. Format as bullet points.`;

        try {
            const result = await fetchInsights({ workspaceId, question });
            setInsight(result.answer);
        } catch (err) {
            console.error('[AnalyticsIntelligenceZone] Failed:', err);
            setError(err.message);
            setInsight(null);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchInsight();
    }, [workspaceId, selectedProvider, timeFilters.type, timeFilters.rangeDays, timeFilters.customStart, timeFilters.customEnd, campaignId, campaignName]);

    return (
        <div className="xl:col-span-1 flex flex-col gap-4 h-full">
            <div className="flex justify-between items-center">
                <h3 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                    <Zap className="w-4 h-4 text-yellow-500 fill-current" />
                    Insights
                </h3>
                <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 bg-red-100 text-red-600 rounded-full text-[10px] font-bold animate-pulse">Live Analysis</span>
                    {loading && <Loader2 className="w-3 h-3 text-cyan-500 animate-spin" />}
                    {!loading && (
                        <button
                            onClick={fetchInsight}
                            className="p-1 hover:bg-slate-100 rounded transition-colors"
                            title="Refresh insights"
                        >
                            <RefreshCw className="w-3 h-3 text-slate-400" />
                        </button>
                    )}
                </div>
            </div>

            {/* Insights Scroll Container */}
            <div className="flex-1 flex flex-col gap-3 overflow-y-auto pr-1 max-h-[450px] no-scrollbar">

                {loading && !insight ? (
                    <div className="glass-panel p-8 rounded-2xl flex flex-col items-center justify-center gap-3 text-center h-full">
                        <div className="w-8 h-8 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin"></div>
                        <p className="text-xs text-slate-400">AI is analyzing your data...</p>
                    </div>
                ) : error ? (
                    <div className="glass-panel p-4 rounded-2xl text-center">
                        <p className="text-xs text-slate-400">Unable to load insights. Click refresh to try again.</p>
                    </div>
                ) : insight ? (
                    <div className="glass-panel p-4 rounded-2xl border-l-4 border-l-violet-400 relative hover:bg-white/80 transition-all group">
                        <div className="flex gap-3">
                            <div className="mt-1 min-w-[24px]">
                                <div className="w-6 h-6 rounded-full bg-violet-100 flex items-center justify-center">
                                    <Sparkles className="w-3.5 h-3.5 text-violet-600" />
                                </div>
                            </div>
                            <div>
                                <p className="text-xs font-medium text-slate-700 leading-relaxed mb-2">
                                    <span className="font-bold text-slate-900">AI Analysis:</span>
                                </p>
                                <div
                                    className="text-xs text-slate-600 leading-relaxed prose prose-sm max-w-none"
                                    dangerouslySetInnerHTML={{ __html: renderMarkdownLite(insight) }}
                                />
                            </div>
                        </div>
                    </div>
                ) : (
                    <div className="glass-panel p-4 rounded-2xl text-center">
                        <p className="text-xs text-slate-400">No insights generated.</p>
                    </div>
                )}

            </div>
        </div>
    );
}
