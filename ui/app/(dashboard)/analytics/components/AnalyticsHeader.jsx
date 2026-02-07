"use client";

/**
 * AnalyticsHeader - Sticky glass header with global filters
 * 
 * WHAT: Fixed header containing page title, platform filter, date picker,
 *       compare toggle, export button, and active filter badges
 * WHY: Provides consistent access to filters while scrolling through data
 * 
 * FEATURES:
 *   - Platform dropdown (All / Meta / Google)
 *   - Date range picker with presets
 *   - Compare toggle (current vs previous period)
 *   - Export button
 *   - Filter badge when campaigns are selected
 * 
 * REFERENCES:
 *   - Metricx v3.0 design system
 *   - ui/components/ui/date-range-picker.jsx
 */

import { Calendar, ChevronDown, Download, GitCompare, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { DateRangePicker } from "@/components/ui/date-range-picker";

/**
 * Platform options for the dropdown filter
 */
const PLATFORM_OPTIONS = [
  { value: null, label: "All Platforms" },
  { value: "meta", label: "Meta Ads" },
  { value: "google", label: "Google Ads" },
];

export default function AnalyticsHeader({
  // Platform filter
  selectedPlatform,
  onPlatformChange,
  connectedPlatforms = [],
  // Date range
  preset,
  onPresetChange,
  dateRange,
  onDateRangeChange,
  // Compare mode
  compareEnabled,
  onCompareToggle,
  // Campaign selection
  selectedCampaigns = [],
  onClearCampaigns,
  // Export
  onExport,
  // Loading state
  loading = false,
}) {
  // Get current platform label
  const currentPlatformLabel = PLATFORM_OPTIONS.find(
    (p) => p.value === selectedPlatform
  )?.label || "All Platforms";

  // Filter platform options to only show connected platforms
  const availablePlatforms = PLATFORM_OPTIONS.filter(
    (p) => p.value === null || connectedPlatforms.includes(p.value)
  );

  return (
    <header className="pb-4 md:pb-6">
      {/* Title Row */}
      <div className="flex items-center justify-between mb-3 md:mb-4">
        <div className="flex items-center gap-2 md:gap-4">
          <h1 className="text-lg md:text-xl font-semibold tracking-tight text-neutral-900">
            Analytics
          </h1>
          {/* Filter badge when campaigns selected */}
          {selectedCampaigns.length > 0 && (
            <div className="filter-badge">
              <span>
                {selectedCampaigns.length} campaign{selectedCampaigns.length > 1 ? "s" : ""} selected
              </span>
              <button
                onClick={onClearCampaigns}
                aria-label="Clear campaign filter"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          )}
        </div>

        {/* Desktop-only export */}
        <Button
          variant="ghost"
          size="sm"
          onClick={onExport}
          disabled={loading}
          className="h-8 w-8 p-0 text-neutral-400 hover:text-neutral-900 hidden md:flex"
          aria-label="Export data"
        >
          <Download className="w-4 h-4" />
        </Button>
      </div>

      {/* Filters Row - scrollable on mobile */}
      <div className="flex items-center gap-2 overflow-x-auto no-scrollbar pb-1">
        {/* Platform Dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              className="h-8 px-2.5 text-xs bg-white border-neutral-200 text-neutral-700 hover:bg-neutral-50 hover:border-neutral-300 shrink-0"
            >
              <span>{currentPlatformLabel.replace(" Ads", "")}</span>
              <ChevronDown className="w-3.5 h-3.5 ml-1.5 text-neutral-400" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-40">
            {availablePlatforms.map((platform) => (
              <DropdownMenuItem
                key={platform.value || "all"}
                onClick={() => onPlatformChange(platform.value)}
                className={
                  selectedPlatform === platform.value
                    ? "bg-white font-medium"
                    : ""
                }
              >
                {platform.label}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Date Range Picker */}
        <DateRangePicker
          preset={preset}
          onPresetChange={onPresetChange}
          dateRange={dateRange}
          onDateRangeChange={onDateRangeChange}
        />

        {/* Compare Toggle */}
        <Button
          variant={compareEnabled ? "default" : "outline"}
          size="sm"
          onClick={onCompareToggle}
          className={`h-8 px-2.5 text-xs gap-1.5 shrink-0 ${compareEnabled
            ? "bg-neutral-900 text-white hover:bg-neutral-800"
            : "bg-white border-neutral-200 text-neutral-700 hover:bg-neutral-50 hover:border-neutral-300"
            }`}
        >
          <GitCompare className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Compare</span>
        </Button>

        {/* Mobile export */}
        <Button
          variant="ghost"
          size="sm"
          onClick={onExport}
          disabled={loading}
          className="h-8 w-8 p-0 text-neutral-400 hover:text-neutral-900 shrink-0 md:hidden"
          aria-label="Export data"
        >
          <Download className="w-4 h-4" />
        </Button>
      </div>
    </header>
  );
}
