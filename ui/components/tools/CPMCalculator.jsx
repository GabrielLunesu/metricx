/**
 * CPM Calculator Component
 *
 * WHAT: Interactive calculator for Cost Per Mille (Thousand Impressions)
 * WHY: High-intent tool page to attract backlinks and conversions
 *
 * Formula: CPM = (Ad Spend / Impressions) × 1000
 *
 * @example
 * import { CPMCalculator } from '@/components/tools/CPMCalculator';
 *
 * <CPMCalculator />
 */

"use client";

import { useState, useMemo } from "react";
import { CalculatorInput, CalculatorResult } from "./CalculatorLayout";
import { ArrowRight } from "lucide-react";

/**
 * CPM Calculator with real-time calculation.
 *
 * @returns {JSX.Element} CPM calculator
 */
export function CPMCalculator() {
  const [adSpend, setAdSpend] = useState("");
  const [impressions, setImpressions] = useState("");

  // Calculate CPM
  const result = useMemo(() => {
    const spend = parseFloat(adSpend) || 0;
    const imp = parseInt(impressions, 10) || 0;

    if (imp === 0) return null;

    const cpm = (spend / imp) * 1000;

    // Determine status based on CPM value
    let status = "neutral";
    let interpretation = "";

    if (cpm < 5) {
      status = "success";
      interpretation = "Excellent CPM! Very cost-efficient impressions.";
    } else if (cpm < 15) {
      status = "success";
      interpretation = "Good CPM. Competitive with industry averages.";
    } else if (cpm < 30) {
      status = "warning";
      interpretation = "Above average CPM. Consider audience refinement.";
    } else {
      status = "error";
      interpretation = "High CPM. Review targeting and bidding strategy.";
    }

    return {
      cpm: cpm.toFixed(2),
      totalImpressions: imp,
      costPer1000: cpm,
      status,
      interpretation,
    };
  }, [adSpend, impressions]);

  const formatImpressions = (num) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  return (
    <div className="cpm-calculator">
      {/* Inputs */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <CalculatorInput
          label="Ad Spend"
          id="ad-spend"
          value={adSpend}
          onChange={setAdSpend}
          prefix="$"
          placeholder="500"
          helperText="Total advertising spend"
        />
        <CalculatorInput
          label="Impressions"
          id="impressions"
          value={impressions}
          onChange={setImpressions}
          placeholder="100000"
          helperText="Total number of ad impressions"
        />
      </div>

      {/* Calculation Indicator */}
      <div className="flex items-center justify-center gap-4 mb-8 text-slate-400">
        <span className="text-sm">(Ad Spend ÷ Impressions)</span>
        <ArrowRight className="w-4 h-4" />
        <span className="text-sm">× 1,000</span>
        <ArrowRight className="w-4 h-4" />
        <span className="text-sm font-semibold text-slate-600">CPM</span>
      </div>

      {/* Results */}
      {result ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <CalculatorResult
            label="Your CPM"
            value={`$${result.cpm}`}
            status={result.status}
            interpretation={result.interpretation}
          />
          <CalculatorResult
            label="Total Impressions"
            value={formatImpressions(result.totalImpressions)}
            status="neutral"
            interpretation={`${result.totalImpressions.toLocaleString()} total views`}
          />
        </div>
      ) : (
        <div className="text-center py-12 text-slate-400">
          <p>Enter your ad spend and impressions to calculate CPM</p>
        </div>
      )}

      {/* Benchmark Reference */}
      <div className="mt-8 p-4 bg-slate-50 rounded-lg">
        <h3 className="font-semibold text-slate-900 mb-2">CPM Benchmarks by Platform</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="font-medium text-slate-700">Facebook</span>
            <p className="text-slate-500">$5 - $15</p>
          </div>
          <div>
            <span className="font-medium text-slate-700">Instagram</span>
            <p className="text-slate-500">$6 - $18</p>
          </div>
          <div>
            <span className="font-medium text-slate-700">Google Display</span>
            <p className="text-slate-500">$2 - $8</p>
          </div>
          <div>
            <span className="font-medium text-slate-700">TikTok</span>
            <p className="text-slate-500">$4 - $12</p>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * CPM Calculator page data.
 */
export const cpmCalculatorData = {
  title: "CPM Calculator",
  slug: "cpm-calculator",
  description:
    "Calculate your Cost Per Mille (CPM) - the cost per 1,000 ad impressions. Compare your CPM against platform benchmarks.",
  howToSteps: [
    {
      name: "Enter your ad spend",
      text: "Enter the total amount spent on advertising.",
    },
    {
      name: "Enter total impressions",
      text: "Enter the number of impressions your ads received.",
    },
    {
      name: "View your CPM",
      text: "See your CPM calculated and compared to industry benchmarks.",
    },
  ],
  faqs: [
    {
      question: "What is CPM?",
      answer:
        "CPM (Cost Per Mille) is the cost per 1,000 ad impressions. 'Mille' is Latin for thousand. It's a standard metric for measuring the cost-efficiency of awareness campaigns.",
    },
    {
      question: "What's a good CPM?",
      answer:
        "CPM varies by platform and industry. Facebook averages $5-15, Google Display $2-8. B2B typically has higher CPMs than B2C. A 'good' CPM depends on your campaign goals and audience value.",
    },
    {
      question: "When should I optimize for CPM?",
      answer:
        "Optimize for CPM when running brand awareness or reach campaigns where visibility matters more than clicks or conversions. For performance campaigns, focus on CPA or ROAS instead.",
    },
    {
      question: "How do I lower my CPM?",
      answer:
        "Lower CPM by: 1) Expanding audience targeting, 2) Testing different placements, 3) Improving ad relevance scores, 4) Adjusting bid strategy, 5) Running during lower-competition times.",
    },
  ],
  relatedTools: [
    {
      name: "CTR Calculator",
      slug: "ctr-calculator",
      description: "Calculate Click-Through Rate",
    },
    {
      name: "CPA Calculator",
      slug: "cpa-calculator",
      description: "Calculate Cost Per Acquisition",
    },
    {
      name: "ROAS Calculator",
      slug: "roas-calculator",
      description: "Calculate Return on Ad Spend",
    },
  ],
};

export default CPMCalculator;
