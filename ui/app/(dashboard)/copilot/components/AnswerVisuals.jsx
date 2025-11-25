"use client";

import { useEffect, useRef } from "react";
import { Chart, registerables } from "chart.js";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/cn";

Chart.register(...registerables);

const currencyMetrics = new Set(["spend", "revenue", "cpa", "cpc", "cpm", "cpl", "cpi", "cpp", "aov"]);
const percentMetrics = new Set(["ctr", "cvr"]);
const ratioMetrics = new Set(["roas", "poas", "arpv"]);

const formatNumber = (value) => new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(value ?? 0);

function formatValue(value, format) {
  if (value === null || value === undefined) return "—";
  // If value is a string (like labels/names), return as-is
  if (typeof value === "string") return value;
  const metric = (format || "").toLowerCase();
  if (currencyMetrics.has(metric)) return `$${formatNumber(value)}`;
  if (percentMetrics.has(metric)) return `${(value * 100).toFixed(1)}%`;
  if (ratioMetrics.has(metric)) return `${value.toFixed(2)}×`;
  if (metric === "mixed") return formatNumber(value);
  return formatNumber(value);
}

function DeltaBadge({ delta, formattedDelta }) {
  if (delta === null || delta === undefined) return null;
  const positive = delta >= 0;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold",
        positive ? "bg-emerald-50 text-emerald-700" : "bg-rose-50 text-rose-700"
      )}
    >
      {positive ? <ArrowUpRight className="w-2.5 h-2.5" /> : <ArrowDownRight className="w-2.5 h-2.5" />}
      {formattedDelta || `${(delta * 100).toFixed(1)}%`}
    </span>
  );
}

// Mini Sparkline (v2.1 - Muted color palette)
// WHAT: Small inline chart for metric cards
// WHY: Subtle blue color for Apple-like aesthetic
function MiniSparkline({ data, metric }) {
  const canvasRef = useRef(null);
  const chartInstance = useRef(null);

  useEffect(() => {
    if (!canvasRef.current || !data || data.length === 0) return;

    const ctx = canvasRef.current.getContext("2d");

    if (chartInstance.current) {
      chartInstance.current.destroy();
    }

    const chartData = data.map((d) => ({ x: d.x || d.date, y: d.y ?? d.value }));

    chartInstance.current = new Chart(ctx, {
      type: "line",
      data: {
        labels: chartData.map((d) => d.x),
        datasets: [
          {
            data: chartData.map((d) => d.y),
            // Muted blue color palette (Apple-like)
            borderColor: "#3b82f6",
            backgroundColor: "rgba(59, 130, 246, 0.08)",
            borderWidth: 1.5,
            tension: 0.4,
            fill: true,
            pointRadius: 0,
            pointHoverRadius: 0,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { enabled: false } },
        scales: {
          x: { display: false },
          y: { display: false },
        },
      },
    });

    return () => {
      if (chartInstance.current) {
        chartInstance.current.destroy();
      }
    };
  }, [data, metric]);

  if (!data || data.length === 0) return <div className="text-[10px] text-slate-400">No data</div>;

  return <canvas ref={canvasRef} className="w-full h-12" />;
}

// Summary Card (v2.1 - Apple-inspired subtle glass design)
// WHAT: Metric summary card with sparkline and delta badge
// WHY: Clean, minimal aesthetic with subtle borders and hover states
function SummaryCard({ card }) {
  return (
    <Card className="bg-white/90 backdrop-blur-sm border border-slate-200/50 rounded-xl hover:bg-slate-50/80 transition-colors duration-200">
      <CardHeader className="pb-2 space-y-0">
        <div className="flex items-center justify-between">
          <CardTitle className="text-[11px] font-medium text-slate-500 uppercase tracking-wide">{card.title}</CardTitle>
          <DeltaBadge delta={card.delta} formattedDelta={card.formatted_delta} />
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="text-3xl font-semibold text-slate-900 tracking-tight">
          {card.formatted_value || formatValue(card.value, card.metric)}
        </div>
        <div className="text-[10px] text-slate-500">{card.timeframe || "Selected period"}</div>
        <div className="h-12 w-full">
          <MiniSparkline data={card.sparkline} metric={card.metric} />
        </div>
        {card.top_contributor && (
          <div className="text-[10px] text-slate-500 pt-1 border-t border-slate-100">
            Top: <span className="font-medium text-slate-700">{card.top_contributor}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ChartCard({ spec }) {
  const canvasRef = useRef(null);
  const chartInstance = useRef(null);

  // Debug: Log chart spec to see series data
  useEffect(() => {
    console.log('[ChartCard] Rendering spec:', {
      title: spec?.title,
      type: spec?.type,
      seriesCount: spec?.series?.length,
      series: spec?.series?.map(s => ({ name: s.name, dataKey: s.dataKey, dataLength: s.data?.length }))
    });
  }, [spec]);

  useEffect(() => {
    if (!canvasRef.current || !spec) return;

    const ctx = canvasRef.current.getContext("2d");

    if (chartInstance.current) {
      chartInstance.current.destroy();
    }

    // Build data structure for Chart.js
    const buildChartData = () => {
      if (!spec.series || spec.series.length === 0) return { labels: [], datasets: [] };

      const isMultiSeries = spec.series.length > 1;
      const chartType = spec.type === "bar" || spec.type === "grouped_bar" ? "bar" : "line";

      if (isMultiSeries) {
        // For multi-series (e.g., current vs previous), we need to:
        // 1. Collect all unique x-values (dates) across all series
        // 2. Create a dataset for each series with values aligned to the labels

        const allXValues = new Set();
        spec.series.forEach((s) => {
          (s.data || []).forEach((d) => {
            const xVal = d.x ?? d.date ?? d[spec.xKey || "x"];
            if (xVal) allXValues.add(String(xVal));
          });
        });

        const labels = Array.from(allXValues).sort();

        // Color scheme: muted palette (Apple-like)
        // Primary blue for current, slate for previous
        const colors = ["#3b82f6", "#94a3b8", "#64748b", "#cbd5e1"];

        const datasets = spec.series.map((s, idx) => {
          // Create a map of x-value to y-value for this series
          const dataMap = {};
          (s.data || []).forEach((d) => {
            const xVal = String(d.x ?? d.date ?? d[spec.xKey || "x"]);
            const yVal = d.y ?? d.value ?? d[spec.yKey || "y"];
            dataMap[xVal] = yVal;
          });

          // Align data to labels (fill missing values with null)
          const alignedData = labels.map(label => dataMap[label] ?? null);

          return {
            label: s.name || s.dataKey,
            data: alignedData,
            borderColor: s.color || colors[idx % colors.length],
            backgroundColor: chartType === "bar"
              ? (s.color || colors[idx % colors.length])
              : "transparent",
            borderWidth: 2,
            tension: 0.4,
            fill: false,
            pointRadius: 0,
            pointHoverRadius: 4,
            pointBackgroundColor: s.color || colors[idx % colors.length],
          };
        });

        return { labels, datasets };
      }

      // Single series (muted blue palette)
      const sData = spec.series[0].data || [];
      const labels = sData.map((d) => d.x ?? d.date ?? d[spec.xKey || "x"]);
      const datasets = [
        {
          label: spec.series[0].name || spec.title,
          data: sData.map((d) => d.y ?? d.value ?? d[spec.yKey || "y"]),
          // Muted blue (Apple-like)
          borderColor: spec.series[0].color || "#3b82f6",
          backgroundColor: chartType === "bar" ? "#3b82f6" : "rgba(59, 130, 246, 0.08)",
          borderWidth: 2,
          tension: 0.4,
          fill: chartType !== "bar",
          pointRadius: 0,
          pointHoverRadius: 4,
        },
      ];

      return { labels, datasets };
    };

    const { labels, datasets } = buildChartData();
    const chartType = spec.type === "bar" || spec.type === "grouped_bar" ? "bar" : "line";

    chartInstance.current = new Chart(ctx, {
      type: chartType,
      data: { labels, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false,
        },
        plugins: {
          legend: {
            display: datasets.length > 1,
            position: "bottom",
            labels: {
              usePointStyle: true,
              padding: 12,
              font: { size: 11, weight: "500" },
              color: "#475569",
            },
          },
          tooltip: {
            backgroundColor: "rgba(255, 255, 255, 0.97)",
            titleColor: "#0f172a",
            bodyColor: "#475569",
            borderColor: "rgba(203, 213, 225, 0.5)",
            borderWidth: 1,
            padding: 10,
            displayColors: true,
            callbacks: {
              label: function (context) {
                const label = context.dataset.label || '';
                const value = formatValue(context.parsed.y, spec.valueFormat || "mixed");
                return `${label}: ${value}`;
              },
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { color: "#94a3b8", font: { size: 10 } },
          },
          y: {
            grid: { color: "rgba(203, 213, 225, 0.3)", drawBorder: false },
            ticks: {
              color: "#94a3b8",
              font: { size: 10 },
              callback: function (value) {
                return formatValue(value, spec.valueFormat || "mixed");
              },
            },
          },
        },
      },
    });

    return () => {
      if (chartInstance.current) {
        chartInstance.current.destroy();
      }
    };
  }, [spec]);

  // Chart Card (v2.1 - Apple-inspired subtle glass design)
  return (
    <Card className="bg-white/90 backdrop-blur-sm border border-slate-200/50 rounded-xl hover:bg-slate-50/80 transition-colors duration-200">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-semibold text-slate-800">{spec.title}</CardTitle>
        {spec.description && <div className="text-[10px] text-slate-500 mt-1">{spec.description}</div>}
      </CardHeader>
      <CardContent>
        <div className="w-full" style={{ height: '192px' }}>
          <canvas ref={canvasRef} />
        </div>
      </CardContent>
    </Card>
  );
}

// Table Card (v2.1 - Apple-inspired subtle glass design)
// WHAT: Data table with clean borders and hover states
// WHY: Minimal aesthetic matching the overall design system
function TableCard({ table }) {
  return (
    <Card className="bg-white/90 backdrop-blur-sm border border-slate-200/50 rounded-xl hover:bg-slate-50/80 transition-colors duration-200">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-semibold text-slate-800">{table.title}</CardTitle>
      </CardHeader>
      <CardContent className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200/60">
              {table.columns?.map((col) => (
                <th key={col.key} className="text-left text-[10px] font-semibold text-slate-600 uppercase tracking-wide py-2 pr-4">
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {table.rows?.map((row, idx) => (
              <tr key={idx} className="border-t border-slate-100/60 hover:bg-slate-50/60 transition-colors duration-150">
                {table.columns?.map((col) => (
                  <td key={col.key} className="py-2 pr-4 text-slate-700">
                    {formatValue(row[col.key], col.format)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}

export default function AnswerVisuals({ visuals }) {
  if (!visuals) return null;
  const { cards = [], viz_specs = [], tables = [] } = visuals;
  const hasContent = cards.length || viz_specs.length || tables.length;
  if (!hasContent) return null;

  // Smart layout: single card + single chart = side-by-side
  const singleCard = cards.length === 1;
  const singleChart = viz_specs.length === 1;
  const showCombined = singleCard && singleChart && tables.length === 0;

  return (
    <div className="mt-6 space-y-4">
      {showCombined ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-1">
            <SummaryCard card={cards[0]} />
          </div>
          <div className="lg:col-span-2">
            <ChartCard spec={viz_specs[0]} />
          </div>
        </div>
      ) : (
        <>
          {cards.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {cards.map((card) => (
                <SummaryCard key={card.id} card={card} />
              ))}
            </div>
          )}
          {viz_specs.length > 0 && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {viz_specs.map((spec) => (
                <ChartCard key={spec.id} spec={spec} />
              ))}
            </div>
          )}
        </>
      )}
      {tables.length > 0 && (
        <div className="space-y-4">
          {tables.map((table) => (
            <TableCard key={table.id} table={table} />
          ))}
        </div>
      )}
    </div>
  );
}
