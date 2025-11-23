"use client";

import { useState } from "react";
import ManualCostDropdown from "./ManualCostDropdown";

export default function PLTable({
  rows,
  excludedRows = new Set(),
  onRowToggle,
  selectedMonth,
  onAddCost,
  manualCosts = [],
  onEditCost,
  onDeleteCost,
}) {
  const [activeDropdown, setActiveDropdown] = useState(null);

  if (!rows || rows.length === 0) {
    return (
      <div className="glass-card rounded-xl border border-slate-200 shadow-sm mb-6 overflow-hidden p-6 bg-white">
        <h2 className="text-sm font-semibold text-slate-800 mb-2">
          Profit and Loss Statement
        </h2>
        <p className="text-xs text-slate-400">
          No P&amp;L data available for this period.
        </p>
      </div>
    );
  }

  const activeRows = rows.filter((r) => !excludedRows.has(r.id));
  const totalActual = activeRows.reduce(
    (sum, r) => sum + (r.actualRaw || 0),
    0
  );

  const formatCurrency = (value) =>
    new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(value);

  return (
    <div className="glass-card rounded-xl overflow-hidden flex flex-col h-full border border-slate-200 shadow-sm bg-white">
      <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-white/80">
        <div>
          <h2 className="text-sm font-semibold text-slate-800">
            Profit &amp; Loss Statement
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Line items for ad spend and manual costs
          </p>
        </div>
        <button
          onClick={onAddCost}
          className="px-3 py-1.5 rounded-lg bg-blue-50 text-blue-600 text-[11px] font-semibold border border-blue-100 hover:bg-blue-100 transition-colors"
        >
          Add Cost
        </button>
      </div>

      <div className="flex-1 overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50/50 text-[10px] uppercase text-slate-400 font-semibold tracking-wider">
              <th className="px-6 py-3 w-10 text-center">Active</th>
              <th className="px-2 py-3">Category</th>
              <th className="px-6 py-3 text-right">Actual ($)</th>
              <th className="px-6 py-3">Notes</th>
            </tr>
          </thead>

          <tbody className="bg-white text-sm">
            {rows.map((row, idx) => {
              const isLastRow = idx === rows.length - 1;
              const isExcluded = excludedRows.has(row.id);
              const isDropdownOpen = activeDropdown === row.id;

              const categoryCosts = row.isManual
                ? manualCosts.filter((c) => c.category === row.category)
                : [];

              return (
                <tr
                  key={row.id}
                  className={`${
                    isLastRow ? "border-b-2 border-slate-200" : "border-b border-slate-100"
                  } transition-all ${isExcluded ? "opacity-50" : ""}`}
                >
                  <td className="text-center py-3 px-6">
                    <input
                      type="checkbox"
                      checked={!isExcluded}
                      onChange={() => onRowToggle?.(row.id)}
                      className="w-4 h-4 rounded border-slate-300 text-cyan-600 focus:ring-cyan-500 cursor-pointer"
                    />
                  </td>
                  <td className="py-3 px-2 relative">
                    <div
                      onClick={() =>
                        row.isManual &&
                        setActiveDropdown(isDropdownOpen ? null : row.id)
                      }
                      className={row.isManual ? "cursor-pointer" : ""}
                    >
                      <p
                        className={`text-sm font-medium ${
                          isExcluded
                            ? "line-through text-slate-400"
                            : "text-slate-700"
                        }`}
                      >
                        {row.category}
                      </p>
                      {row.isManual && (
                        <p className="text-[11px] text-blue-500 mt-0.5 hover:text-blue-600">
                          Manual entry - click to manage
                        </p>
                      )}
                    </div>

                    {isDropdownOpen && (
                      <ManualCostDropdown
                        costs={categoryCosts}
                        onEdit={onEditCost}
                        onDelete={onDeleteCost}
                        onClose={() => setActiveDropdown(null)}
                      />
                    )}
                  </td>
                  <td className="text-right py-3 px-6 font-mono">
                    <span
                      className={`text-sm font-semibold ${
                        isExcluded
                          ? "line-through text-slate-400"
                          : "text-slate-800"
                      }`}
                    >
                      {row.actual}
                    </span>
                  </td>
                  <td className="py-3 px-6 text-xs text-slate-400">
                    {row.notes}
                  </td>
                </tr>
              );
            })}

            <tr className="bg-slate-50/80 border-t border-slate-200">
              <td className="py-4 px-6"></td>
              <td className="py-4 px-2">
                <p className="text-sm font-bold text-slate-900">
                  Total Active Expenses
                </p>
              </td>
              <td className="text-right py-4 px-6 text-base font-bold text-slate-900">
                {formatCurrency(totalActual)}
              </td>
              <td className="py-4 px-6"></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
