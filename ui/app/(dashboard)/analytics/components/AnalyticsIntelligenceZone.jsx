"use client";
import { useEffect, useState } from "react";
import { fetchQA } from "@/lib/api";
import { renderMarkdownLite } from "@/lib/markdown";
import { Zap, Sparkles } from "lucide-react";

export default function AnalyticsIntelligenceZone({
    workspaceId,
    selectedProvider,
    timeFilters,
    campaignId, // New prop
    campaignName // New prop
}) {
    const [insight, setInsight] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!workspaceId) return;

        let mounted = true;
        setLoading(true);

        // Generate a prompt for the AI to give actionable insights
        const providerText = selectedProvider === 'all' ? 'all platforms' : selectedProvider;
        const campaignText = campaignName ? ` for campaign "${campaignName}"` : '';
        const question = `Analyze performance for ${providerText}${campaignText} over the last ${timeFilters.rangeDays} days. Identify 1 critical warning (e.g. budget leak, high CPA), 1 scaling opportunity (e.g. high ROAS creative), and 1 general observation. Format as bullet points.`;

        const context = {
            provider: selectedProvider,
            rangeDays: timeFilters.rangeDays,
            campaignId: campaignId || undefined,
            campaignName: campaignName || undefined
        };

        fetchQA({ workspaceId, question, context })
            .then((data) => {
                if (!mounted) return;
                setInsight(data);
                setLoading(false);
            })
            .catch((err) => {
                console.error('Failed to fetch AI insight:', err);
                if (mounted) setLoading(false);
            });

        return () => { mounted = false; };
    }, [workspaceId, selectedProvider, timeFilters.type, timeFilters.rangeDays, timeFilters.customStart, timeFilters.customEnd, campaignId, campaignName]);

    return (
        <div className="xl:col-span-1 flex flex-col gap-4 h-full">
            <div className="flex justify-between items-center">
                <h3 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                    <Zap className="w-4 h-4 text-yellow-500 fill-current" />
                    Insights
                </h3>
                <span className="px-2 py-0.5 bg-red-100 text-red-600 rounded-full text-[10px] font-bold animate-pulse">Live Analysis</span>
            </div>

            {/* Insights Scroll Container */}
            <div className="flex-1 flex flex-col gap-3 overflow-y-auto pr-1 max-h-[450px] no-scrollbar">

                {loading ? (
                    <div className="glass-panel p-8 rounded-2xl flex flex-col items-center justify-center gap-3 text-center h-full">
                        <div className="w-8 h-8 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin"></div>
                        <p className="text-xs text-slate-400">AI is analyzing your data...</p>
                    </div>
                ) : insight ? (
                    <>
                        {/* AI Analysis Card */}
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
                                        dangerouslySetInnerHTML={{ __html: renderMarkdownLite(insight.answer) }}
                                    />
                                </div>
                            </div>
                        </div>

                    </>
                ) : (
                    <div className="glass-panel p-4 rounded-2xl text-center">
                        <p className="text-xs text-slate-400">No insights generated.</p>
                    </div>
                )}

            </div>
        </div>
    );
}
