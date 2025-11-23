'use client';

import { useEffect, useState } from "react";
import { fetchQA } from "@/lib/api";

const normalizeProviderLabel = (label) => {
    if (!label) return label;
    const lowered = String(label).toLowerCase();
    // Common case: "ProviderEnum.meta" → "meta"
    if (lowered.includes("providerenum")) {
        return lowered.split(".").pop();
    }
    // Fallback: take last segment if any dotted string
    if (lowered.includes(".")) {
        return lowered.split(".").pop();
    }
    return lowered;
};

export default function PlatformSpendMix({ workspaceId, timeframe }) {
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!workspaceId) return;

        let mounted = true;

        const loadData = async () => {
            setLoading(true);
            setError(null);
            try {
                let timeStr = "last 7 days";
                switch (timeframe) {
                    case 'today': timeStr = "today"; break;
                    case 'yesterday': timeStr = "yesterday"; break;
                    case 'last_7_days': timeStr = "last 7 days"; break;
                    case 'last_30_days': timeStr = "last 30 days"; break;
                }

                const question = `What is my spend by provider ${timeStr}?`;
                const res = await fetchQA({ workspaceId, question });

                if (!mounted) return;

                // QA returns data.breakdown = [{ label: "Google", value: 123 }, ...]
                if (res.data && res.data.breakdown) {
                    const total = res.data.breakdown.reduce((sum, item) => sum + item.value, 0);
                    const processed = res.data.breakdown.map(item => ({
                        provider: normalizeProviderLabel(item.label),
                        value: item.value,
                        pct: total > 0 ? (item.value / total) * 100 : 0
                    }));
                    setData(processed);
                } else {
                    setData([]);
                }
            } catch (err) {
                console.error("Failed to fetch Platform Spend Mix:", err);
                if (mounted) {
                    setError(err.message);
                }
            } finally {
                if (mounted) {
                    setLoading(false);
                }
            }
        };

        loadData();

        return () => { mounted = false; };
    }, [workspaceId, timeframe]);

    if (loading) {
        return (
            <div className="glass-panel p-6 rounded-3xl mb-2 h-[200px] flex items-center justify-center animate-pulse">
                <div className="w-full h-full bg-slate-100/50 rounded-xl"></div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="glass-panel p-6 rounded-3xl mb-2 h-[200px] flex items-center justify-center">
                <p className="text-red-500 text-sm">Failed to load: {error}</p>
            </div>
        );
    }

    if (!data || data.length === 0) {
        return (
            <div className="glass-panel p-6 rounded-3xl mb-2 h-[200px] flex items-center justify-center">
                <p className="text-slate-400 text-sm">No spend data available</p>
            </div>
        );
    }

    return (
        <div className="glass-panel p-6 rounded-3xl mb-2 h-[200px] flex items-center justify-center">
            <div className="flex items-end gap-12 h-32 w-full px-8 justify-center">
                {data.map((item) => {
                    const isGoogle = item.provider.toLowerCase().includes('google');
                    const colorClass = isGoogle
                        ? "from-blue-500 to-cyan-400 shadow-[0_0_15px_rgba(6,182,212,0.4)]"
                        : "from-blue-600 to-indigo-500 shadow-[0_0_15px_rgba(99,102,241,0.4)]";

                    return (
                        <div key={item.provider} className="flex flex-col items-center gap-3 group w-24">
                            <div className="w-full bg-slate-100 rounded-t-xl relative h-32 overflow-hidden shadow-inner">
                                <div
                                    className={`absolute bottom-0 left-0 w-full bg-gradient-to-t ${colorClass} transition-all duration-700`}
                                    style={{ height: `${Math.max(item.pct, 5)}%` }}
                                >
                                    <div className="absolute top-0 w-full h-[2px] bg-white/50"></div>
                                </div>
                            </div>
                            <span className="text-xs font-bold text-slate-500 tracking-wide text-center truncate w-full capitalize">
                                {item.provider} ({Math.round(item.pct)}%)
                            </span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
