'use client';

/**
 * AttributionCardUnified Component
 *
 * WHAT: Shows attribution summary using unified dashboard data
 * WHY: Uses pre-fetched attribution_summary instead of separate API call
 */

export default function AttributionCardUnified({ data, loading }) {
    if (loading || !data) {
        return (
            <div className="glass-panel rounded-2xl p-4 animate-pulse h-48">
                <div className="h-full bg-slate-100 rounded"></div>
            </div>
        );
    }

    const summary = data.attribution_summary || [];

    if (summary.length === 0) {
        return (
            <div className="glass-panel rounded-2xl p-6">
                <h3 className="text-lg font-medium mb-4 text-slate-800">Attribution</h3>
                <p className="text-slate-500">No attribution data available yet</p>
            </div>
        );
    }

    const totalRevenue = summary.reduce((sum, item) => sum + (item.revenue || 0), 0);
    const totalOrders = summary.reduce((sum, item) => sum + (item.orders || 0), 0);

    return (
        <div className="glass-panel rounded-2xl p-6">
            <h3 className="text-lg font-medium mb-4 text-slate-800">Attribution by Channel</h3>

            {/* Summary stats */}
            <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                    <p className="text-2xl font-semibold text-cyan-600">
                        ${totalRevenue.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </p>
                    <p className="text-sm text-slate-500">Attributed Revenue</p>
                </div>
                <div>
                    <p className="text-2xl font-semibold text-purple-600">
                        {totalOrders.toLocaleString()}
                    </p>
                    <p className="text-sm text-slate-500">Attributed Orders</p>
                </div>
            </div>

            {/* Channel breakdown */}
            <div className="space-y-2">
                {summary.slice(0, 5).map((item, i) => (
                    <div key={item.channel || i} className="flex items-center gap-3">
                        <div className="flex-1">
                            <div className="flex justify-between text-sm mb-1">
                                <span className="capitalize text-slate-700">{item.channel}</span>
                                <span className="text-slate-500">{item.pct?.toFixed(1)}%</span>
                            </div>
                            <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                                <div
                                    className="h-full bg-cyan-500 rounded-full"
                                    style={{ width: `${item.pct || 0}%` }}
                                />
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
