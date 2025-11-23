/**
 * Finance Page Top Bar
 * 
 * WHAT: Period selector and comparison toggle
 * WHY: Controls which data is displayed in Finance page
 * REFERENCES: app/(dashboard)/finance/page.jsx
 */

"use client";
import { useState, useEffect, useRef } from "react";
import { ChevronDown } from "lucide-react";

export default function TopBar({ selectedPeriod, onPeriodChange, compareEnabled, onCompareToggle }) {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);
  const [customMonth, setCustomMonth] = useState(selectedPeriod?.month || 1);
  const [customYear, setCustomYear] = useState(selectedPeriod?.year || new Date().getFullYear());

  // Handle click outside to close dropdown
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsDropdownOpen(false);
      }
    }

    if (isDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isDropdownOpen]);

  // Generate all period options
  const periods = [];
  const now = new Date();
  const monthNames = ["January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"];
  const yearOptions = Array.from({ length: 3 }, (_, idx) => now.getFullYear() + 1 - idx);

  // Generate last 12 months
  for (let i = 0; i < 12; i++) {
    const date = new Date(now.getFullYear(), now.getMonth() - i, 1);
    periods.push({
      year: date.getFullYear(),
      month: date.getMonth() + 1,
      label: i === 0 ? 'This Month' : i === 1 ? 'Last Month' : `${monthNames[date.getMonth()]} ${date.getFullYear()}`,
      isMain: i <= 1 // First two are main options
    });
  }

  const handlePeriodClick = (period) => {
    onPeriodChange?.({ year: period.year, month: period.month });
    setIsDropdownOpen(false);
  };

  const isSelected = (period) => {
    return selectedPeriod.year === period.year && selectedPeriod.month === period.month;
  };

  const getCurrentLabel = () => {
    const current = periods.find(p => isSelected(p));
    return current?.label || 'Select Period';
  };

  const hasCustomSelected = periods.some(p => !p.isMain && isSelected(p));

  const handleApplyCustomMonth = () => {
    if (!customMonth || !customYear) return;
    onPeriodChange?.({ year: Number(customYear), month: Number(customMonth) });
    setIsDropdownOpen(false);
  };

  const handleYearPreset = (year) => {
    // Default to December when picking full-year shortcut
    onPeriodChange?.({ year, month: 12 });
    setIsDropdownOpen(false);
  };

  return (
    <header className="relative shrink-0 rounded-lg py-6 backdrop-blur-md flex flex-col md:flex-row justify-between items-start md:items-center gap-4 z-40">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Finance &amp; P&amp;L Overview</h1>
        <p className="text-lg text-slate-500 mt-1 font-normal">See how your ad spend turns into profit.</p>
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center gap-3 bg-white/90 p-3 sm:p-2 rounded-2xl border border-slate-200 shadow-sm w-full md:w-auto">
        {/* Period selector pill */}
        <div className="w-full sm:w-auto space-y-2">
          <div className="flex items-center justify-between sm:justify-start gap-2">
            <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-500 sm:hidden">
              {getCurrentLabel()}
            </span>
          </div>
          <div className="flex gap-2 overflow-x-auto no-scrollbar max-w-full snap-x snap-mandatory pb-1" style={{ overflowY: 'visible' }}>
            {periods.filter(p => p.isMain).map((period, idx) => (
              <button
                key={idx}
                onClick={() => handlePeriodClick(period)}
                className={`px-4 py-1.5 rounded-full text-xs font-medium transition-all whitespace-nowrap snap-start ${isSelected(period)
                  ? 'text-blue-700 bg-blue-50 border border-blue-100 shadow-sm'
                  : 'text-slate-500 hover:bg-slate-50 hover:text-slate-700'
                  }`}
              >
                {period.label === 'This Month' ? 'This Month' : period.label === 'Last Month' ? 'Last Month' : period.label}
              </button>
            ))}
          </div>

          {/* Custom / other months */}
          <div className="relative snap-start" style={{ zIndex: 9999 }} ref={dropdownRef}>
            <button
              type="button"
              onClick={() => setIsDropdownOpen(!isDropdownOpen)}
              className={`w-full sm:w-auto justify-between sm:justify-start px-4 py-2 rounded-xl border border-slate-200 text-xs font-semibold flex items-center gap-2 transition-all ${hasCustomSelected
                ? 'text-blue-700 bg-blue-50 border-blue-100 shadow-sm'
                : 'text-slate-600 hover:bg-slate-50'
                }`}
            >
              <span className="truncate">{hasCustomSelected ? getCurrentLabel() : 'Custom'}</span>
              <ChevronDown className={`w-3 h-3 opacity-60 transition-transform ${isDropdownOpen ? 'rotate-180' : ''}`} />
            </button>

            {isDropdownOpen && (
              <div className="absolute left-0 sm:left-auto sm:right-0 top-full mt-2 w-full sm:w-72 bg-white rounded-2xl border border-slate-200 shadow-2xl p-3 space-y-3 z-[110]" style={{ zIndex: 9999 }}>
                <div className="space-y-1">
                  <p className="text-[10px] font-semibold uppercase text-slate-400 tracking-wide">Year quick picks</p>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      onClick={() => handleYearPreset(now.getFullYear())}
                      className="px-3 py-2 rounded-xl border border-slate-200 text-xs font-semibold text-slate-700 hover:border-blue-200 hover:bg-blue-50 transition-colors"
                    >
                      This Year ({now.getFullYear()})
                    </button>
                    <button
                      onClick={() => handleYearPreset(now.getFullYear() - 1)}
                      className="px-3 py-2 rounded-xl border border-slate-200 text-xs font-semibold text-slate-700 hover:border-blue-200 hover:bg-blue-50 transition-colors"
                    >
                      Last Year ({now.getFullYear() - 1})
                    </button>
                  </div>
                </div>

                <div className="space-y-2">
                  <p className="text-[10px] font-semibold uppercase text-slate-400 tracking-wide">Custom month</p>
                  <div className="grid grid-cols-2 gap-2">
                    <select
                      value={customMonth}
                      onChange={(e) => setCustomMonth(Number(e.target.value))}
                      className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs font-medium text-slate-700 bg-white focus:outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
                    >
                      {monthNames.map((name, idx) => (
                        <option key={name} value={idx + 1}>{name}</option>
                      ))}
                    </select>
                    <select
                      value={customYear}
                      onChange={(e) => setCustomYear(Number(e.target.value))}
                      className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs font-medium text-slate-700 bg-white focus:outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
                    >
                      {yearOptions.map((year) => (
                        <option key={year} value={year}>{year}</option>
                      ))}
                    </select>
                  </div>
                  <button
                    onClick={handleApplyCustomMonth}
                    className="w-full px-4 py-2 rounded-xl bg-gradient-to-r from-blue-500 to-blue-600 text-white text-xs font-semibold shadow-sm hover:from-blue-600 hover:to-blue-700 transition-colors"
                  >
                    Apply
                  </button>
                </div>

                <div className="space-y-1">
                  <p className="text-[10px] font-semibold uppercase text-slate-400 tracking-wide">Recent months</p>
                  <div className="grid grid-cols-2 gap-2 max-h-52 overflow-y-auto pr-1">
                    {periods.filter(p => !p.isMain).map((period, idx) => (
                      <button
                        key={idx}
                        onClick={() => handlePeriodClick(period)}
                        className={`w-full text-left px-3 py-2 rounded-xl text-xs font-semibold transition-all border ${isSelected(period)
                          ? 'bg-blue-50 text-blue-600 border-blue-200'
                          : 'text-slate-600 hover:bg-slate-50 border-slate-200'
                          }`}
                      >
                        {period.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="h-px w-full bg-slate-200 sm:h-8 sm:w-px sm:mx-1" />

        {/* Compare toggle */}
        <div className="flex items-center justify-between sm:justify-start gap-2 pr-1 pl-1 w-full sm:w-auto">
          <div className="flex items-center gap-2">
            <div className="relative inline-block w-8 h-4 align-middle select-none">
              <input
                type="checkbox"
                id="finance-compare-toggle"
                className="sr-only peer"
                checked={compareEnabled}
                onChange={(e) => onCompareToggle?.(e.target.checked)}
              />
              <label
                htmlFor="finance-compare-toggle"
                className="block overflow-hidden h-4 rounded-full bg-slate-200 cursor-pointer peer-checked:bg-blue-500 transition-colors duration-300"
              >
                <span className="block w-4 h-4 bg-white rounded-full shadow-sm transition-transform duration-300 ease-in-out peer-checked:translate-x-4" />
              </label>
            </div>
            <span className="text-[10px] font-semibold uppercase text-slate-400 tracking-wide whitespace-nowrap">
              Compare
            </span>
          </div>
          <div className="text-[11px] px-2 py-1 rounded-lg bg-slate-50 text-slate-500 sm:hidden">
            Toggle month-over-month view
          </div>
        </div>
      </div>
    </header>
  );
}
