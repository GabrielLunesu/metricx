/**
 * TimeframeSelector - Subtle timeframe picker
 * 
 * WHAT: Small dropdown/pill selector for dashboard timeframe
 * WHY: Users need to switch time periods without it being too prominent
 * 
 * CHANGES (2025-12-30):
 *   - Smaller, more subtle design
 *   - Neutral colors to match new design system
 *   - Simplified layout (no icon)
 */

import React from 'react';

export default function TimeframeSelector({ value, onChange }) {
    const options = [
        { label: 'Today', value: 'today' },
        { label: 'Yesterday', value: 'yesterday' },
        { label: '7 Days', value: 'last_7_days' },
        { label: '30 Days', value: 'last_30_days' },
    ];

    return (
        <div className="flex items-center gap-1 bg-white/50 backdrop-blur-sm border border-neutral-200/60 rounded-full p-1">
            {options.map((option) => (
                <button
                    key={option.value}
                    onClick={() => onChange(option.value)}
                    className={`
                        px-3 py-1 text-xs font-medium rounded-full transition-all duration-200
                        ${value === option.value
                            ? 'bg-neutral-900 text-white'
                            : 'text-neutral-500 hover:text-neutral-900 hover:bg-white/60'
                        }
                    `}
                >
                    {option.label}
                </button>
            ))}
        </div>
    );
}
