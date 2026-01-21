/**
 * ROAS Calculator Component
 *
 * WHAT: Interactive calculator for Return on Ad Spend
 * WHY: High-intent tool page to attract backlinks and conversions
 *
 * Formula: ROAS = Revenue from Ads / Ad Spend
 *
 * @example
 * import { ROASCalculator } from '@/components/tools/ROASCalculator';
 *
 * <ROASCalculator />
 */

"use client";

import { useState, useMemo } from "react";
import { CalculatorInput, CalculatorResult } from "./CalculatorLayout";
import { ArrowRight, TrendingUp, TrendingDown, Minus } from "lucide-react";

/**
 * ROAS Calculator with real-time calculation.
 *
 * @returns {JSX.Element} ROAS calculator
 */
export function ROASCalculator() {
  const [adSpend, setAdSpend] = useState("");
  const [revenue, setRevenue] = useState("");

  // Calculate ROAS
  const result = useMemo(() => {
    const spend = parseFloat(adSpend) || 0;
    const rev = parseFloat(revenue) || 0;

    if (spend === 0) return null;

    const roas = rev / spend;
    const roasPercent = roas * 100;

    // Determine status based on ROAS value
    let status = "neutral";
    let interpretation = "";
    let Icon = Minus;

    if (roas >= 4) {
      status = "success";
      interpretation = "Excellent! Your ads are highly profitable.";
      Icon = TrendingUp;
    } else if (roas >= 2) {
      status = "success";
      interpretation = "Good performance. Room for optimization.";
      Icon = TrendingUp;
    } else if (roas >= 1) {
      status = "warning";
      interpretation = "Breaking even. Consider optimizing your campaigns.";
      Icon = Minus;
    } else {
      status = "error";
      interpretation = "Losing money. Review your ad strategy.";
      Icon = TrendingDown;
    }

    return {
      roas: roas.toFixed(2),
      roasPercent: roasPercent.toFixed(0),
      profit: rev - spend,
      status,
      interpretation,
      Icon,
    };
  }, [adSpend, revenue]);

  return (
    <div className="roas-calculator">
      {/* Inputs */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <CalculatorInput
          label="Ad Spend"
          id="ad-spend"
          value={adSpend}
          onChange={setAdSpend}
          prefix="$"
          placeholder="1000"
          helperText="Total amount spent on advertising"
        />
        <CalculatorInput
          label="Revenue from Ads"
          id="revenue"
          value={revenue}
          onChange={setRevenue}
          prefix="$"
          placeholder="5000"
          helperText="Revenue attributed to your ads"
        />
      </div>

      {/* Calculation Indicator */}
      <div className="flex items-center justify-center gap-4 mb-8 text-slate-400">
        <span className="text-sm">Revenue</span>
        <ArrowRight className="w-4 h-4" />
        <span className="text-sm">÷ Ad Spend</span>
        <ArrowRight className="w-4 h-4" />
        <span className="text-sm font-semibold text-slate-600">ROAS</span>
      </div>

      {/* Results */}
      {result ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <CalculatorResult
            label="Your ROAS"
            value={`${result.roas}x`}
            status={result.status}
            interpretation={result.interpretation}
          />
          <CalculatorResult
            label="As Percentage"
            value={result.roasPercent}
            suffix="%"
            status="neutral"
          />
          <CalculatorResult
            label="Net Profit"
            value={`$${result.profit.toLocaleString()}`}
            status={result.profit >= 0 ? "success" : "error"}
            interpretation={
              result.profit >= 0
                ? "Positive return on investment"
                : "Negative return on investment"
            }
          />
        </div>
      ) : (
        <div className="text-center py-12 text-slate-400">
          <p>Enter your ad spend and revenue to calculate ROAS</p>
        </div>
      )}

      {/* Benchmark Reference */}
      <div className="mt-8 p-4 bg-slate-50 rounded-lg">
        <h3 className="font-semibold text-slate-900 mb-2">ROAS Benchmarks</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-red-500 font-medium">Below 1x</span>
            <p className="text-slate-500">Losing money</p>
          </div>
          <div>
            <span className="text-amber-500 font-medium">1x - 2x</span>
            <p className="text-slate-500">Break-even</p>
          </div>
          <div>
            <span className="text-emerald-500 font-medium">2x - 4x</span>
            <p className="text-slate-500">Good</p>
          </div>
          <div>
            <span className="text-emerald-600 font-medium">4x+</span>
            <p className="text-slate-500">Excellent</p>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * ROAS Calculator page data for use in page component.
 */
export const roasCalculatorData = {
  title: "ROAS Calculator",
  slug: "roas-calculator",
  description:
    "Calculate your Return on Ad Spend (ROAS) instantly. Enter your ad spend and revenue to see your ROAS, profit, and performance benchmarks.",
  howToSteps: [
    {
      name: "Enter your ad spend",
      text: "Enter the total amount you spent on advertising in the Ad Spend field.",
    },
    {
      name: "Enter your revenue",
      text: "Enter the revenue generated from your advertising campaigns in the Revenue field.",
    },
    {
      name: "View your ROAS",
      text: "See your ROAS calculated instantly as both a multiplier (e.g., 5x) and percentage (e.g., 500%).",
    },
  ],
  faqs: [
    {
      question: "What is ROAS?",
      answer:
        "ROAS (Return on Ad Spend) measures the revenue generated for every dollar spent on advertising. A ROAS of 5x means you earn $5 for every $1 spent on ads.",
    },
    {
      question: "What is a good ROAS?",
      answer:
        "A good ROAS varies by industry and business model, but generally: 2x-3x is considered break-even to good, 4x+ is excellent. E-commerce brands typically aim for 4x or higher.",
    },
    {
      question: "How do I improve my ROAS?",
      answer:
        "Improve ROAS by: 1) Targeting more qualified audiences, 2) Improving ad creative, 3) Optimizing landing pages, 4) A/B testing ad variations, 5) Adjusting bidding strategies.",
    },
    {
      question: "What's the difference between ROAS and ROI?",
      answer:
        "ROAS measures revenue per ad dollar spent. ROI (Return on Investment) considers all costs including product costs, overhead, etc. ROAS = Revenue/Ad Spend; ROI = (Revenue - All Costs)/All Costs.",
    },
  ],
  relatedTools: [
    {
      name: "CPA Calculator",
      slug: "cpa-calculator",
      description: "Calculate your Cost Per Acquisition",
    },
    {
      name: "Break-even ROAS Calculator",
      slug: "break-even-roas-calculator",
      description: "Find your break-even point",
    },
    {
      name: "Ad Spend Planner",
      slug: "ad-spend-calculator",
      description: "Plan your advertising budget",
    },
  ],
};

export default ROASCalculator;
