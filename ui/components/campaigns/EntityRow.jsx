import TrendSparkline from "./TrendSparkline";
import StatusPill from "../StatusPill";

export default function EntityRow({ row, onClick }) {
  const display = row.display || {};
  const hasChildren = row.level !== "ad"; // Ads are leaf nodes

  return (
    <div className="px-6 py-3 text-sm hover:bg-slate-50/80 transition-all">
      <div className="grid grid-cols-[minmax(0,3fr)_minmax(0,1.2fr)_minmax(0,1.2fr)_minmax(0,1.1fr)_minmax(0,1.3fr)_minmax(0,1.1fr)_minmax(0,1.1fr)_minmax(0,1.2fr)_minmax(0,1.2fr)_minmax(0,1.1fr)] gap-4 items-center">
        <div>
          <div className="text-sm font-semibold text-slate-900">
            {row.name}
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">
            {display.subtitle}
          </div>
        </div>
        <Cell value={display.revenue} align="right" />
        <Cell value={display.spend} align="right" />
        <Cell value={display.roas} align="right" />
        <Cell value={display.conversions} align="right" />
        <Cell value={display.cpc} align="right" />
        <Cell value={display.ctr} align="right" />
        <div className="text-right">
          <StatusPill status={row.status} />
        </div>
        <div className="text-right">
          <TrendSparkline
            data={row.trend?.map((point) => point.value ?? 0) || []}
          />
        </div>
        <div className="text-right">
          {hasChildren && onClick ? (
            <button
              onClick={() => onClick(row.id)}
              className="inline-flex items-center justify-center px-3 py-1.5 rounded-full border border-slate-200 text-[11px] font-medium text-slate-600 bg-white hover:text-slate-800 hover:border-slate-300 transition-colors"
            >
              View
            </button>
          ) : (
            <span className="text-[11px] text-slate-400">—</span>
          )}
        </div>
      </div>
    </div>
  );
}

function Cell({ value, align = "left" }) {
  return (
    <div
      className={`text-${align} tabular-nums text-sm font-medium text-slate-700`}
    >
      {value ?? "—"}
    </div>
  );
}
