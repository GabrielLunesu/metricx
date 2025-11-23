"use client";
import { useEffect, useRef, useState } from "react";
import { Chart, registerables } from "chart.js";
import { fetchWorkspaceKpis } from "@/lib/api";

Chart.register(...registerables);

export default function AnalyticsGraphEngine({
    workspaceId,
    selectedProvider,
    timeFilters,
    campaignId
}) {
    const chartRef = useRef(null);
    const chartInstance = useRef(null);
    const [loading, setLoading] = useState(true);
    const [chartData, setChartData] = useState(null);

    useEffect(() => {
        if (!workspaceId) return;

        let mounted = true;
        setLoading(true);

        // Build params based on timeFilters type
        const params = {
            workspaceId,
            metrics: ['revenue', 'spend', 'roas'],
            provider: selectedProvider === 'all' ? null : selectedProvider,
            sparkline: true,
            campaignId: campaignId || null
        };

        // Add time range params based on filter type
        if (timeFilters.type === 'custom' && timeFilters.customStart && timeFilters.customEnd) {
            // Custom date range - only pass custom dates
            params.customStartDate = timeFilters.customStart;
            params.customEndDate = timeFilters.customEnd;
            params.lastNDays = timeFilters.rangeDays; // for backend compatibility
        } else {
            // Preset range - only pass lastNDays, don't include custom dates at all
            params.lastNDays = timeFilters.rangeDays;
        }

        fetchWorkspaceKpis(params)
            .then((data) => {
                if (!mounted) return;
                // Transform data into a map for easier access
                const dataMap = {};
                data.forEach(item => {
                    if (item.sparkline) {
                        dataMap[item.key] = item.sparkline;
                    }
                });
                setChartData(dataMap);
                setLoading(false);
            })
            .catch((err) => {
                console.error('Failed to fetch chart data:', err);
                if (mounted) setLoading(false);
            });

        return () => { mounted = false; };
    }, [workspaceId, selectedProvider, timeFilters.type, timeFilters.rangeDays, timeFilters.customStart, timeFilters.customEnd, campaignId]);


    // Cleanup effect - destroy chart when timeFilters change
    useEffect(() => {
        return () => {
            if (chartInstance.current) {
                chartInstance.current.destroy();
                chartInstance.current = null;
            }
        };
    }, [timeFilters.type, timeFilters.rangeDays, timeFilters.customStart, timeFilters.customEnd]);

    useEffect(() => {
        if (!chartRef.current || !chartData || loading) return;

        const ctx = chartRef.current.getContext('2d');

        if (chartInstance.current) {
            chartInstance.current.destroy();
        }

        // Get labels from one of the datasets (assuming all have same dates)
        const firstMetric = Object.values(chartData)[0];
        if (!firstMetric || firstMetric.length === 0) return;

        // Check if this is a single-day view (24 hours)
        const isSingleDay = timeFilters.rangeDays === 1 ||
            (timeFilters.type === 'custom' && timeFilters.customStart === timeFilters.customEnd);

        const labels = firstMetric.map(d => {
            const date = new Date(d.date);
            if (isSingleDay) {
                // Show hours for 24-hour view
                return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
            } else {
                // Show dates for multi-day view
                return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            }
        });

        // Gradients
        const gradientRevenue = ctx.createLinearGradient(0, 0, 0, 400);
        gradientRevenue.addColorStop(0, 'rgba(34, 211, 238, 0.3)'); // Cyan
        gradientRevenue.addColorStop(1, 'rgba(34, 211, 238, 0)');

        const gradientSpend = ctx.createLinearGradient(0, 0, 0, 400);
        gradientSpend.addColorStop(0, 'rgba(15, 23, 42, 0.1)'); // Slate
        gradientSpend.addColorStop(1, 'rgba(15, 23, 42, 0)');

        chartInstance.current = new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: [
                    {
                        label: 'Revenue',
                        data: chartData.revenue?.map(d => d.value) || [],
                        borderColor: '#22d3ee', // Cyan 400
                        backgroundColor: gradientRevenue,
                        borderWidth: 3,
                        tension: 0.4,
                        fill: true,
                        pointBackgroundColor: '#fff',
                        pointBorderColor: '#22d3ee',
                        pointBorderWidth: 2,
                        pointRadius: 4,
                        pointHoverRadius: 6,
                        yAxisID: 'y',
                        order: 1
                    },
                    {
                        label: 'Spend',
                        data: chartData.spend?.map(d => d.value) || [],
                        borderColor: '#1e293b', // Slate 800
                        backgroundColor: gradientSpend,
                        borderWidth: 2,
                        borderDash: [5, 5],
                        tension: 0.4,
                        fill: true,
                        pointRadius: 0,
                        pointHoverRadius: 4,
                        yAxisID: 'y',
                        order: 2
                    },
                    {
                        label: 'ROAS',
                        data: chartData.roas?.map(d => d.value) || [],
                        borderColor: '#a78bfa', // Violet 400
                        borderWidth: 2,
                        tension: 0.4,
                        fill: false,
                        yAxisID: 'y1',
                        pointRadius: 0,
                        pointHoverRadius: 4,
                        order: 0
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(255, 255, 255, 0.9)',
                        titleColor: '#1e293b',
                        bodyColor: '#475569',
                        borderColor: '#e2e8f0',
                        borderWidth: 1,
                        padding: 12,
                        boxPadding: 4,
                        usePointStyle: true,
                        callbacks: {
                            label: function (context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.parsed.y !== null) {
                                    if (label.includes('ROAS')) return label + context.parsed.y.toFixed(2) + 'x';
                                    return label + '$' + context.parsed.y.toLocaleString();
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { color: '#94a3b8', font: { size: 10, family: "'Inter', sans-serif" } }
                    },
                    y: {
                        display: false, // Hide Y axis as per inspo (or keep minimal)
                        grid: { display: false }
                    },
                    y1: {
                        display: false,
                        position: 'right',
                        grid: { display: false }
                    }
                }
            }
        });

        return () => {
            if (chartInstance.current) {
                chartInstance.current.destroy();
            }
        };
    }, [chartData, loading]);

    return (
        <div className="xl:col-span-2 glass-panel rounded-[24px] p-6 flex flex-col relative overflow-hidden h-full">
            {/* Graph Header */}
            <div className="flex flex-wrap justify-between items-center mb-6 gap-4">
                <div className="flex items-center gap-4">
                    <h2 className="text-lg font-semibold text-slate-800">
                        Performance Velocity
                        {(timeFilters.rangeDays === 1 ||
                            (timeFilters.type === 'custom' && timeFilters.customStart === timeFilters.customEnd)) ? (
                            <span className="text-sm font-normal text-slate-500 ml-2">(24 Hours)</span>
                        ) : null}
                    </h2>
                    <div className="flex bg-slate-100/50 p-1 rounded-lg border border-white/50">
                        <button className="px-3 py-1 rounded-md bg-white shadow-sm text-[10px] font-semibold text-slate-800">Overview</button>
                        <button className="px-3 py-1 rounded-md text-[10px] font-medium text-slate-500 hover:text-slate-700">Breakdown</button>
                    </div>
                </div>
                <div className="flex gap-4 items-center">
                    <div className="flex items-center gap-2 text-[10px]">
                        <span className="w-2 h-2 rounded-full bg-cyan-400"></span> Revenue
                        <span className="w-2 h-2 rounded-full bg-slate-800 ml-2"></span> Spend
                        <span className="w-2 h-2 rounded-full bg-violet-400 ml-2"></span> ROAS
                    </div>
                </div>
            </div>

            {/* Canvas Area */}
            <div className="relative w-full flex-1 min-h-[300px]">
                {loading ? (
                    <div className="absolute inset-0 flex items-center justify-center">
                        <div className="w-8 h-8 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin"></div>
                    </div>
                ) : (
                    <canvas ref={chartRef}></canvas>
                )}
            </div>
        </div>
    );
}
