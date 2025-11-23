'use client';

import { useEffect, useState } from "react";
import { Sparkles, AlertTriangle, Zap } from "lucide-react";
import { fetchQA } from "@/lib/api";

export default function AiInsightsPanel({ workspaceId, timeframe }) {
    const [insights, setInsights] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!workspaceId) return;

        let mounted = true;

        const loadData = async () => {
            setLoading(true);
            setError(null);
            try {
                let timeStr = "last 7 days";
                switch (timeframe) {
                    case 'today': timeStr = "today"; break;
                    case 'yesterday': timeStr = "yesterday"; break;
                    case 'last_7_days': timeStr = "last 7 days"; break;
                    case 'last_30_days': timeStr = "last 30 days"; break;
                }

                // Parallel fetch for 2 distinct insights
                const [res1, res2] = await Promise.all([
                    fetchQA({ workspaceId, question: `What is my biggest performance drop ${timeStr}?` }),
                    fetchQA({ workspaceId, question: `What is my best performing area ${timeStr}?` })
                ]);

                if (!mounted) return;

                const newInsights = [];

                if (res1 && res1.answer) {
                    newInsights.push({
                        type: 'warning',
                        text: res1.answer,

                    });
                }

                if (res2 && res2.answer) {
                    newInsights.push({
                        type: 'opportunity',
                        text: res2.answer,

                    });
                }

                setInsights(newInsights);
            } catch (err) {
                console.error("Failed to fetch AI Insights:", err);
                if (mounted) {
                    setError(err.message);
                }
            } finally {
                if (mounted) {
                    setLoading(false);
                }
            }
        };

        loadData();

        return () => { mounted = false; };
    }, [workspaceId, timeframe]);

    if (loading) {
        return (
            <div className="lg:col-span-1 flex flex-col gap-4">
                <div className="flex items-center gap-2 mb-1">
                    <Sparkles className="w-4 h-4 text-purple-500" />
                    <h3 className="text-sm font-medium text-slate-700">AI Insights</h3>
                </div>
                <div className="glass-panel p-5 rounded-[20px] h-32 animate-pulse"></div>
                <div className="glass-panel p-5 rounded-[20px] h-32 animate-pulse"></div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="lg:col-span-1 flex flex-col gap-4">
                <div className="flex items-center gap-2 mb-1">
                    <Sparkles className="w-4 h-4 text-purple-500" />
                    <h3 className="text-sm font-medium text-slate-700">AI Insights</h3>
                </div>
                <div className="glass-panel p-5 rounded-[20px] text-red-500 text-sm text-center">
                    Failed to load insights: {error}
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
