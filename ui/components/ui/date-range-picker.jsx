"use client";
/**
 * DateRangePicker Component (v2.0 - Compact & Polished)
 * ======================================================
 *
 * WHAT: A compact date picker supporting both single date and date range selection
 * WHY: Clean UX for analytics filtering with quick presets and custom selection
 *
 * FEATURES:
 *   - Preset quick-select chips (Today, 7D, 30D, 90D)
 *   - Single calendar with range selection
 *   - Compact trigger showing selected range
 *   - Apply/Cancel buttons for explicit confirmation
 *
 * RELATED:
 *   - components/ui/calendar.jsx (shadcn calendar)
 *   - components/ui/popover.jsx (shadcn popover)
 */
import * as React from "react";
import { format, subDays, startOfDay, endOfDay, isSameDay } from "date-fns";
import { Calendar as CalendarIcon } from "lucide-react";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/cn";

/**
 * Preset date range options - compact labels for chips.
 */
const PRESETS = [
    { key: 'today', label: 'Today', shortLabel: 'Today', getDates: () => ({ from: startOfDay(new Date()), to: endOfDay(new Date()) }) },
    { key: 'yesterday', label: 'Yesterday', shortLabel: 'Yest', getDates: () => ({ from: startOfDay(subDays(new Date(), 1)), to: endOfDay(subDays(new Date(), 1)) }) },
    { key: 'last_7_days', label: 'Last 7 Days', shortLabel: '7D', getDates: () => ({ from: startOfDay(subDays(new Date(), 6)), to: endOfDay(new Date()) }) },
    { key: 'last_30_days', label: 'Last 30 Days', shortLabel: '30D', getDates: () => ({ from: startOfDay(subDays(new Date(), 29)), to: endOfDay(new Date()) }) },
    { key: 'last_90_days', label: 'Last 90 Days', shortLabel: '90D', getDates: () => ({ from: startOfDay(subDays(new Date(), 89)), to: endOfDay(new Date()) }) },
];

/**
 * DateRangePicker component.
 *
 * @param {Object} props
 * @param {string} props.preset - Current preset key
 * @param {Function} props.onPresetChange - Callback when preset changes
 * @param {Object} props.dateRange - Date range { from: Date, to: Date }
 * @param {Function} props.onDateRangeChange - Callback when date range changes
 * @param {string} props.className - Additional CSS classes
 */
export function DateRangePicker({
    preset,
    onPresetChange,
    dateRange,
    onDateRangeChange,
    className
}) {
    const [open, setOpen] = React.useState(false);
    const [localRange, setLocalRange] = React.useState(dateRange);
    const [localPreset, setLocalPreset] = React.useState(preset);

    // Sync local state when props change (when popover opens)
    React.useEffect(() => {
        if (open) {
            setLocalRange(dateRange);
            setLocalPreset(preset);
        }
    }, [open, dateRange, preset]);

    // Get display label for trigger button
    const getDisplayLabel = () => {
        if (preset && preset !== 'custom') {
            const presetConfig = PRESETS.find(p => p.key === preset);
            return presetConfig?.label || 'Select dates';
        }
        if (dateRange?.from && dateRange?.to) {
            if (isSameDay(dateRange.from, dateRange.to)) {
                return format(dateRange.from, 'MMM d, yyyy');
            }
            const fromStr = format(dateRange.from, 'MMM d');
            const toStr = format(dateRange.to, 'MMM d');
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

        // If user selects a range, mark as custom
        setLocalPreset('custom');
        setLocalRange(range);
    };

    // Apply selection
    const handleApply = () => {
        if (localRange?.from) {
            // Ensure we have both from and to (for single date, to = from)
            const finalRange = {
                from: localRange.from,
                to: localRange.to || localRange.from
            };
            onPresetChange?.(localPreset);
            onDateRangeChange?.(finalRange);
            setOpen(false);
        }
    };

    // Cancel and reset
    const handleCancel = () => {
        setLocalRange(dateRange);
        setLocalPreset(preset);
        setOpen(false);
    };

    // Check if a preset is selected
    const isPresetSelected = (key) => localPreset === key;

    return (
        <Popover open={open} onOpenChange={setOpen}>
            <PopoverTrigger asChild>
                <button
                    className={cn(
                        "flex z-[9999] items-center gap-2 px-3 py-2 rounded-lg text-[13px] font-medium",
                        "bg-white border border-slate-200",
                        "hover:bg-slate-50 hover:border-slate-300 transition-all duration-150",
                        "text-slate-700 shadow-sm",
                        "focus:outline-none focus:ring-2 focus:ring-slate-900/10",
                        className
                    )}
                >
                    <CalendarIcon className="w-4 h-4 text-slate-400" />
                    <span>{getDisplayLabel()}</span>
                </button>
            </PopoverTrigger>
            <PopoverContent
                className="w-auto p-0 bg-white border-slate-200 shadow-xl rounded-xl overflow-hidden z-[10000]"
                align="end"
                sideOffset={8}
            >
                {/* Preset Chips */}
                <div className="px-4 pt-4 pb-3 border-b border-slate-100">
                    <div className="flex flex-wrap gap-1.5">
                        {PRESETS.map((presetOption) => (
                            <button
                                key={presetOption.key}
                                onClick={() => handlePresetClick(presetOption.key)}
                                className={cn(
                                    "px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-150",
                                    isPresetSelected(presetOption.key)
                                        ? "bg-slate-900 text-white"
                                        : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                                )}
                            >
                                {presetOption.shortLabel}
                            </button>
                        ))}
                        {localPreset === 'custom' && (
                            <span className="px-3 py-1.5 rounded-full text-xs font-medium bg-cyan-100 text-cyan-700">
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
                        numberOfMonths={1}
                        disabled={{ after: new Date() }}
                        defaultMonth={localRange?.from || new Date()}
                    />
                </div>

                {/* Selected Range Display */}
                {localRange?.from && (
                    <div className="px-4 py-2 border-t border-slate-100 bg-slate-50/50">
                        <p className="text-xs text-slate-500">
                            {localRange.to && !isSameDay(localRange.from, localRange.to) ? (
                                <>
                                    <span className="font-medium text-slate-700">{format(localRange.from, 'MMM d, yyyy')}</span>
                                    <span className="mx-1.5">→</span>
                                    <span className="font-medium text-slate-700">{format(localRange.to, 'MMM d, yyyy')}</span>
                                </>
                            ) : (
                                <span className="font-medium text-slate-700">{format(localRange.from, 'MMMM d, yyyy')}</span>
                            )}
                        </p>
                    </div>
                )}

                {/* Action Buttons */}
                <div className="flex items-center justify-end gap-2 px-4 py-3 border-t border-slate-100 bg-slate-50/30">
                    <button
                        onClick={handleCancel}
                        className="px-3 py-1.5 text-xs font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-md transition-colors"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleApply}
                        disabled={!localRange?.from}
                        className={cn(
                            "px-4 py-1.5 text-xs font-medium rounded-md transition-colors",
                            localRange?.from
                                ? "bg-slate-900 text-white hover:bg-slate-800"
                                : "bg-slate-200 text-slate-400 cursor-not-allowed"
                        )}
                    >
                        Apply
                    </button>
                </div>
            </PopoverContent>
        </Popover>
    );
}

export { PRESETS };
