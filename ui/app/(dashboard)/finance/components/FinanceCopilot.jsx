"use client";

/**
 * FinanceCopilot - Quick Finance Questions Card
 * 
 * WHAT: Entry point to ask finance-related questions
 * WHY: Provides quick actions and navigates to full Copilot page with context
 * 
 * BEHAVIOR:
 *   - Quick action buttons navigate to /copilot?q={question}
 *   - Input field navigates to /copilot?q={input}
 *   - Shows recent AI insight as preview
 * 
 * REFERENCES:
 *   - Metricx v3.0 design system
 *   - Copilot page: app/(dashboard)/copilot/page.jsx
 */

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Sparkles, Send, TrendingUp, DollarSign, PieChart, Lightbulb, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { getApiBase } from "@/lib/config";

/**
 * Get month name from number
 */
function getMonthName(month) {
  const months = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
  ];
  return months[month - 1] || "";
}

/**
 * Quick action suggestions for finance queries
 */
const QUICK_ACTIONS = [
  {
    icon: TrendingUp,
    label: "Profit trends",
    query: "What are my profit trends this month?",
  },
  {
    icon: PieChart,
    label: "Spend breakdown",
    query: "Break down my ad spend by platform",
  },
  {
    icon: DollarSign,
    label: "ROAS analysis",
    query: "How is my ROAS performing?",
  },
  {
    icon: Lightbulb,
    label: "Recommendations",
    query: "Give me recommendations to improve profitability",
  },
];

export default function FinanceCopilot({
  workspaceId,
  selectedPeriod,
  summary,
}) {
  const router = useRouter();
  const [inputValue, setInputValue] = useState("");
  const [preview, setPreview] = useState(null);
  const [loadingPreview, setLoadingPreview] = useState(false);

  // Fetch a quick insight preview when period changes
  useEffect(() => {
    if (!workspaceId) return;

    const fetchPreview = async () => {
      setLoadingPreview(true);
      try {
        const BASE = getApiBase();
        const res = await fetch(`${BASE}/workspaces/${workspaceId}/finance/insight`, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            month: getMonthName(selectedPeriod.month),
            year: selectedPeriod.year,
          }),
        });

        if (res.ok) {
          const data = await res.json();
          // Truncate to first 2 sentences for preview
          const sentences = data.message.split(/[.!?]+/).filter(Boolean);
          const truncated = sentences.slice(0, 2).join(". ") + (sentences.length > 2 ? "..." : ".");
          setPreview(truncated);
        }
      } catch (err) {
        console.error("Failed to fetch preview:", err);
      } finally {
        setLoadingPreview(false);
      }
    };

    fetchPreview();
  }, [workspaceId, selectedPeriod]);

  const navigateToCopilot = (query) => {
    const encodedQuery = encodeURIComponent(query);
    router.push(`/copilot?q=${encodedQuery}`);
  };

  const handleSubmit = (e) => {
    e?.preventDefault();
    if (!inputValue.trim()) return;
    navigateToCopilot(inputValue.trim());
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="border border-neutral-200 bg-white rounded-xl h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-neutral-100 flex items-center gap-3">
        <div className="w-9 h-9 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center shadow-sm">
          <Sparkles className="w-4 h-4 text-white" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-blue-600">Financial Copilot</h3>
          <p className="text-xs text-neutral-500">Ask anything about your finances</p>
        </div>
      </div>

      {/* Preview Insight */}
      <div className="flex-1 p-5 flex flex-col">
        {loadingPreview ? (
          <div className="space-y-2 mb-4">
            <div className="h-4 w-full bg-neutral-100 rounded animate-pulse" />
            <div className="h-4 w-3/4 bg-neutral-100 rounded animate-pulse" />
          </div>
        ) : preview ? (
          <div className="mb-4">
            <p className="text-sm text-neutral-600 leading-relaxed">{preview}</p>
            <button
              onClick={() => navigateToCopilot(`Give me a detailed financial analysis for ${getMonthName(selectedPeriod.month)} ${selectedPeriod.year}`)}
              className="mt-2 text-xs font-medium text-blue-600 hover:text-blue-700 flex items-center gap-1"
            >
              See full analysis <ArrowRight className="w-3 h-3" />
            </button>
          </div>
        ) : (
          <div className="mb-4 text-center py-4">
            <div className="w-10 h-10 bg-neutral-100 rounded-full flex items-center justify-center mx-auto mb-2">
              <Sparkles className="w-5 h-5 text-neutral-400" />
            </div>
            <p className="text-sm text-neutral-500">Ask a question below</p>
          </div>
        )}

        {/* Quick Actions */}
        <div className="grid grid-cols-2 gap-2 mt-auto">
          {QUICK_ACTIONS.map((action, idx) => (
            <button
              key={idx}
              onClick={() => navigateToCopilot(action.query)}
              className="flex items-center gap-2 px-3 py-2.5 text-xs font-medium text-neutral-600 bg-neutral-50 hover:bg-neutral-100 rounded-lg border border-neutral-200 transition-colors text-left group"
            >
              <action.icon className="w-3.5 h-3.5 text-neutral-400 group-hover:text-blue-500 flex-shrink-0 transition-colors" />
              <span className="truncate">{action.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Input Area */}
      <form onSubmit={handleSubmit} className="p-3 border-t border-neutral-100 bg-neutral-50">
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your finances..."
            className="flex-1 px-3 py-2 text-sm bg-white border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent placeholder:text-neutral-400"
          />
          <Button
            type="submit"
            size="sm"
            disabled={!inputValue.trim()}
            className="h-9 w-9 p-0 bg-neutral-900 hover:bg-neutral-800 text-white rounded-lg disabled:opacity-50"
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </form>
    </div>
  );
}
