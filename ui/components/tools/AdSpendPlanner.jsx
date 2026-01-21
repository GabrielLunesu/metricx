/**
 * Ad Spend Planner Component
 *
 * WHAT: Interactive calculator for planning ad budget based on revenue goals
 * WHY: Helps merchants plan budget to hit revenue targets
 *
 * Formula: Required Ad Spend = Revenue Goal / Target ROAS
 *
 * @example
 * import { AdSpendPlanner } from '@/components/tools/AdSpendPlanner';
 *
 * <AdSpendPlanner />
 */

"use client";

import { useState, useMemo } from "react";
import { CalculatorInput, CalculatorResult } from "./CalculatorLayout";
import { ArrowRight, Target, DollarSign } from "lucide-react";

/**
 * Ad Spend Planner with real-time calculation.
 *
 * @returns {JSX.Element} Ad spend planner
 */
export function AdSpendPlanner() {
  const [revenueGoal, setRevenueGoal] = useState("");
  const [targetROAS, setTargetROAS] = useState("");
  const [currentROAS, setCurrentROAS] = useState("");

  // Calculate required ad spend
  const result = useMemo(() => {
    const goal = parseFloat(revenueGoal) || 0;
    const roas = parseFloat(targetROAS) || 0;
    const current = parseFloat(currentROAS) || 0;

    if (roas === 0) return null;

    const requiredSpend = goal / roas;
    const currentSpend = current > 0 ? goal / current : null;

    // Determine status
    let status = "neutral";
    let interpretation = "";

    if (current > 0) {
      if (current >= roas) {
        status = "success";
        interpretation = `You're already exceeding target ROAS. You could spend $${requiredSpend.toLocaleString()} to hit your goal.`;
      } else {
        const diff = roas - current;
        status = "warning";
        interpretation = `You need to improve ROAS by ${diff.toFixed(1)}x to hit target. Focus on optimization.`;
      }
    }

    return {
      requiredSpend: requiredSpend.toFixed(2),
      currentSpend: currentSpend?.toFixed(2),
      dailyBudget: (requiredSpend / 30).toFixed(2),
      weeklyBudget: (requiredSpend / 4).toFixed(2),
      status,
      interpretation,
    };
  }, [revenueGoal, targetROAS, currentROAS]);

  return (
    <div className="ad-spend-planner">
      {/* Inputs */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <CalculatorInput
          label="Revenue Goal"
          id="revenue-goal"
          value={revenueGoal}
          onChange={setRevenueGoal}
          prefix="$"
          placeholder="50000"
          helperText="Monthly revenue target"
        />
        <CalculatorInput
          label="Target ROAS"
          id="target-roas"
          value={targetROAS}
          onChange={setTargetROAS}
          suffix="x"
          placeholder="4"
          helperText="Target Return on Ad Spend"
        />
        <CalculatorInput
          label="Current ROAS (Optional)"
          id="current-roas"
          value={currentROAS}
          onChange={setCurrentROAS}
          suffix="x"
          placeholder="3.5"
          helperText="Your current ROAS"
        />
      </div>

      {/* Calculation Indicator */}
      <div className="flex items-center justify-center gap-4 mb-8 text-slate-400">
        <span className="text-sm">Revenue Goal</span>
        <ArrowRight className="w-4 h-4" />
        <span className="text-sm">÷ Target ROAS</span>
        <ArrowRight className="w-4 h-4" />
        <span className="text-sm font-semibold text-slate-600">Required Ad Spend</span>
      </div>

      {/* Results */}
      {result ? (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <CalculatorResult
              label="Required Monthly Ad Spend"
              value={`$${parseFloat(result.requiredSpend).toLocaleString()}`}
              status={result.status}
              interpretation={result.interpretation}
            />
            <CalculatorResult
              label="Weekly Budget"
              value={`$${parseFloat(result.weeklyBudget).toLocaleString()}`}
              status="neutral"
              interpretation="Divide monthly by 4"
            />
            <CalculatorResult
              label="Daily Budget"
              value={`$${parseFloat(result.dailyBudget).toLocaleString()}`}
              status="neutral"
              interpretation="Divide monthly by 30"
            />
          </div>

          {/* Budget Breakdown */}
          <div className="p-4 bg-slate-50 rounded-lg">
            <h3 className="font-semibold text-slate-900 mb-3">Budget Allocation Suggestion</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-blue-500 rounded"></div>
                <span>Meta Ads: 50%</span>
                <span className="text-slate-500">${(parseFloat(result.requiredSpend) * 0.5).toLocaleString()}</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-red-500 rounded"></div>
                <span>Google Ads: 35%</span>
                <span className="text-slate-500">${(parseFloat(result.requiredSpend) * 0.35).toLocaleString()}</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-black rounded"></div>
                <span>TikTok: 15%</span>
                <span className="text-slate-500">${(parseFloat(result.requiredSpend) * 0.15).toLocaleString()}</span>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="text-center py-12 text-slate-400">
          <p>Enter your revenue goal and target ROAS to plan your ad spend</p>
        </div>
      )}
    </div>
  );
}

/**
 * Ad Spend Planner page data.
 */
export const adSpendPlannerData = {
  title: "Ad Spend Planner",
  slug: "ad-spend-calculator",
  description:
    "Plan your advertising budget based on revenue goals. Calculate the ad spend needed to hit your targets at your desired ROAS.",
  howToSteps: [
    {
      name: "Set your revenue goal",
      text: "Enter your target monthly revenue from advertising.",
    },
    {
      name: "Enter target ROAS",
      text: "Set the ROAS you want to achieve (e.g., 4x means $4 revenue per $1 spent).",
    },
    {
      name: "View budget breakdown",
      text: "See required monthly, weekly, and daily budgets plus allocation suggestions.",
    },
  ],
  faqs: [
    {
      question: "How do I determine my target ROAS?",
      answer:
        "Your target ROAS depends on your profit margins. Calculate your break-even ROAS first (use our Break-even Calculator), then set a target above that for profitability. Most e-commerce brands target 3-5x ROAS.",
    },
    {
      question: "Should I spread budget across platforms?",
      answer:
        "Yes, diversifying across platforms reduces risk and captures different audiences. Start with proven channels (Meta, Google) before testing newer ones (TikTok). Allocate more to platforms with better ROAS.",
    },
    {
      question: "How often should I adjust my budget?",
      answer:
        "Review weekly for optimization, monthly for major changes. Scale up campaigns gradually (20-30% increases) when ROAS is strong. Cut or pause campaigns quickly if ROAS drops below breakeven.",
    },
  ],
  relatedTools: [
    {
      name: "Break-even ROAS Calculator",
      slug: "break-even-roas-calculator",
      description: "Find your break-even point",
    },
    {
      name: "ROAS Calculator",
      slug: "roas-calculator",
      description: "Calculate your Return on Ad Spend",
    },
    {
      name: "CPA Calculator",
      slug: "cpa-calculator",
      description: "Calculate Cost Per Acquisition",
    },
  ],
};

export default AdSpendPlanner;
