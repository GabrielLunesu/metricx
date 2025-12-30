/**
 * CampaignFilters Component
 * =========================
 *
 * WHAT: Filter bar with platform, status, date picker, and search
 * WHY: Unified filtering controls for campaigns page
 *
 * REFERENCES:
 *   - Metricx v3.0 design system
 *   - ui/components/ui/date-range-picker.jsx
 */

"use client";

import * as React from "react";
import { format, startOfDay, endOfDay, subDays, isSameDay } from "date-fns";
import { Calendar as CalendarIcon, ChevronDown, Search, LayoutTemplate } from "lucide-react";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/cn";

/**
 * Date range presets for campaigns
 */
const DATE_PRESETS = [
  {
    key: "today",
    label: "Today",
    shortLabel: "Today",
    getDates: () => ({
      from: startOfDay(new Date()),
      to: endOfDay(new Date()),
    }),
  },
  {
    key: "yesterday",
    label: "Yesterday",
    shortLabel: "Yesterday",
    getDates: () => ({
      from: startOfDay(subDays(new Date(), 1)),
      to: endOfDay(subDays(new Date(), 1)),
    }),
  },
  {
    key: "last_7_days",
    label: "Last 7 Days",
    shortLabel: "7D",
    getDates: () => ({
      from: startOfDay(subDays(new Date(), 6)),
      to: endOfDay(new Date()),
    }),
  },
  {
    key: "last_30_days",
    label: "Last 30 Days",
    shortLabel: "30D",
    getDates: () => ({
      from: startOfDay(subDays(new Date(), 29)),
      to: endOfDay(new Date()),
    }),
  },
  {
    key: "last_90_days",
    label: "Last 90 Days",
    shortLabel: "90D",
    getDates: () => ({
      from: startOfDay(subDays(new Date(), 89)),
      to: endOfDay(new Date()),
    }),
  },
];

/**
 * Status filter options
 */
const STATUS_OPTIONS = [
  { key: "active", label: "Active" },
  { key: "all", label: "All Status" },
  { key: "paused", label: "Paused" },
];

/**
 * CampaignFilters - Filter bar component for campaigns page.
 *
 * @param {Object} props
 * @param {string[]} props.platforms - Available platforms
 * @param {string|null} props.selectedPlatform - Currently selected platform
 * @param {Function} props.onPlatformChange - Platform change handler
 * @param {string} props.selectedStatus - Currently selected status
 * @param {Function} props.onStatusChange - Status change handler
 * @param {Object} props.dateRange - { from: Date, to: Date }
 * @param {Function} props.onDateRangeChange - Date range change handler
 * @param {string} props.searchQuery - Current search query
 * @param {Function} props.onSearchChange - Search change handler
 */
export default function CampaignFilters({
  platforms = [],
  selectedPlatform,
  onPlatformChange,
  selectedStatus = "active",
  onStatusChange,
  dateRange,
  onDateRangeChange,
  searchQuery = "",
  onSearchChange,
}) {
  // Date picker state
  const [dateOpen, setDateOpen] = React.useState(false);
  const [localRange, setLocalRange] = React.useState(dateRange);
  const [localPreset, setLocalPreset] = React.useState("last_7_days");

  // Platform dropdown state
  const [platformOpen, setPlatformOpen] = React.useState(false);

  // Detect current preset based on dateRange
  React.useEffect(() => {
    if (!dateRange?.from || !dateRange?.to) return;

    for (const preset of DATE_PRESETS) {
      const presetDates = preset.getDates();
      if (
        isSameDay(dateRange.from, presetDates.from) &&
        isSameDay(dateRange.to, presetDates.to)
      ) {
        setLocalPreset(preset.key);
        return;
      }
    }
    setLocalPreset("custom");
  }, [dateRange]);

  // Sync local state when popover opens
  React.useEffect(() => {
    if (dateOpen) {
      setLocalRange(dateRange);
    }
  }, [dateOpen, dateRange]);

  // Get display label for date button
  const getDateDisplayLabel = () => {
    if (localPreset && localPreset !== "custom") {
      const presetConfig = DATE_PRESETS.find((p) => p.key === localPreset);
      return presetConfig?.label || "Select dates";
    }
    if (dateRange?.from && dateRange?.to) {
      if (isSameDay(dateRange.from, dateRange.to)) {
        return format(dateRange.from, "MMM d, yyyy");
      }
      const fromStr = format(dateRange.from, "MMM d");
      const toStr = format(dateRange.to, "MMM d");
      return `${fromStr} - ${toStr}`;
    }
    return "Last 7 Days";
  };

  // Handle preset click
  const handlePresetClick = (presetKey) => {
    setLocalPreset(presetKey);
    const presetConfig = DATE_PRESETS.find((p) => p.key === presetKey);
    if (presetConfig) {
      setLocalRange(presetConfig.getDates());
    }
  };

  // Handle calendar date selection
  const handleDateSelect = (range) => {
    if (!range) return;
    setLocalPreset("custom");
    setLocalRange(range);
  };

  // Apply date selection
  const handleDateApply = () => {
    if (localRange?.from) {
      const finalRange = {
        from: localRange.from,
        to: localRange.to || localRange.from,
      };
      onDateRangeChange?.(finalRange);
      setDateOpen(false);
    }
  };

  // Cancel date selection
  const handleDateCancel = () => {
    setLocalRange(dateRange);
    setDateOpen(false);
  };

  return (
    <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
      {/* Left: Filters */}
      <div className="flex items-center gap-3 w-full lg:w-auto overflow-x-auto no-scrollbar pb-1 lg:pb-0">
        {/* Platform Filter */}
        <Popover open={platformOpen} onOpenChange={setPlatformOpen}>
          <PopoverTrigger asChild>
            <button className="flex items-center gap-2 px-3 py-2 bg-white border border-neutral-200 rounded-md text-sm font-medium text-neutral-700 hover:border-neutral-300 hover:bg-neutral-50 transition-all shadow-sm">
              <LayoutTemplate className="w-4 h-4 text-neutral-400" />
              <span>{selectedPlatform ? selectedPlatform.charAt(0).toUpperCase() + selectedPlatform.slice(1) : "All Platforms"}</span>
              <ChevronDown className="w-3.5 h-3.5 text-neutral-400" />
            </button>
          </PopoverTrigger>
          <PopoverContent className="w-40 p-1 bg-white" align="start">
            <button
              onClick={() => {
                onPlatformChange(null);
                setPlatformOpen(false);
              }}
              className={cn(
                "w-full px-3 py-2 text-sm text-left rounded-md transition-colors",
                selectedPlatform === null
                  ? "bg-neutral-100 text-neutral-900 font-medium"
                  : "text-neutral-600 hover:bg-neutral-50"
              )}
            >
              All Platforms
            </button>
            {platforms.map((platform) => (
              <button
                key={platform}
                onClick={() => {
                  onPlatformChange(platform);
                  setPlatformOpen(false);
                }}
                className={cn(
                  "w-full px-3 py-2 text-sm text-left rounded-md capitalize transition-colors",
                  selectedPlatform === platform
                    ? "bg-neutral-100 text-neutral-900 font-medium"
                    : "text-neutral-600 hover:bg-neutral-50"
                )}
              >
                {platform}
              </button>
            ))}
          </PopoverContent>
        </Popover>

        {/* Status Filter */}
        <div className="flex items-center bg-white border border-neutral-200 rounded-md shadow-sm">
          {STATUS_OPTIONS.map((option) => (
            <button
              key={option.key}
              onClick={() => onStatusChange(option.key)}
              className={cn(
                "px-3 py-2 text-sm font-medium transition-all first:rounded-l-md last:rounded-r-md",
                selectedStatus === option.key
                  ? option.key === "active"
                    ? "bg-emerald-50 text-emerald-700"
                    : "bg-neutral-100 text-neutral-900"
                  : "text-neutral-500 hover:text-neutral-700 hover:bg-neutral-50"
              )}
            >
              {option.key === "active" && (
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1.5" />
              )}
              {option.label}
            </button>
          ))}
        </div>

        {/* Divider */}
        <div className="h-6 w-px bg-neutral-200 mx-1" />

        {/* Date Filter */}
        <Popover open={dateOpen} onOpenChange={setDateOpen}>
          <PopoverTrigger asChild>
            <button className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-neutral-500 hover:text-neutral-900 transition-colors">
              <span>{getDateDisplayLabel()}</span>
              <CalendarIcon className="w-4 h-4" />
            </button>
          </PopoverTrigger>
          <PopoverContent
            className="w-auto p-0 bg-white border-neutral-200 shadow-xl rounded-xl overflow-hidden z-[10000]"
            align="start"
            sideOffset={8}
          >
            {/* Preset Chips */}
            <div className="px-4 pt-4 pb-3 border-b border-neutral-100">
              <div className="flex flex-wrap gap-2">
                {DATE_PRESETS.map((preset) => (
                  <button
                    key={preset.key}
                    onClick={() => handlePresetClick(preset.key)}
                    className={cn(
                      "px-3 py-1.5 rounded-full text-xs font-medium transition-all",
                      localPreset === preset.key
                        ? "bg-neutral-900 text-white"
                        : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200"
                    )}
                  >
                    {preset.shortLabel}
                  </button>
                ))}
                {localPreset === "custom" && (
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
                numberOfMonths={2}
                disabled={{ after: new Date() }}
                defaultMonth={localRange?.from || subDays(new Date(), 30)}
              />
            </div>

            {/* Selected Range Display */}
            {localRange?.from && (
              <div className="px-4 py-2 border-t border-neutral-100 bg-neutral-50/50">
                <p className="text-xs text-neutral-500">
                  {localRange.to && !isSameDay(localRange.from, localRange.to) ? (
                    <>
                      <span className="font-medium text-neutral-700">
                        {format(localRange.from, "MMM d, yyyy")}
                      </span>
                      <span className="mx-1.5">→</span>
                      <span className="font-medium text-neutral-700">
                        {format(localRange.to, "MMM d, yyyy")}
                      </span>
                    </>
                  ) : (
                    <span className="font-medium text-neutral-700">
                      {format(localRange.from, "MMMM d, yyyy")}
                    </span>
                  )}
                </p>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex items-center justify-end gap-2 px-4 py-3 border-t border-neutral-100 bg-neutral-50/30">
              <button
                onClick={handleDateCancel}
                className="px-3 py-1.5 text-xs font-medium text-neutral-600 hover:text-neutral-900 hover:bg-neutral-100 rounded-md transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleDateApply}
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
      </div>

      {/* Right: Search */}
      <div className="relative w-full lg:w-80 group">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <Search className="w-4 h-4 text-neutral-400 group-focus-within:text-neutral-600 transition-colors" />
        </div>
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="block w-full pl-10 pr-12 py-2 border border-neutral-200 rounded-md leading-5 bg-white placeholder-neutral-400 text-sm focus:outline-none focus:ring-1 focus:ring-neutral-300 focus:border-neutral-400 transition-all shadow-sm"
          placeholder="Search campaigns..."
        />
        <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
          <span className="text-xs text-neutral-300 font-sans border border-neutral-200 rounded px-1.5 py-0.5">
            ⌘K
          </span>
        </div>
      </div>
    </div>
  );
}
