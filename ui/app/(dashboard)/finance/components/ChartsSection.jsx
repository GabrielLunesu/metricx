"use client";
import { useEffect, useRef } from "react";
import { Chart, registerables } from "chart.js";
import SpendCompositionCard from "./SpendCompositionCard";

Chart.register(...registerables);

export default function ChartsSection({
  composition,
  timeseries,
  totalRevenue,
  totalSpend,
  excludedRows = new Set(),
  rows = [],
  onRowToggle,
  mode = "both", // "both" | "revenueOnly" | "compositionOnly"
  selectedMonth,
}) {
  const revenueChartRef = useRef(null);
  const revenueChartInstance = useRef(null);

  useEffect(() => {
    // Revenue Chart
    if (revenueChartRef.current && timeseries && timeseries.length > 0) {
      const ctx = revenueChartRef.current.getContext('2d');

      if (revenueChartInstance.current) {
        revenueChartInstance.current.destroy();
      }

      // Process timeseries data for revenue chart
      const labels = timeseries.map(d => {
        const date = new Date(d.date);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      });
      const revenueData = timeseries.map(d => d.revenue || 0);

      revenueChartInstance.current = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [{
            label: 'Revenue',
            data: revenueData,
            backgroundColor: 'rgba(6, 182, 212, 0.7)',
            borderColor: 'rgba(6, 182, 212, 1)',
            borderWidth: 1,
            borderRadius: 8,
            hoverBackgroundColor: 'rgba(6, 182, 212, 0.9)'
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: {
            mode: 'index',
            intersect: false
          },
          plugins: {
            legend: {
              display: false
            },
            tooltip: {
              backgroundColor: 'rgba(255, 255, 255, 0.95)',
              titleColor: '#0B0B0B',
              bodyColor: '#0B0B0B',
              borderColor: 'rgba(6, 182, 212, 0.2)',
              borderWidth: 1,
              padding: 12,
              displayColors: false,
              callbacks: {
                label: function (context) {
                  return 'Revenue: $' + context.parsed.y.toLocaleString(undefined, { maximumFractionDigits: 0 });
                }
              }
            }
          },
          scales: {
            x: {
              grid: {
                display: false
              },
              ticks: {
                font: { size: 11 },
                color: '#6B7280'
              }
            },
            y: {
              beginAtZero: true,
              grid: {
                color: 'rgba(0, 0, 0, 0.05)',
                drawBorder: false
              },
              ticks: {
                font: { size: 11 },
                color: '#6B7280',
                callback: function (value) {
                  return '$' + (value / 1000).toFixed(0) + 'K';
                }
              }
            }
          }
        }
      });
    }

    return () => {
      if (revenueChartInstance.current) {
        revenueChartInstance.current.destroy();
      }
    };
  }, [timeseries]);

  const revenueCard = timeseries && timeseries.length > 0 && (
    <div className="glass-card rounded-xl p-5 border border-slate-200 bg-white relative overflow-hidden">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
          Revenue Over Time
        </h3>
        <span className="text-[10px] text-emerald-600 font-medium">
          Revenue:&nbsp;$
          {(timeseries.reduce((sum, d) => sum + (d.revenue || 0), 0) / 1000).toFixed(0)}K
        </span>
      </div>
      <div className="h-48 w-full">
        <canvas ref={revenueChartRef}></canvas>
      </div>
    </div>
  );

  const compositionCard = (
    <SpendCompositionCard
      composition={composition}
      rows={rows}
      excludedRows={excludedRows}
      totalRevenue={totalRevenue}
      totalSpend={totalSpend}
      selectedMonth={selectedMonth}
    />
  );

  if (mode === "revenueOnly") {
    return revenueCard || null;
  }

  if (mode === "compositionOnly") {
    return compositionCard || null;
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
      {revenueCard}
      {compositionCard}
    </div>
  );
}
