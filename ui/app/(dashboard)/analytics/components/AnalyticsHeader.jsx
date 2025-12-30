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
    <header className="pb-6">
      <div className="flex items-center justify-between">
        {/* Left: Title + Subtitle + Filter Badge */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-semibold tracking-tight text-neutral-900">
              Analytics
            </h1>
            <span className="text-sm text-neutral-500">
              Performance Deep-dive
            </span>
          </div>

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

        {/* Right: Filters */}
        <div className="flex items-center gap-3">
          {/* Platform Dropdown */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                className="h-9 px-3 bg-white border-neutral-200 text-neutral-700 hover:bg-neutral-50 hover:border-neutral-300"
              >
                <span>Platform: {currentPlatformLabel.replace(" Ads", "")}</span>
                <ChevronDown className="w-4 h-4 ml-2 bg-white text-neutral-400" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-40">
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
            className={`h-9 px-3 gap-2 ${compareEnabled
              ? "bg-neutral-900 text-white hover:bg-neutral-800"
              : "bg-white border-neutral-200 text-neutral-700 hover:bg-neutral-50 hover:border-neutral-300"
              }`}
          >
            <GitCompare className="w-4 h-4" />
            <span className="hidden sm:inline">Compare</span>
          </Button>

          {/* Export Button */}
          <Button
            variant="ghost"
            size="sm"
            onClick={onExport}
            disabled={loading}
            className="h-9 w-9 p-0 text-neutral-400 hover:text-neutral-900"
            aria-label="Export data"
          >
            <Download className="w-5 h-5" />
          </Button>
        </div>
      </div>
    </header>
  );
}
