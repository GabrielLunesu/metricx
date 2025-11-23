"use client";
import PlatformBadge from "../../../../components/campaigns/PlatformBadge";
import TrendSparkline from "../../../../components/campaigns/TrendSparkline";
import StatusPill from "../../../../components/StatusPill"; // Global StatusPill
import { Facebook, Search, Instagram, Youtube } from "lucide-react";

function CellValue({ v }) {
  return <div className="text-right tabular-nums">{v || '—'}</div>;
}

// WHAT: Displays a single row in the Campaigns or Ad Sets table.
// WHY: Presentational component, receives pre-formatted data from adapter.
// REFERENCES:
// - ui/app/(dashboard)/campaigns/page.jsx (parent)
// - ui/app/(dashboard)/campaigns/[id]/page.jsx (parent)
// - ui/lib/campaignsAdapter.js (data source)
function CampaignIcon({ platform }) {
  const normalized =
    platform?.toLowerCase().replace(/\s+ads?$/i, "").trim() || "";

  if (normalized === "meta" || normalized === "facebook") {
    return (
      <div className="bg-blue-50 p-2 rounded-lg">
        <Facebook className="w-4 h-4 text-blue-600" />
      </div>
    );
  }

  if (normalized === "instagram") {
    return (
      <div className="bg-purple-50 p-2 rounded-lg">
        <Instagram className="w-4 h-4 text-purple-600" />
      </div>
    );
  }

  if (normalized === "google") {
    return (
      <div className="bg-white border border-slate-100 p-2 rounded-lg shadow-sm">
        <Search className="w-4 h-4 text-blue-500" />
      </div>
    );
  }

  if (normalized === "youtube") {
    return (
      <div className="bg-slate-50 border border-slate-200 p-2 rounded-lg">
        <Youtube className="w-4 h-4 text-red-500" />
      </div>
    );
  }

  return (
    <div className="bg-slate-50 p-2 rounded-lg">
      <span className="w-4 h-4 text-xs font-semibold text-slate-500 flex items-center justify-center">
        {platform?.[0]?.toUpperCase() || "?"}
      </span>
    </div>
  );
}

export default function CampaignRow({ row, selected, onRowClick, onSelectToggle }) {
  return (
    <div
      className={`grid grid-cols-[40px_minmax(0,3fr)_minmax(0,1.2fr)_minmax(0,1.4fr)_minmax(0,1.4fr)_minmax(0,0.9fr)_minmax(0,1fr)] gap-4 items-center px-6 md:px-8 py-4 cursor-pointer transition-all ${
        selected ? "bg-cyan-50/40 border-l-2 border-l-cyan-400" : "hover:bg-slate-50/80"
      }`}
      onClick={onRowClick}
    >
      {/* Checkbox */}
      <div
        className="flex items-center"
        onClick={(e) => {
          e.stopPropagation();
          onSelectToggle?.();
        }}
      >
        <input
          type="checkbox"
          className="custom-checkbox cursor-pointer"
          checked={!!selected}
          onChange={() => {}}
          aria-label="Select campaign"
        />
      </div>

      {/* Campaign name + icon */}
      <div className="flex items-center gap-3">
        <CampaignIcon platform={row.platform} />
        <div>
          <p className="text-sm font-semibold text-slate-900">{row.name}</p>
          <p className="text-[11px] text-slate-400 mt-0.5">
            {row.display?.subtitle || "—"}
          </p>
        </div>
      </div>

      {/* Platform */}
      <div>
        <PlatformBadge platform={row.platform} />
      </div>

      {/* Spend */}
      <div className="text-right">
        <CellValue v={row.display?.spend} />
      </div>

      {/* Revenue */}
      <div className="text-right">
        <CellValue v={row.display?.revenue} />
      </div>

      {/* ROAS */}
      <div className="text-right">
        <CellValue v={row.display?.roas} />
      </div>

      {/* Trend */}
      <div className="flex items-center justify-end">
        <TrendSparkline data={row.trend?.map((p) => p.value) || []} />
      </div>
    </div>
  );
}
