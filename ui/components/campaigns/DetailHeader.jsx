import Link from "next/link";
import StatusPill from "../StatusPill";
import PlatformBadge from "./PlatformBadge";

export default function DetailHeader({
  name,
  platform,
  status,
  timeframe = "Last 7 days",
  subtitle,
  loading,
}) {
  return (
    <header className="mb-6">
      <div className="text-[11px] text-slate-400 mb-2">
        <Link href="/campaigns" className="hover:underline">
          Campaigns
        </Link>
        <span className="mx-1">›</span>
        <span className="text-slate-300">{name}</span>
      </div>
      <div className="flex items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-2xl font-semibold tracking-tight text-slate-900">
              {name}
            </h2>
            {loading && (
              <span className="text-[11px] text-cyan-500">Loading…</span>
            )}
          </div>
          <div className="flex items-center gap-3 mt-2 text-xs">
            <PlatformBadge platform={platform} />
            <StatusPill status={status} />
            <span className="text-slate-400">•</span>
            <span className="text-slate-500">{timeframe}</span>
          </div>
          <div className="text-[11px] text-slate-400 mt-2">
            {subtitle || "Last updated —"}
          </div>
        </div>
      </div>
    </header>
  );
}
