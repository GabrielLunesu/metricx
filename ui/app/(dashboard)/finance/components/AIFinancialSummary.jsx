/**
 * AI Financial Summary
 *
 * WHAT: AI-generated financial insight via lightweight insights endpoint
 * WHY: Natural language summary without visual generation (faster)
 * REFERENCES: lib/api.js:fetchInsights, backend/app/routers/qa.py:POST /qa/insights
 */

"use client";
import { useState, useEffect, useCallback } from "react";
import { Sparkles, RefreshCw, Loader2 } from "lucide-react";
import { fetchInsights } from "@/lib/api";
import { renderMarkdownLite } from "@/lib/markdown";

export default function AIFinancialSummary({ workspaceId, selectedPeriod }) {
  const [insight, setInsight] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const generateInsight = useCallback(async () => {
    if (!workspaceId || !selectedPeriod) return;

    setLoading(true);
    setError(null);

    try {
      // Calculate date range
      const startDate = new Date(selectedPeriod.year, selectedPeriod.month - 1, 1);

      // Check if it's the current month
      const now = new Date();
      const isCurrentMonth = selectedPeriod.year === now.getFullYear() &&
        selectedPeriod.month === (now.getMonth() + 1);

      let endDate;
      if (isCurrentMonth) {
        endDate = now;
      } else {
        endDate = new Date(selectedPeriod.year, selectedPeriod.month, 0);
      }

      // Format dates as readable strings
      const formatDate = (date) => {
        const monthNames = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"];
        return `${monthNames[date.getMonth()]} ${date.getDate()}`;
      };

      const question = `Give me a brief financial summary from ${formatDate(startDate)} to ${formatDate(endDate)} ${selectedPeriod.year}. Focus on spend, revenue, profit margins, and ROAS.`;

      console.log('[AIFinancialSummary] Requesting insight:', question.substring(0, 60) + '...');

      const response = await fetchInsights({
        workspaceId,
        question
      });

      console.log('[AIFinancialSummary] Response received');
      setInsight(response.answer);
    } catch (err) {
      console.error('[AIFinancialSummary] Failed:', err);
      setError(err.message);
      setInsight(null);
    } finally {
      setLoading(false);
    }
  }, [workspaceId, selectedPeriod]);

  // Auto-generate insight on mount or period change
  useEffect(() => {
    generateInsight();
  }, [generateInsight]);

  return (
    <div className="glass-card rounded-xl p-5 border border-blue-100 bg-gradient-to-br from-white to-blue-50/50 flex flex-col justify-between h-full">
      <div>
        <div className="flex items-center gap-2 mb-4">
          <div className="w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center text-blue-600">
            <Sparkles className="w-3.5 h-3.5" />
          </div>
          <h3 className="text-xs font-bold uppercase text-blue-700 tracking-wide">
            Financial Copilot
          </h3>
          {loading && <Loader2 className="w-3 h-3 text-blue-500 animate-spin ml-auto" />}
          {!loading && (
            <button
              onClick={generateInsight}
              className="ml-auto p-1 hover:bg-blue-100 rounded transition-colors"
              title="Refresh insight"
            >
              <RefreshCw className="w-3 h-3 text-blue-500" />
            </button>
          )}
        </div>

        {loading && !insight && (
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
            <span className="text-xs text-slate-500 ml-2">Analyzing financial data...</span>
          </div>
        )}

        {error && (
          <p className="text-xs text-slate-500 leading-relaxed">
            Unable to generate insight. Click refresh to try again.
          </p>
        )}

        {!insight && !loading && !error && (
          <p className="text-xs text-slate-600 leading-relaxed">
            Get a natural-language breakdown of how your spend, revenue, and margins are evolving this period.
          </p>
        )}

        {insight && !loading && (
          <div className="mt-2">
            <div
              className="text-xs text-slate-600 leading-relaxed"
              dangerouslySetInnerHTML={{ __html: renderMarkdownLite(insight) }}
            />
          </div>
        )}
      </div>
    </div>
  );
}
