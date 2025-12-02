'use client';

/**
 * KpiCard Component
 *
 * WHAT: Displays a single KPI metric with trend indicator, sparkline, and source icon
 * WHY: Give merchants quick insight into key metrics with visual data source clarity
 */

import { TrendingUp, TrendingDown, ShoppingBag } from "lucide-react";
import { useEffect, useRef } from "react";
import Chart from "chart.js/auto";

/**
 * Platform icon components - inline SVGs for crisp rendering
 */

const MetaIcon = ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
        <path d="M12.001 2C6.477 2 2 6.477 2 12.001c0 5.013 3.693 9.153 8.505 9.876v-6.988H7.848v-2.888h2.657V9.845c0-2.622 1.564-4.07 3.956-4.07 1.146 0 2.345.204 2.345.204v2.576h-1.322c-1.302 0-1.708.808-1.708 1.636v1.963h2.9l-.464 2.888h-2.436v6.988c4.812-.723 8.505-4.863 8.505-9.876C22 6.477 17.523 2 12.001 2z"/>
    </svg>
);

const GoogleIcon = ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
        <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
        <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
        <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
        <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
    </svg>
);

const TikTokIcon = ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
        <path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-5.2 1.74 2.89 2.89 0 0 1 2.31-4.64 2.93 2.93 0 0 1 .88.13V9.4a6.84 6.84 0 0 0-1-.05A6.33 6.33 0 0 0 5 20.1a6.34 6.34 0 0 0 10.86-4.43v-7a8.16 8.16 0 0 0 4.77 1.52v-3.4a4.85 4.85 0 0 1-1-.1z"/>
    </svg>
);

/**
 * Platform icon mapping
 */
const PLATFORM_ICONS = {
    meta: { icon: MetaIcon, color: 'text-[#1877F2]' },
    google: { icon: GoogleIcon, color: '' },
    tiktok: { icon: TikTokIcon, color: 'text-black' },
};

/**
 * Source badge component showing platform icon(s)
 */
function SourceBadge({ source, platforms = [] }) {
    if (!source) return null;

    if (source === 'shopify') {
        return (
            <div className="group/source relative">
                <div className="flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-emerald-50">
                    <ShoppingBag className="w-3.5 h-3.5 text-emerald-600" />
                </div>
                <div className="absolute left-0 top-full mt-1 px-2 py-1 bg-slate-800 text-white text-[10px] rounded whitespace-nowrap opacity-0 invisible group-hover/source:opacity-100 group-hover/source:visible transition-all z-10">
                    From Shopify orders
                </div>
            </div>
        );
    }

    if (source === 'platform') {
        // Filter to only show connected platforms
        const connectedIcons = platforms
            .filter(p => PLATFORM_ICONS[p])
            .map(p => ({ name: p, ...PLATFORM_ICONS[p] }));

        // If no platforms connected, show nothing
        if (connectedIcons.length === 0) return null;

        const platformNames = platforms.map(p =>
            p === 'meta' ? 'Meta' : p === 'google' ? 'Google' : p === 'tiktok' ? 'TikTok' : p
        ).join(' + ');

        return (
            <div className="group/source relative">
                <div className="flex items-center gap-0.5 px-1.5 py-0.5 rounded-md bg-slate-100">
                    {connectedIcons.map(({ name, icon: Icon, color }) => (
                        <Icon key={name} className={`w-3.5 h-3.5 ${color}`} />
                    ))}
                </div>
                <div className="absolute left-0 top-full mt-1 px-2 py-1 bg-slate-800 text-white text-[10px] rounded whitespace-nowrap opacity-0 invisible group-hover/source:opacity-100 group-hover/source:visible transition-all z-10">
                    From {platformNames}
                </div>
            </div>
        );
    }

    if (source === 'computed') {
        return (
            <div className="group/source relative">
                <div className="flex items-center gap-0.5 px-1.5 py-0.5 rounded-md bg-purple-50">
                    <span className="text-[10px] font-medium text-purple-600">calc</span>
                </div>
                <div className="absolute left-0 top-full mt-1 px-2 py-1 bg-slate-800 text-white text-[10px] rounded whitespace-nowrap opacity-0 invisible group-hover/source:opacity-100 group-hover/source:visible transition-all z-10">
                    Calculated from revenue ÷ spend
                </div>
            </div>
        );
    }

    return null;
}

export default function KpiCard({ title, value, change, trend, color = "cyan", sparklineData, source, platforms = [] }) {
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
          <SourceBadge source={source} platforms={platforms} />
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
