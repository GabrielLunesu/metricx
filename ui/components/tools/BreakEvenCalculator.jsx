/**
 * Break-even ROAS Calculator Component
 *
 * WHAT: Interactive calculator for finding break-even ROAS
 * WHY: Essential for merchants to understand minimum profitable ROAS
 *
 * Formula: Break-even ROAS = 1 / Profit Margin
 *
 * @example
 * import { BreakEvenCalculator } from '@/components/tools/BreakEvenCalculator';
 *
 * <BreakEvenCalculator />
 */

"use client";

import { useState, useMemo } from "react";
import { CalculatorInput, CalculatorResult } from "./CalculatorLayout";
import { ArrowRight, AlertTriangle, CheckCircle } from "lucide-react";

/**
 * Break-even ROAS Calculator with real-time calculation.
 *
 * @returns {JSX.Element} Break-even ROAS calculator
 */
export function BreakEvenCalculator() {
  const [sellingPrice, setSellingPrice] = useState("");
  const [productCost, setProductCost] = useState("");
  const [shippingCost, setShippingCost] = useState("");
  const [otherCosts, setOtherCosts] = useState("");
  const [currentROAS, setCurrentROAS] = useState("");

  // Calculate break-even ROAS
  const result = useMemo(() => {
    const price = parseFloat(sellingPrice) || 0;
    const product = parseFloat(productCost) || 0;
    const shipping = parseFloat(shippingCost) || 0;
    const other = parseFloat(otherCosts) || 0;
    const current = parseFloat(currentROAS) || 0;

    if (price === 0) return null;

    const totalCost = product + shipping + other;
    const profit = price - totalCost;
    const profitMargin = profit / price;
    const breakEvenROAS = profitMargin > 0 ? 1 / profitMargin : Infinity;

    // Determine status
    let status = "neutral";
    let interpretation = "";

    if (profitMargin <= 0) {
      status = "error";
      interpretation = "Warning: Your costs exceed your selling price!";
    } else if (current > 0) {
      if (current >= breakEvenROAS * 1.5) {
        status = "success";
        interpretation = `Excellent! Your current ROAS is ${((current / breakEvenROAS - 1) * 100).toFixed(0)}% above break-even.`;
      } else if (current >= breakEvenROAS) {
        status = "success";
        interpretation = "You're profitable, but there's room to improve ROAS.";
      } else {
        status = "error";
        interpretation = `You need to improve ROAS by ${((breakEvenROAS / current - 1) * 100).toFixed(0)}% to break even.`;
      }
    }

    return {
      breakEvenROAS: breakEvenROAS === Infinity ? "N/A" : breakEvenROAS.toFixed(2),
      profitMargin: (profitMargin * 100).toFixed(1),
      profitPerSale: profit.toFixed(2),
      totalCost: totalCost.toFixed(2),
      status,
      interpretation,
      isValid: profitMargin > 0,
    };
  }, [sellingPrice, productCost, shippingCost, otherCosts, currentROAS]);

  return (
    <div className="break-even-calculator">
      {/* Inputs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        <CalculatorInput
          label="Selling Price"
          id="selling-price"
          value={sellingPrice}
          onChange={setSellingPrice}
          prefix="$"
          placeholder="100"
          helperText="Price you sell the product for"
        />
        <CalculatorInput
          label="Product Cost (COGS)"
          id="product-cost"
          value={productCost}
          onChange={setProductCost}
          prefix="$"
          placeholder="30"
          helperText="Cost of goods sold"
        />
        <CalculatorInput
          label="Shipping Cost"
          id="shipping-cost"
          value={shippingCost}
          onChange={setShippingCost}
          prefix="$"
          placeholder="5"
          helperText="Shipping per order"
        />
        <CalculatorInput
          label="Other Costs"
          id="other-costs"
          value={otherCosts}
          onChange={setOtherCosts}
          prefix="$"
          placeholder="5"
          helperText="Payment fees, packaging, etc."
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
      <div className="flex items-center justify-center gap-4 mb-8 text-slate-400 flex-wrap">
        <span className="text-sm">1</span>
        <ArrowRight className="w-4 h-4" />
        <span className="text-sm">÷ Profit Margin</span>
        <ArrowRight className="w-4 h-4" />
        <span className="text-sm font-semibold text-slate-600">Break-even ROAS</span>
      </div>

      {/* Results */}
      {result ? (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <CalculatorResult
              label="Break-even ROAS"
              value={result.isValid ? `${result.breakEvenROAS}x` : "N/A"}
              status={result.status}
              interpretation={result.interpretation}
            />
            <CalculatorResult
              label="Profit Margin"
              value={result.profitMargin}
              suffix="%"
              status={parseFloat(result.profitMargin) > 30 ? "success" : "warning"}
            />
            <CalculatorResult
              label="Profit Per Sale"
              value={`$${result.profitPerSale}`}
              status={parseFloat(result.profitPerSale) > 0 ? "success" : "error"}
            />
            <CalculatorResult
              label="Total Costs"
              value={`$${result.totalCost}`}
              status="neutral"
            />
          </div>

          {/* ROAS Target Guide */}
          {result.isValid && (
            <div className="p-4 bg-slate-50 rounded-lg">
              <h3 className="font-semibold text-slate-900 mb-3">ROAS Targets Based on Your Margins</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-red-500" />
                  <span>Below {result.breakEvenROAS}x</span>
                  <span className="text-red-500">Losing $</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-amber-500 rounded-full"></div>
                  <span>{result.breakEvenROAS}x</span>
                  <span className="text-amber-500">Break-even</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-500" />
                  <span>{(parseFloat(result.breakEvenROAS) * 1.25).toFixed(1)}x+</span>
                  <span className="text-emerald-500">Profitable</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-600" />
                  <span>{(parseFloat(result.breakEvenROAS) * 1.5).toFixed(1)}x+</span>
                  <span className="text-emerald-600">Excellent</span>
                </div>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="text-center py-12 text-slate-400">
          <p>Enter your product pricing to calculate break-even ROAS</p>
        </div>
      )}
    </div>
  );
}

/**
 * Break-even ROAS Calculator page data.
 */
export const breakEvenCalculatorData = {
  title: "Break-even ROAS Calculator",
  slug: "break-even-roas-calculator",
  description:
    "Calculate the minimum ROAS needed to break even on your ad spend. Enter your costs to find your profitability threshold.",
  howToSteps: [
    {
      name: "Enter your selling price",
      text: "Enter the price you sell your product for.",
    },
    {
      name: "Enter all costs",
      text: "Add product cost, shipping, and other per-order expenses.",
    },
    {
      name: "View break-even ROAS",
      text: "See the minimum ROAS needed to not lose money on ads.",
    },
  ],
  faqs: [
    {
      question: "What is break-even ROAS?",
      answer:
        "Break-even ROAS is the minimum Return on Ad Spend needed to cover all costs. Below this point, you lose money on every sale from ads. It's calculated as 1 divided by your profit margin.",
    },
    {
      question: "Why is knowing break-even ROAS important?",
      answer:
        "It sets your minimum performance threshold. Any ROAS above break-even is profitable. This helps you: set appropriate bid caps, evaluate campaign performance, and make informed scaling decisions.",
    },
    {
      question: "How much above break-even should I target?",
      answer:
        "Aim for at least 25-50% above break-even for healthy profitability. This buffer accounts for returns, customer service costs, and provides room for growth. If break-even is 2x, target 2.5-3x.",
    },
    {
      question: "What if my break-even ROAS is very high?",
      answer:
        "High break-even ROAS (5x+) means low margins. Consider: 1) Raising prices, 2) Reducing product costs, 3) Focusing on LTV through repeat purchases, 4) Targeting only high-intent audiences.",
    },
  ],
  relatedTools: [
    {
      name: "ROAS Calculator",
      slug: "roas-calculator",
      description: "Calculate your Return on Ad Spend",
    },
    {
      name: "Ad Spend Planner",
      slug: "ad-spend-calculator",
      description: "Plan your advertising budget",
    },
    {
      name: "CPA Calculator",
      slug: "cpa-calculator",
      description: "Calculate Cost Per Acquisition",
    },
  ],
};

export default BreakEvenCalculator;
