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

  return (
    <header className="shrink-0 rounded-lg px-6 lg:px-8 py-6 border-b border-slate-200/60 bg-white/70 backdrop-blur-md flex flex-col md:flex-row justify-between items-start md:items-center gap-4 z-20">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Finance &amp; P&amp;L Overview</h1>
        <p className="text-sm text-slate-500 mt-1 font-light">See how your ad spend turns into profit.</p>
      </div>

      <div className="flex items-center gap-3 bg-white p-1.5 rounded-full border border-slate-200 shadow-sm">
        {/* Period selector pill */}
        <div className="flex gap-1">
          {periods.filter(p => p.isMain).map((period, idx) => (
            <button
              key={idx}
              onClick={() => handlePeriodClick(period)}
              className={`px-4 py-1.5 rounded-full text-xs font-medium transition-all ${isSelected(period)
                  ? 'text-blue-700 bg-blue-50 border border-blue-100 shadow-sm'
                  : 'text-slate-500 hover:bg-slate-50 hover:text-slate-700'
                }`}
            >
              {period.label === 'This Month' ? 'This Month' : period.label === 'Last Month' ? 'Last Month' : period.label}
            </button>
          ))}

          {/* Custom / other months */}
          <div className="relative" ref={dropdownRef}>
            <button
              type="button"
              onClick={() => setIsDropdownOpen(!isDropdownOpen)}
              className={`px-4 py-1.5 rounded-full text-xs font-medium flex items-center gap-1 transition-all ${hasCustomSelected
                  ? 'text-blue-700 bg-blue-50 border border-blue-100 shadow-sm'
                  : 'text-slate-500 hover:bg-slate-50 hover:text-slate-700'
                }`}
            >
              {hasCustomSelected ? getCurrentLabel() : 'Custom'}
              <ChevronDown className={`w-3 h-3 opacity-60 transition-transform ${isDropdownOpen ? 'rotate-180' : ''}`} />
            </button>

            {isDropdownOpen && (
              <div className="absolute top-full right-0 mt-2 w-64 glass-panel rounded-2xl border border-slate-200 shadow-float p-2 max-h-80 overflow-y-auto z-50">
                {periods.filter(p => !p.isMain).map((period, idx) => (
                  <button
                    key={idx}
                    onClick={() => handlePeriodClick(period)}
                    className={`w-full text-left px-4 py-2 rounded-xl text-sm font-medium transition-all ${isSelected(period)
                        ? 'bg-blue-50 text-blue-600'
                        : 'text-slate-600 hover:bg-slate-50'
                      }`}
                  >
                    {period.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="h-4 w-px bg-slate-200 mx-1" />

        {/* Compare toggle */}
        <div className="flex items-center gap-2 pr-3 pl-1">
          <div className="relative inline-block w-8 h-4 align-middle select-none transition duration-200 ease-in">
            <input
              type="checkbox"
              id="finance-compare-toggle"
              className="toggle-checkbox absolute block w-4 h-4 rounded-full bg-white border-4 border-slate-200 appearance-none cursor-pointer transition-all duration-300 left-0 top-0 shadow-sm checked:right-0 checked:border-blue-500"
              checked={compareEnabled}
              onChange={(e) => onCompareToggle?.(e.target.checked)}
            />
            <label
              htmlFor="finance-compare-toggle"
              className="toggle-label block overflow-hidden h-4 rounded-full bg-slate-200 cursor-pointer"
            />
          </div>
          <span className="text-[10px] font-semibold uppercase text-slate-400 tracking-wide">
            Compare
          </span>
        </div>
      </div>
    </header>
  );
}
