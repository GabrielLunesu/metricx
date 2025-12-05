'use client';

/**
 * SpendMixUnified Component
 *
 * WHAT: Shows spend breakdown by platform using unified dashboard data
 * WHY: Uses pre-fetched spend_mix instead of QA endpoint (which called AI!)
 */

const providerColors = {
    meta: 'bg-blue-500',
    google: 'bg-red-500',
    tiktok: 'bg-slate-800',
    unknown: 'bg-slate-400'
};

export default function SpendMixUnified({ data, loading }) {
    if (loading || !data) {
        return (
            <div className="glass-panel rounded-2xl p-4 animate-pulse h-32">
                <div className="h-full bg-slate-100 rounded"></div>
            </div>
        );
    }

    const spendMix = data.spend_mix || [];

    if (spendMix.length === 0) {
        return (
            <div className="glass-panel rounded-2xl p-4">
                <p className="text-slate-500">No spend data available</p>
            </div>
        );
    }

    const total = spendMix.reduce((sum, item) => sum + (item.spend || 0), 0);

    return (
        <div className="glass-panel rounded-2xl p-4">
            {/* Stacked bar */}
            <div className="h-4 rounded-full overflow-hidden flex">
                {spendMix.map((item, i) => (
                    <div
                        key={item.provider || i}
                        className={`${providerColors[item.provider] || providerColors.unknown}`}
                        style={{ width: `${item.pct || 0}%` }}
                        title={`${item.provider}: ${item.pct?.toFixed(1)}%`}
                    />
                ))}
            </div>

            {/* Legend */}
            <div className="flex flex-wrap gap-4 mt-3">
                {spendMix.map((item, i) => (
                    <div key={item.provider || i} className="flex items-center gap-2">
                        <div className={`w-3 h-3 rounded-full ${providerColors[item.provider] || providerColors.unknown}`}></div>
                        <span className="text-sm text-slate-600 capitalize">{item.provider}</span>
                        <span className="text-sm font-medium text-slate-800">
                            ${item.spend?.toLocaleString(undefined, { maximumFractionDigits: 0 }) || '0'}
                        </span>
                        <span className="text-xs text-slate-400">({item.pct?.toFixed(1) || 0}%)</span>
                    </div>
                ))}
            </div>
        </div>
    );
}
