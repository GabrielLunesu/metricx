/**
 * AI Financial Summary
 * 
 * WHAT: AI-generated financial insight via QA system
 * WHY: Natural language summary and recommendations
 * REFERENCES: lib/api.js:fetchQA
 */

"use client";
import { useState, useEffect } from "react";
import { Sparkles, TrendingUp } from "lucide-react";
import { fetchQA } from "@/lib/api";
import { renderMarkdownLite } from "@/lib/markdown";

export default function AIFinancialSummary({ workspaceId, selectedPeriod }) {
  const [insight, setInsight] = useState(null);
  const [loading, setLoading] = useState(false);

  // Auto-generate insight on mount or period change
  useEffect(() => {
    if (workspaceId && selectedPeriod) {
      generateInsight();
    }
  }, [workspaceId, selectedPeriod]); // Removed hasGenerated from dependencies to trigger on period change

  const generateInsight = async () => {
    setLoading(true);
    try {
      // Calculate date range
      const startDate = new Date(selectedPeriod.year, selectedPeriod.month - 1, 1);

      // Check if it's the current month
      const now = new Date();
      const isCurrentMonth = selectedPeriod.year === now.getFullYear() &&
        selectedPeriod.month === (now.getMonth() + 1);

      let endDate;
      if (isCurrentMonth) {
        // If current month, use today's date
        endDate = now;
      } else {
        // Otherwise, use the last day of the selected month
        endDate = new Date(selectedPeriod.year, selectedPeriod.month, 0);
      }

      // Format dates as readable strings
      const formatDate = (date) => {
        const monthNames = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"];
        return `${monthNames[date.getMonth()]} ${date.getDate()}`;
      };

      const question = `Workspace performance breakdown from ${formatDate(startDate)} to ${formatDate(endDate)} 2025`;

      // Log for debugging
      console.log('Finance AI Question:', question);

      const response = await fetchQA({
        workspaceId,
        question
      });

      console.log('Finance AI Response:', response);

      setInsight(response.answer);
    } catch (err) {
      console.error('Failed to generate insight:', err);
      setInsight('Unable to generate insight. Please try again.');
    } finally {
      setLoading(false);
    }
  };

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
        </div>

        {loading && !insight && (
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
            <span className="text-xs text-slate-500 ml-2">Analyzing financial data...</span>
          </div>
        )}

        {!insight && !loading && (
          <p className="text-xs text-slate-600 leading-relaxed">
            Get a natural-language breakdown of how your spend, revenue, and margins are evolving this period.
          </p>
        )}

        {insight && (
          <div className="mt-2">
            <div
              className="text-xs text-slate-600 leading-relaxed"
              dangerouslySetInnerHTML={{ __html: renderMarkdownLite(insight) }}
            />
          </div>
        )}
      </div>


      {/* ask copilot for scenarios button */}
      {/* <button
        onClick={generateInsight}
        disabled={loading}
        className="mt-6 w-full py-2.5 rounded-lg bg-white border border-blue-200 text-blue-600 text-xs font-semibold hover:bg-blue-50 hover:border-blue-300 transition-all shadow-sm disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2"
      >
        <TrendingUp className="w-3.5 h-3.5" />
        {insight ? "Ask Copilot for scenarios" : "Generate financial insight"}
      </button> */}
    </div>
  );
}
