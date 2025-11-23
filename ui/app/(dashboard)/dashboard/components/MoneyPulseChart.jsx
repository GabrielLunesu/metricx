'use client';

import { useEffect, useRef, useState } from "react";
import Chart from "chart.js/auto";
import { fetchWorkspaceKpis } from "@/lib/api";

export default function MoneyPulseChart({ workspaceId, timeframe }) {
    const chartRef = useRef(null);
    const canvasRef = useRef(null);
    const [loading, setLoading] = useState(true);
    const [viewMode, setViewMode] = useState('overview'); // 'overview' | 'breakdown'
    const [chartData, setChartData] = useState(null);

    // Fetch Data
    useEffect(() => {
        if (!workspaceId) return;

        const loadData = async () => {
            setLoading(true);
            try {
                // Map timeframe to API params
                let lastNDays = 7;
                let dayOffset = 0;

                switch (timeframe) {
                    case 'today':
                        lastNDays = 1;
                        dayOffset = 0;
                        break;
                    case 'yesterday':
                        lastNDays = 1;
                        dayOffset = 1;
                        break;
                    case 'last_7_days':
                        lastNDays = 7;
                        dayOffset = 0;
                        break;
                    case 'last_30_days':
                        lastNDays = 30;
                        dayOffset = 0;
                        break;
                    default:
                        lastNDays = 7;
                }

                const metrics = ["revenue", "spend"];
                const res = await fetchWorkspaceKpis({
                    workspaceId,
                    metrics,
                    lastNDays,
                    dayOffset,
                    sparkline: true
                });

                // Process data
                const kpiMap = {};
                res.forEach(item => {
                    kpiMap[item.key] = item;
                });

                const revenueData = kpiMap.revenue?.sparkline || [];
                const spendData = kpiMap.spend?.sparkline || [];

                // Extract labels (dates) and values
                const labels = revenueData.map(p => {
                    const d = new Date(p.date);
                    return timeframe === 'today' || timeframe === 'yesterday'
                        ? d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                        : d.toLocaleDateString([], { month: 'short', day: 'numeric' });
                });

                const revValues = revenueData.map(p => p.value);
                const spendValues = spendData.map(p => p.value);

                setChartData({
                    labels,
                    revValues,
                    spendValues
                });

            } catch (err) {
                console.error("Failed to fetch Money Pulse data:", err);
            } finally {
                setLoading(false);
            }
        };

        loadData();
    }, [workspaceId, timeframe]);

    // Render Chart
    useEffect(() => {
        if (!canvasRef.current || !chartData) return;

        if (chartRef.current) chartRef.current.destroy();

        const ctx = canvasRef.current.getContext('2d');

        // Gradients for Line Chart
        const revGradient = ctx.createLinearGradient(0, 0, 0, 300);
        revGradient.addColorStop(0, 'rgba(6, 182, 212, 0.4)'); // Cyan
        revGradient.addColorStop(1, 'rgba(6, 182, 212, 0)');

        const spendGradient = ctx.createLinearGradient(0, 0, 0, 300);
        spendGradient.addColorStop(0, 'rgba(244, 63, 94, 0.2)'); // Rose
        spendGradient.addColorStop(1, 'rgba(244, 63, 94, 0)');

        const commonOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(255, 255, 255, 0.9)',
                    titleColor: '#1e293b',
                    bodyColor: '#1e293b',
                    borderColor: '#e2e8f0',
                    borderWidth: 1,
                    padding: 10,
                    displayColors: true,
                    usePointStyle: true,
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { color: '#94a3b8', font: { size: 10 } }
                },
                y: {
                    display: false, // Minimal look
                    grid: { display: false }
                }
            },
            interaction: {
                mode: 'index',
                intersect: false,
            }
        };

        if (viewMode === 'overview') {
            // Line Chart
            chartRef.current = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: chartData.labels,
                    datasets: [{
                        label: 'Revenue',
                        data: chartData.revValues,
                        borderColor: '#06b6d4', // Cyan 500
                        backgroundColor: revGradient,
                        borderWidth: 3,
                        tension: 0.5,
                        fill: true,
                        pointRadius: 0,
                        pointHoverRadius: 6
                    }, {
                        label: 'Spend',
                        data: chartData.spendValues,
                        borderColor: '#f43f5e', // Rose 500
                        backgroundColor: spendGradient,
                        borderWidth: 2,
                        borderDash: [5, 5],
                        tension: 0.4,
                        fill: true,
                        pointRadius: 0
                    }]
                },
                options: commonOptions
            });
        } else {
            // Bar Chart (Breakdown)
            chartRef.current = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: chartData.labels,
                    datasets: [{
                        label: 'Revenue',
                        data: chartData.revValues,
                        backgroundColor: '#06b6d4', // Cyan 500
                        borderRadius: 4,
                        barPercentage: 0.6,
                        categoryPercentage: 0.8
                    }, {
                        label: 'Spend',
                        data: chartData.spendValues,
                        backgroundColor: '#f43f5e', // Rose 500
                        borderRadius: 4,
                        barPercentage: 0.6,
                        categoryPercentage: 0.8
                    }]
                },
                options: {
                    ...commonOptions,
                    scales: {
                        ...commonOptions.scales,
                        x: {
                            ...commonOptions.scales.x,
                            grid: { display: false }
                        },
                        y: {
                            display: false,
                            grid: { display: false } // Keep clean look
                        }
                    }
                }
            });
        }

        return () => {
            if (chartRef.current) chartRef.current.destroy();
        };
    }, [chartData, viewMode]);

    return (
        <div className="lg:col-span-2 glass-panel rounded-[32px] p-6 md:p-8 relative overflow-hidden">
            <div className="flex flex-col md:flex-row md:items-center justify-between mb-6 gap-4">
                <div>
                    <h3 className="text-lg font-medium text-slate-800 tracking-tight">Money Pulse</h3>
                    <p className="text-xs text-slate-500">Real-time revenue & spend velocity</p>
                </div>
                {/* Toggle Pill */}
                <div className="flex bg-slate-100/50 p-1 rounded-full border border-white/60 backdrop-blur-sm">
                    <button
                        onClick={() => setViewMode('overview')}
                        className={`px-4 py-1.5 rounded-full text-xs font-medium transition-all ${viewMode === 'overview' ? 'bg-white shadow-sm text-slate-800' : 'text-slate-500 hover:text-slate-700'}`}
                    >
                        Overview
                    </button>
                    <button
                        onClick={() => setViewMode('breakdown')}
                        className={`px-4 py-1.5 rounded-full text-xs font-medium transition-all ${viewMode === 'breakdown' ? 'bg-white shadow-sm text-slate-800' : 'text-slate-500 hover:text-slate-700'}`}
                    >
                        Breakdown
                    </button>
                </div>
            </div>

            <div className="relative w-full h-[280px]">
                {loading && (
                    <div className="absolute inset-0 flex items-center justify-center bg-white/50 z-20 backdrop-blur-sm">
                        <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin"></div>
                    </div>
                )}

                <canvas ref={canvasRef}></canvas>
            </div>
        </div>
    );
}
