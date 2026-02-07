"use client";

/**
 * FinanceHeader - Header with title and date range picker
 * 
 * WHAT: Page header with date range selection using shadcn DateRangePicker
 * WHY: Clean header matching Metricx v3.0 design with proper date selection
 * 
 * PRESETS:
 *   - This Month
 *   - Last Month  
 *   - Last 90 Days
 *   - Custom (calendar picker)
 * 
 * REFERENCES:
 *   - components/ui/date-range-picker.jsx
 *   - Metricx v3.0 design system
 */

import * as React from "react";
import { useMediaQuery } from "@/hooks/use-media-query";
import { format, startOfMonth, endOfMonth, subMonths, subDays, startOfDay, endOfDay, isSameDay } from "date-fns";
import { Calendar as CalendarIcon } from "lucide-react";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/cn";

/**
 * Finance-specific presets
 */
const PRESETS = [
  { 
    key: 'this_month', 
    label: 'This Month', 
    shortLabel: 'This Month',
    getDates: () => {
      const now = new Date();
      return { 
        from: startOfMonth(now), 
        to: endOfDay(now) // Up to today, not end of month
      };
    }
  },
  { 
    key: 'last_month', 
    label: 'Last Month', 
    shortLabel: 'Last Month',
    getDates: () => {
      const lastMonth = subMonths(new Date(), 1);
      return { 
        from: startOfMonth(lastMonth), 
        to: endOfMonth(lastMonth) 
      };
    }
  },
  { 
    key: 'last_90_days', 
    label: 'Last 90 Days', 
    shortLabel: '90 Days',
    getDates: () => ({ 
      from: startOfDay(subDays(new Date(), 89)), 
      to: endOfDay(new Date()) 
    })
  },
];

export default function FinanceHeader({
  dateRange,
  onDateRangeChange,
}) {
  const [open, setOpen] = React.useState(false);
  const [localRange, setLocalRange] = React.useState(dateRange);
  const [localPreset, setLocalPreset] = React.useState('this_month');
  const isDesktop = useMediaQuery("(min-width: 768px)");

  // Detect current preset based on dateRange
  React.useEffect(() => {
    if (!dateRange?.from || !dateRange?.to) return;
    
    // Check each preset
    for (const preset of PRESETS) {
      const presetDates = preset.getDates();
      if (
        isSameDay(dateRange.from, presetDates.from) &&
        isSameDay(dateRange.to, presetDates.to)
      ) {
        setLocalPreset(preset.key);
        return;
      }
    }
    setLocalPreset('custom');
  }, [dateRange]);

  // Sync local state when popover opens
  React.useEffect(() => {
    if (open) {
      setLocalRange(dateRange);
    }
  }, [open, dateRange]);

  // Get display label for trigger button
  const getDisplayLabel = () => {
    if (localPreset && localPreset !== 'custom') {
      const presetConfig = PRESETS.find(p => p.key === localPreset);
      return presetConfig?.label || 'Select dates';
    }
    if (dateRange?.from && dateRange?.to) {
      if (isSameDay(dateRange.from, dateRange.to)) {
        return format(dateRange.from, 'MMM d, yyyy');
      }
      const fromStr = format(dateRange.from, 'MMM d');
      const toStr = format(dateRange.to, 'MMM d, yyyy');
      return `${fromStr} - ${toStr}`;
    }
    return 'Select dates';
  };

  // Handle preset chip click
  const handlePresetClick = (presetKey) => {
    setLocalPreset(presetKey);
    const presetConfig = PRESETS.find(p => p.key === presetKey);
    if (presetConfig) {
      setLocalRange(presetConfig.getDates());
    }
  };

  // Handle calendar date selection
  const handleDateSelect = (range) => {
    if (!range) return;
    setLocalPreset('custom');
    setLocalRange(range);
  };

  // Apply selection
  const handleApply = () => {
    if (localRange?.from) {
      const finalRange = {
        from: localRange.from,
        to: localRange.to || localRange.from
      };
      onDateRangeChange?.(finalRange);
      setOpen(false);
    }
  };

  // Cancel and reset
  const handleCancel = () => {
    setLocalRange(dateRange);
    setOpen(false);
  };

  // Check if a preset is selected
  const isPresetSelected = (key) => localPreset === key;

  return (
    <header className="pb-6 flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
      {/* Left: Title + Subtitle */}
      <div className="flex flex-col gap-1">
        <h1 className="text-xl md:text-2xl font-semibold tracking-tight text-neutral-900">
          Finance & P&L
        </h1>
        <p className="text-xs md:text-sm text-neutral-500 font-medium">
          See how your ad spend turns into profit.
        </p>
      </div>

      {/* Right: Date Range Picker */}
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <button
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium",
              "bg-white border border-neutral-200",
              "hover:bg-neutral-50 hover:border-neutral-300 transition-all duration-150",
              "text-neutral-700 shadow-sm",
              "focus:outline-none focus:ring-2 focus:ring-neutral-900/10"
            )}
          >
            <CalendarIcon className="w-4 h-4 text-neutral-400" />
            <span>{getDisplayLabel()}</span>
          </button>
        </PopoverTrigger>
        <PopoverContent
          className="w-auto p-0 bg-white border-neutral-200 shadow-xl rounded-xl overflow-hidden z-[10000]"
          align="end"
          sideOffset={8}
        >
          {/* Preset Chips */}
          <div className="px-4 pt-4 pb-3 border-b border-neutral-100">
            <div className="flex flex-wrap gap-2">
              {PRESETS.map((presetOption) => (
                <button
                  key={presetOption.key}
                  onClick={() => handlePresetClick(presetOption.key)}
                  className={cn(
                    "px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-150",
                    isPresetSelected(presetOption.key)
                      ? "bg-neutral-900 text-white"
                      : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200"
                  )}
                >
                  {presetOption.shortLabel}
                </button>
              ))}
              {localPreset === 'custom' && (
                <span className="px-3 py-1.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700">
                  Custom
                </span>
              )}
            </div>
          </div>

          {/* Calendar */}
          <div className="p-2">
            <Calendar
              mode="range"
              selected={localRange}
              onSelect={handleDateSelect}
              numberOfMonths={isDesktop ? 2 : 1}
              disabled={{ after: new Date() }}
              defaultMonth={localRange?.from || subMonths(new Date(), 1)}
            />
          </div>

          {/* Selected Range Display */}
          {localRange?.from && (
            <div className="px-4 py-2 border-t border-neutral-100 bg-neutral-50/50">
              <p className="text-xs text-neutral-500">
                {localRange.to && !isSameDay(localRange.from, localRange.to) ? (
                  <>
                    <span className="font-medium text-neutral-700">{format(localRange.from, 'MMM d, yyyy')}</span>
                    <span className="mx-1.5">→</span>
                    <span className="font-medium text-neutral-700">{format(localRange.to, 'MMM d, yyyy')}</span>
                  </>
                ) : (
                  <span className="font-medium text-neutral-700">{format(localRange.from, 'MMMM d, yyyy')}</span>
                )}
              </p>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex items-center justify-end gap-2 px-4 py-3 border-t border-neutral-100 bg-neutral-50/30">
            <button
              onClick={handleCancel}
              className="px-3 py-1.5 text-xs font-medium text-neutral-600 hover:text-neutral-900 hover:bg-neutral-100 rounded-md transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleApply}
              disabled={!localRange?.from}
              className={cn(
                "px-4 py-1.5 text-xs font-medium rounded-md transition-colors",
                localRange?.from
                  ? "bg-neutral-900 text-white hover:bg-neutral-800"
                  : "bg-neutral-200 text-neutral-400 cursor-not-allowed"
              )}
            >
              Apply
            </button>
          </div>
        </PopoverContent>
      </Popover>
    </header>
  );
}
