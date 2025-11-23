'use client';

import { TrendingUp, TrendingDown } from "lucide-react";
import { useEffect, useRef } from "react";
import Chart from "chart.js/auto";

export default function KpiCard({ title, value, change, trend, color = "cyan", sparklineData }) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);

  const colorMap = {
    cyan: { bg: "bg-cyan-400", shadow: "shadow-[0_0_8px_rgba(34,211,238,0.6)]", hex: "#22d3ee" },
    purple: { bg: "bg-purple-400", shadow: "shadow-[0_0_8px_rgba(192,132,252,0.6)]", hex: "#c084fc" },
    blue: { bg: "bg-blue-400", shadow: "shadow-[0_0_8px_rgba(96,165,250,0.6)]", hex: "#60a5fa" },
    orange: { bg: "bg-orange-400", shadow: "shadow-[0_0_8px_rgba(251,146,60,0.6)]", hex: "#fb923c" },
    emerald: { bg: "bg-emerald-400", shadow: "shadow-[0_0_8px_rgba(52,211,153,0.6)]", hex: "#34d399" },
  };

  const theme = colorMap[color] || colorMap.cyan;

  useEffect(() => {
    if (sparklineData && canvasRef.current) {
      if (chartRef.current) chartRef.current.destroy();

      const ctx = canvasRef.current.getContext('2d');
      const gradient = ctx.createLinearGradient(0, 0, 0, 30);
      gradient.addColorStop(0, theme.hex);
      gradient.addColorStop(1, 'rgba(255,255,255,0)');

      chartRef.current = new Chart(ctx, {
        type: 'line',
        data: {
          labels: sparklineData.map((_, i) => i),
          datasets: [{
            data: sparklineData,
            borderColor: theme.hex,
            backgroundColor: gradient,
            borderWidth: 2,
            tension: 0.4,
            fill: true,
            pointRadius: 0,
            pointHoverRadius: 0
          }]
        },
        options: {
          responsive: false,
          maintainAspectRatio: false,
          plugins: { legend: { display: false }, tooltip: { enabled: false } },
          scales: { x: { display: false }, y: { display: false } },
          animation: { duration: 0 } // Disable animation for performance
        }
      });
    }
    return () => {
      if (chartRef.current) chartRef.current.destroy();
    };
  }, [sparklineData, theme.hex]);

  return (
    <div className="glass-panel rounded-[22px] p-5 glass-card-hover transition-all duration-500 group snap-center min-w-[280px]">
      <div className="flex justify-between items-start mb-2">
        <div className="flex items-center gap-2">
          <div className={`w-1.5 h-1.5 rounded-full ${theme.bg} ${theme.shadow}`}></div>
          <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">{title}</span>
        </div>
        {change && (
          <div className={`flex items-center px-1.5 py-0.5 rounded-md border ${trend === 'up' ? 'text-emerald-500 bg-emerald-50/50 border-emerald-100' : 'text-rose-500 bg-rose-50/50 border-rose-100'}`}>
            {trend === 'up' ? <TrendingUp className="w-3 h-3 mr-1" /> : <TrendingDown className="w-3 h-3 mr-1" />}
            <span className="text-[10px] font-semibold">{change}</span>
          </div>
        )}
      </div>
      <div className="flex items-end justify-between">
        <h2 className="text-2xl font-semibold text-slate-800 tracking-tight">{value}</h2>
        {sparklineData && (
          <canvas ref={canvasRef} width="80" height="30" className="opacity-80 group-hover:opacity-100 transition-opacity"></canvas>
        )}
      </div>
    </div>
  );
}
