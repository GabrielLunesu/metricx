"use client";
/**
 * AdNaviInsight Component
 * -----------------------
 * WHAT: Displays AI-generated insights for analytics filters
 * WHY: Provides quick, contextual analysis without heavy QA pipeline
 *
 * REFACTORED: Uses fetchInsights (lightweight, text-only) instead of fetchQA
 * (which uses the full LLM pipeline with 30-60s polling).
 *
 * REFERENCES:
 * - ui/lib/api.js (fetchInsights)
 * - backend/app/routers/qa.py (POST /qa/insights)
 */
import { useEffect, useState } from "react";
import { fetchInsights } from "@/lib/api";
import { renderMarkdownLite } from "@/lib/markdown";
import { Sparkles } from "lucide-react";

export default function metricxInsight({
  workspaceId,
  selectedProvider,
  selectedTimeframe,
  rangeDays,
  customStartDate,
  customEndDate
}) {
  const [insight, setInsight] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Generate dynamic question based on selected filters
  const generateQuestion = () => {
    const providerText = selectedProvider === 'all'
      ? 'all platforms'
      : selectedProvider;

    let timeframeText;
    if (selectedTimeframe === '7d') {
      timeframeText = 'last 7 days';
    } else if (selectedTimeframe === '30d') {
      timeframeText = 'last 30 days';
    } else if (customStartDate && customEndDate) {
      timeframeText = `from ${customStartDate} to ${customEndDate}`;
    } else {
      timeframeText = `last ${rangeDays} days`;
    }

    return `Give me a breakdown of ${providerText} for the ${timeframeText}`;
  };

  useEffect(() => {
    if (!workspaceId) return;

    let mounted = true;
    setLoading(true);

    const question = generateQuestion();

    fetchInsights({ workspaceId, question })
      .then((data) => {
        if (!mounted) return;
        setInsight(data);
        setError(null);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to fetch AI insight:', err);
        if (mounted) {
          setError(err.message);
          setLoading(false);
        }
      });

    return () => { mounted = false; };
  }, [workspaceId, selectedProvider, selectedTimeframe, rangeDays, customStartDate, customEndDate]);

  return (
    <div className="px-8 mb-8">
      <div className="glass-card rounded-3xl p-8 border border-neutral-200/60 shadow-lg relative overflow-hidden">
        {/* Glow effect */}
        <div className="absolute -top-10 -right-10 w-40 h-40 bg-cyan-400 rounded-full blur-[100px] opacity-15 pulse-glow-aura"></div>

        {/* Header */}
        <div className="flex items-center gap-3 mb-6 relative z-10">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-cyan-400 to-cyan-600 flex items-center justify-center shadow-lg">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <h3 className="text-lg font-semibold text-neutral-900">metricx Insight</h3>
        </div>

        {/* Insight Content */}
        <div className="relative z-10">
          {loading ? (
            <div className="flex items-center gap-3 py-4">
              <div className="w-6 h-6 border-3 border-cyan-500 border-t-transparent rounded-full animate-spin"></div>
              <p className="text-neutral-500 text-sm">Analyzing your data...</p>
            </div>
          ) : error ? (
            <div className="bg-red-50 border border-red-200 rounded-2xl p-4">
              <p className="text-red-600 text-sm">Failed to generate insight: {error}</p>
            </div>
          ) : insight ? (
            <div className="space-y-4">
              {/* AI Answer */}
              <div className="bg-gradient-to-br from-cyan-50 to-white border border-cyan-200/60 rounded-2xl p-6">
                <div className="text-neutral-800 leading-relaxed" dangerouslySetInnerHTML={{ __html: renderMarkdownLite(insight.answer) }} />
              </div>

              {/* Metadata (optional, can be hidden) */}
              <div className="flex items-center gap-2 text-xs text-neutral-400">
                <Sparkles className="w-3 h-3" />
                <span>Generated using AI analysis</span>
              </div>
            </div>
          ) : (
            <p className="text-neutral-400 text-sm py-4">No insights available</p>
          )}
        </div>
      </div>
    </div>
  );
}

