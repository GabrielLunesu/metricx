/**
 * CPA Calculator Component
 *
 * WHAT: Interactive calculator for Cost Per Acquisition
 * WHY: High-intent tool page to attract backlinks and conversions
 *
 * Formula: CPA = Ad Spend / Number of Conversions
 *
 * @example
 * import { CPACalculator } from '@/components/tools/CPACalculator';
 *
 * <CPACalculator />
 */

"use client";

import { useState, useMemo } from "react";
import { CalculatorInput, CalculatorResult } from "./CalculatorLayout";
import { ArrowRight } from "lucide-react";

/**
 * CPA Calculator with real-time calculation.
 *
 * @returns {JSX.Element} CPA calculator
 */
export function CPACalculator() {
  const [adSpend, setAdSpend] = useState("");
  const [conversions, setConversions] = useState("");
  const [targetCPA, setTargetCPA] = useState("");

  // Calculate CPA
  const result = useMemo(() => {
    const spend = parseFloat(adSpend) || 0;
    const conv = parseInt(conversions, 10) || 0;
    const target = parseFloat(targetCPA) || 0;

    if (conv === 0) return null;

    const cpa = spend / conv;

    // Determine status based on target CPA
    let status = "neutral";
    let interpretation = "";

    if (target > 0) {
      if (cpa <= target * 0.8) {
        status = "success";
        interpretation = `Great! Your CPA is ${((1 - cpa / target) * 100).toFixed(0)}% below target.`;
      } else if (cpa <= target) {
        status = "success";
        interpretation = "You're within target CPA.";
      } else if (cpa <= target * 1.2) {
        status = "warning";
        interpretation = `Slightly over target by ${((cpa / target - 1) * 100).toFixed(0)}%.`;
      } else {
        status = "error";
        interpretation = `CPA is ${((cpa / target - 1) * 100).toFixed(0)}% above target. Review campaigns.`;
      }
    } else {
      interpretation = "Set a target CPA to see performance comparison.";
    }

    return {
      cpa: cpa.toFixed(2),
      totalConversions: conv,
      status,
      interpretation,
      costPerConversion: cpa,
    };
  }, [adSpend, conversions, targetCPA]);

  return (
    <div className="cpa-calculator">
      {/* Inputs */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <CalculatorInput
          label="Ad Spend"
          id="ad-spend"
          value={adSpend}
          onChange={setAdSpend}
          prefix="$"
          placeholder="1000"
          helperText="Total advertising spend"
        />
        <CalculatorInput
          label="Conversions"
          id="conversions"
          value={conversions}
          onChange={setConversions}
          placeholder="50"
          helperText="Number of conversions (sales, leads, etc.)"
        />
        <CalculatorInput
          label="Target CPA (Optional)"
          id="target-cpa"
          value={targetCPA}
          onChange={setTargetCPA}
          prefix="$"
          placeholder="25"
          helperText="Your target cost per acquisition"
        />
      </div>

      {/* Calculation Indicator */}
      <div className="flex items-center justify-center gap-4 mb-8 text-slate-400">
        <span className="text-sm">Ad Spend</span>
        <ArrowRight className="w-4 h-4" />
        <span className="text-sm">÷ Conversions</span>
        <ArrowRight className="w-4 h-4" />
        <span className="text-sm font-semibold text-slate-600">CPA</span>
      </div>

      {/* Results */}
      {result ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <CalculatorResult
            label="Your CPA"
            value={`$${result.cpa}`}
            status={result.status}
            interpretation={result.interpretation}
          />
          <CalculatorResult
            label="Total Conversions"
            value={result.totalConversions.toLocaleString()}
            status="neutral"
            interpretation={`From $${parseFloat(adSpend).toLocaleString()} ad spend`}
          />
        </div>
      ) : (
        <div className="text-center py-12 text-slate-400">
          <p>Enter your ad spend and conversions to calculate CPA</p>
        </div>
      )}

      {/* Benchmark Reference */}
      <div className="mt-8 p-4 bg-slate-50 rounded-lg">
        <h3 className="font-semibold text-slate-900 mb-2">CPA Benchmarks by Industry</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="font-medium text-slate-700">E-commerce</span>
            <p className="text-slate-500">$10 - $50</p>
          </div>
          <div>
            <span className="font-medium text-slate-700">SaaS</span>
            <p className="text-slate-500">$50 - $200</p>
          </div>
          <div>
            <span className="font-medium text-slate-700">Finance</span>
            <p className="text-slate-500">$50 - $150</p>
          </div>
          <div>
            <span className="font-medium text-slate-700">Education</span>
            <p className="text-slate-500">$30 - $100</p>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * CPA Calculator page data.
 */
export const cpaCalculatorData = {
  title: "CPA Calculator",
  slug: "cpa-calculator",
  description:
    "Calculate your Cost Per Acquisition (CPA) instantly. Enter your ad spend and conversions to find your customer acquisition cost.",
  howToSteps: [
    {
      name: "Enter your ad spend",
      text: "Enter the total amount spent on advertising campaigns.",
    },
    {
      name: "Enter your conversions",
      text: "Enter the number of conversions (sales, signups, leads) generated.",
    },
    {
      name: "Set target CPA (optional)",
      text: "Enter your target CPA to see how your actual CPA compares.",
    },
  ],
  faqs: [
    {
      question: "What is CPA?",
      answer:
        "CPA (Cost Per Acquisition) is the average cost to acquire one customer or conversion. It's calculated by dividing total ad spend by the number of conversions.",
    },
    {
      question: "What's a good CPA?",
      answer:
        "A good CPA depends on your industry, product margins, and customer lifetime value. Generally, your CPA should be less than your customer's lifetime value (LTV) for profitability.",
    },
    {
      question: "How do I lower my CPA?",
      answer:
        "Lower CPA by: 1) Improving targeting, 2) Testing better ad creatives, 3) Optimizing landing pages, 4) Using retargeting, 5) Focusing on higher-intent audiences.",
    },
    {
      question: "What's the difference between CPA and CAC?",
      answer:
        "CPA typically refers to cost per conversion from ads. CAC (Customer Acquisition Cost) includes all costs to acquire a customer: marketing, sales, onboarding, etc. CAC is usually higher than CPA.",
    },
  ],
  relatedTools: [
    {
      name: "ROAS Calculator",
      slug: "roas-calculator",
      description: "Calculate your Return on Ad Spend",
    },
    {
      name: "CPM Calculator",
      slug: "cpm-calculator",
      description: "Calculate Cost Per Thousand Impressions",
    },
    {
      name: "Break-even ROAS Calculator",
      slug: "break-even-roas-calculator",
      description: "Find your break-even point",
    },
  ],
};

export default CPACalculator;
