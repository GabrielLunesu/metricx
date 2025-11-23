import React from 'react';
import { Calendar } from 'lucide-react';

export default function TimeframeSelector({ value, onChange }) {
    const options = [
        { label: 'Today', value: 'today' },
        { label: 'Yesterday', value: 'yesterday' },
        { label: 'Last 7 Days', value: 'last_7_days' },
        { label: 'Last 30 Days', value: 'last_30_days' },
    ];

    return (
        <div className="flex items-center space-x-2 bg-white/40 backdrop-blur-md border border-white/50 rounded-full p-1 shadow-sm max-w-[90vw] md:max-w-full overflow-hidden">
            <div className="pl-3 pr-1 text-slate-500 flex-shrink-0">
                <Calendar size={16} />
            </div>
            <div className="flex space-x-1 overflow-x-auto no-scrollbar">
                {options.map((option) => (
                    <button
                        key={option.value}
                        onClick={() => onChange(option.value)}
                        className={`
              px-3 py-1.5 text-sm font-medium rounded-full transition-all duration-300 whitespace-nowrap flex-shrink-0
              ${value === option.value
                                ? 'bg-white text-cyan-700 shadow-sm'
                                : 'text-slate-600 hover:bg-white/50 hover:text-slate-800'
                            }
            `}
                    >
                        {option.label}
                    </button>
                ))}
            </div>
        </div>
    );
}
