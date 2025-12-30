"use client";

/**
 * FinancePLTable - P&L Statement table with Add Cost button
 * 
 * WHAT: Clean table showing revenue and costs breakdown
 * WHY: Core P&L view for financial analysis
 * 
 * REFERENCES:
 *   - Metricx v3.0 design system
 */

import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";

/**
 * Currency symbols
 */
const CURRENCY_SYMBOLS = {
  USD: "$",
  EUR: "€",
  GBP: "£",
  CAD: "C$",
  AUD: "A$",
};

/**
 * Format currency value
 */
function formatCurrency(value, currency = "EUR", showSign = false) {
  if (value === null || value === undefined) return "—";
  const symbol = CURRENCY_SYMBOLS[currency] || "€";
  const absValue = Math.abs(value);
  const formatted = new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(absValue);
  
  if (showSign && value < 0) {
    return `-${symbol}${formatted}`;
  }
  return `${symbol}${formatted}`;
}

export default function FinancePLTable({
  rows = [],
  totalRevenue = 0,
  netProfit = 0,
  onAddCost,
  onEditCost,
  loading = false,
  currency = "EUR",
}) {
  // Separate revenue and cost rows
  const revenueRow = { category: "Gross Sales", amount: totalRevenue };
  const costRows = rows.filter(r => r.actualRaw && r.actualRaw > 0);

  if (loading) {
    return (
      <div className="p-6 border border-neutral-200 bg-white rounded-xl">
        <div className="flex items-center justify-between mb-6">
          <div className="h-5 w-40 bg-neutral-100 rounded animate-pulse" />
          <div className="h-8 w-24 bg-neutral-100 rounded animate-pulse" />
        </div>
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="flex justify-between py-3 border-b border-neutral-100">
              <div className="h-4 w-32 bg-neutral-100 rounded animate-pulse" />
              <div className="h-4 w-24 bg-neutral-100 rounded animate-pulse" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 border border-neutral-200 bg-white rounded-xl shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-base font-semibold text-neutral-900 tracking-tight">
          Profit & Loss Statement
        </h3>
        <Button
          variant="outline"
          size="sm"
          onClick={onAddCost}
          className="h-8 px-3 text-xs font-medium text-neutral-600 hover:text-neutral-900 border-neutral-200 hover:bg-neutral-50"
        >
          <Plus className="w-3.5 h-3.5 mr-1.5" />
          Add Cost
        </Button>
      </div>

      {/* Table */}
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-neutral-100">
            <th className="pb-3 text-xs font-medium text-neutral-500 uppercase tracking-wider w-full">
              Category
            </th>
            <th className="pb-3 text-xs font-medium text-neutral-500 uppercase tracking-wider text-right whitespace-nowrap">
              Amount
            </th>
          </tr>
        </thead>
        <tbody className="text-neutral-600">
          {/* Revenue row */}
          <tr className="group border-b border-neutral-100/50">
            <td className="py-3 group-hover:text-neutral-900 transition-colors">
              Gross Sales
            </td>
            <td className="py-3 text-right font-medium text-neutral-900 tabular-nums">
              {formatCurrency(totalRevenue, currency)}
            </td>
          </tr>

          {/* Cost rows */}
          {costRows.map((row) => (
            <tr
              key={row.id}
              className="group border-b border-neutral-100/50 cursor-pointer hover:bg-neutral-50/50"
              onClick={() => row.isManual && onEditCost?.(row)}
            >
              <td className="py-3 group-hover:text-neutral-900 transition-colors">
                {row.category}
                {row.isManual && (
                  <span className="ml-2 text-[10px] text-neutral-400 uppercase">manual</span>
                )}
              </td>
              <td className="py-3 text-right tabular-nums text-neutral-500">
                -{formatCurrency(row.actualRaw, currency)}
              </td>
            </tr>
          ))}

          {/* Empty state if no costs */}
          {costRows.length === 0 && (
            <tr>
              <td colSpan={2} className="py-6 text-center text-neutral-400 text-sm">
                No costs recorded. Click "Add Cost" to add expenses.
              </td>
            </tr>
          )}
        </tbody>
        <tfoot>
          <tr>
            <td className="pt-4 font-semibold text-neutral-900">Net Profit</td>
            <td className={`pt-4 text-right font-semibold tabular-nums text-lg tracking-tight ${
              netProfit >= 0 ? "text-emerald-600" : "text-red-600"
            }`}>
              {formatCurrency(netProfit, currency)}
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
