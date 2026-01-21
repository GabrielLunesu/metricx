/**
 * CTR Calculator Component
 *
 * WHAT: Interactive calculator for Click-Through Rate
 * WHY: High-intent tool page to attract backlinks and conversions
 *
 * Formula: CTR = (Clicks / Impressions) × 100
 *
 * @example
 * import { CTRCalculator } from '@/components/tools/CTRCalculator';
 *
 * <CTRCalculator />
 */

"use client";

import { useState, useMemo } from "react";
import { CalculatorInput, CalculatorResult } from "./CalculatorLayout";
import { ArrowRight } from "lucide-react";

/**
 * CTR Calculator with real-time calculation.
 *
 * @returns {JSX.Element} CTR calculator
 */
export function CTRCalculator() {
  const [clicks, setClicks] = useState("");
  const [impressions, setImpressions] = useState("");

  // Calculate CTR
  const result = useMemo(() => {
    const clickCount = parseInt(clicks, 10) || 0;
    const impCount = parseInt(impressions, 10) || 0;

    if (impCount === 0) return null;

    const ctr = (clickCount / impCount) * 100;

    // Determine status based on CTR value
    let status = "neutral";
    let interpretation = "";

    if (ctr >= 3) {
      status = "success";
      interpretation = "Excellent CTR! Your ads are highly engaging.";
    } else if (ctr >= 1.5) {
      status = "success";
      interpretation = "Good CTR. Above average performance.";
    } else if (ctr >= 0.5) {
      status = "warning";
      interpretation = "Average CTR. Room for creative improvement.";
    } else {
      status = "error";
      interpretation = "Low CTR. Review ad copy and targeting.";
    }

    return {
      ctr: ctr.toFixed(2),
      totalClicks: clickCount,
      totalImpressions: impCount,
      status,
      interpretation,
    };
  }, [clicks, impressions]);

  const formatNumber = (num) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  return (
    <div className="ctr-calculator">
      {/* Inputs */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <CalculatorInput
          label="Clicks"
          id="clicks"
          value={clicks}
          onChange={setClicks}
          placeholder="1500"
          helperText="Total number of clicks"
        />
        <CalculatorInput
          label="Impressions"
          id="impressions"
          value={impressions}
          onChange={setImpressions}
          placeholder="100000"
          helperText="Total number of impressions"
        />
      </div>

      {/* Calculation Indicator */}
      <div className="flex items-center justify-center gap-4 mb-8 text-slate-400">
        <span className="text-sm">(Clicks ÷ Impressions)</span>
        <ArrowRight className="w-4 h-4" />
        <span className="text-sm">× 100</span>
        <ArrowRight className="w-4 h-4" />
        <span className="text-sm font-semibold text-slate-600">CTR %</span>
      </div>

      {/* Results */}
      {result ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <CalculatorResult
            label="Your CTR"
            value={result.ctr}
            suffix="%"
            status={result.status}
            interpretation={result.interpretation}
          />
          <CalculatorResult
            label="Total Clicks"
            value={formatNumber(result.totalClicks)}
            status="neutral"
          />
          <CalculatorResult
            label="Total Impressions"
            value={formatNumber(result.totalImpressions)}
            status="neutral"
          />
        </div>
      ) : (
        <div className="text-center py-12 text-slate-400">
          <p>Enter your clicks and impressions to calculate CTR</p>
        </div>
      )}

      {/* Benchmark Reference */}
      <div className="mt-8 p-4 bg-slate-50 rounded-lg">
        <h3 className="font-semibold text-slate-900 mb-2">CTR Benchmarks by Ad Type</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="font-medium text-slate-700">Search Ads</span>
            <p className="text-slate-500">1.9% - 4.5%</p>
          </div>
          <div>
            <span className="font-medium text-slate-700">Display Ads</span>
            <p className="text-slate-500">0.3% - 0.9%</p>
          </div>
          <div>
            <span className="font-medium text-slate-700">Facebook Feed</span>
            <p className="text-slate-500">0.9% - 1.5%</p>
          </div>
          <div>
            <span className="font-medium text-slate-700">Email</span>
            <p className="text-slate-500">2.5% - 4.5%</p>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * CTR Calculator page data.
 */
export const ctrCalculatorData = {
  title: "CTR Calculator",
  slug: "ctr-calculator",
  description:
    "Calculate your Click-Through Rate (CTR) instantly. Compare your ad engagement against industry benchmarks.",
  howToSteps: [
    {
      name: "Enter total clicks",
      text: "Enter the number of clicks your ad or content received.",
    },
    {
      name: "Enter total impressions",
      text: "Enter the number of times your ad or content was viewed.",
    },
    {
      name: "View your CTR",
      text: "See your CTR percentage and compare it to benchmarks.",
    },
  ],
  faqs: [
    {
      question: "What is CTR?",
      answer:
        "CTR (Click-Through Rate) is the percentage of people who clicked on your ad after seeing it. It's calculated as (Clicks ÷ Impressions) × 100.",
    },
    {
      question: "What's a good CTR?",
      answer:
        "Good CTR varies by platform and ad type. Search ads: 2-5%, Display ads: 0.5-1%, Social ads: 1-2%. Higher CTR usually indicates more relevant, engaging ads.",
    },
    {
      question: "Why is CTR important?",
      answer:
        "CTR indicates how well your ads resonate with your audience. High CTR can lower costs (better Quality Score on Google), improve ad delivery, and shows your targeting is effective.",
    },
    {
      question: "How do I improve CTR?",
      answer:
        "Improve CTR by: 1) Writing compelling headlines, 2) Using strong CTAs, 3) Adding ad extensions, 4) Refining audience targeting, 5) Testing different creatives, 6) Matching ad to landing page intent.",
    },
  ],
  relatedTools: [
    {
      name: "CPM Calculator",
      slug: "cpm-calculator",
      description: "Calculate Cost Per Thousand Impressions",
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

export default CTRCalculator;
