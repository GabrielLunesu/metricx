import Card from "../Card";
import EntityRow from "./EntityRow";

export default function EntityTable({
  title,
  rows = [],
  loading = false,
  error = null,
  onRowClick,
}) {
  return (
    <Card className="rounded-[24px] border border-slate-200 bg-white shadow-lg shadow-slate-200/50 overflow-hidden">
      {/* Header with title and loading indicator */}
      <div className="px-6 py-4 flex items-center justify-between border-b border-slate-100 bg-slate-50/70">
        <span className="text-sm font-semibold text-slate-800 tracking-wide">
          {title}
        </span>
        {loading ? (
          <span className="text-xs text-cyan-600 font-medium animate-pulse flex items-center gap-2">
            <span className="inline-block w-1.5 h-1.5 bg-cyan-500 rounded-full animate-ping" />
            Loading…
          </span>
        ) : null}
      </div>

      {/* Column Headers */}
      <div className="px-6 py-3 border-b border-slate-100 bg-slate-50/80 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
        <div className="grid grid-cols-[minmax(0,3fr)_minmax(0,1.2fr)_minmax(0,1.2fr)_minmax(0,1.1fr)_minmax(0,1.3fr)_minmax(0,1.1fr)_minmax(0,1.1fr)_minmax(0,1.2fr)_minmax(0,1.2fr)_minmax(0,1.1fr)] gap-4 items-center">
          <div>Name</div>
          <div className="text-right">Revenue</div>
          <div className="text-right">Spend</div>
          <div className="text-right">ROAS</div>
          <div className="text-right">Conversions</div>
          <div className="text-right">CPC</div>
          <div className="text-right">CTR</div>
          <div className="text-right">Status</div>
          <div className="text-right">Trend</div>
          <div className="text-right">Action</div>
        </div>
      </div>

      {/* Table Body */}
      <div className="relative">
        {loading && (
          <div className="p-12 text-center">
            <div className="inline-flex flex-col items-center gap-4">
              <div className="w-8 h-8 border-2 border-slate-200 border-t-cyan-500 rounded-full animate-spin" />
              <span className="text-sm text-slate-600 font-medium">
                Loading {title.toLowerCase()}...
              </span>
            </div>
          </div>
        )}
        {error && (
          <div className="p-12 text-center">
            <div className="inline-flex flex-col items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-red-50 border border-red-200 flex items-center justify-center">
                <span className="text-red-500 text-xl">!</span>
              </div>
              <span className="text-sm text-red-600 font-medium">
                Failed to load {title.toLowerCase()}. Please try again.
              </span>
            </div>
          </div>
        )}
        {!loading && !error && rows.length === 0 && (
          <div className="p-12 text-center">
            <div className="inline-flex flex-col items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-slate-50 border border-slate-200 flex items-center justify-center">
                <span className="text-slate-400 text-xl">∅</span>
              </div>
              <span className="text-sm text-slate-500 font-medium">
                No {title.toLowerCase()} found.
              </span>
            </div>
          </div>
        )}
        {!loading &&
          !error &&
          rows.map((r) => (
            <EntityRow key={r.id} row={r} onClick={onRowClick} />
          ))}
      </div>
    </Card>
  );
}
