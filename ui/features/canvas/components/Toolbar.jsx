// WHAT: Canvas toolbar — breadcrumbs, search slot, controls
// WHY: Top-level controls and context for the canvas
// REFERENCES: design notes in docs/canvas/01-functional-spec.md

import React from "react";

export default function Toolbar({
  onAddRule = () => { },
  onSync = () => { },
  onExport = () => { },
  onToggleFilters = () => { },
  onToggleInspector = () => { },
  syncing = false,
  filtersVisible = true,
  inspectorVisible = true,
  onBack = null,
  backLabel = "Back",
  onToggleFullscreen = null,
  isFullscreen = false,
  children,
}) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-6">
        {onBack && (
          <button
            onClick={onBack}
            className="flex items-center gap-2 px-3 py-2 rounded-full bg-white/40 border border-neutral-200/60 text-sm font-medium text-neutral-600 hover:text-[#111] hover:border-[#B9C7F5] transition-all"
          >
            <span className="text-lg">←</span>
            {backLabel}
          </button>
        )}
        <h1 className="text-lg font-medium tracking-tight text-[#111]">metricx Canvas</h1>
      </div>
      <div className="flex-1 flex justify-center max-w-md mx-8">{children /* search slot */}</div>
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleFilters}
          className={`px-4 py-2 rounded-full border text-sm font-medium transition-all ${filtersVisible ? "bg-white/60 border-neutral-200/60 text-[#111]" : "bg-white/30 border-transparent text-neutral-500"
            }`}
        >
          Filters
        </button>
        <button
          onClick={onToggleInspector}
          className={`px-4 py-2 rounded-full border text-sm font-medium transition-all ${inspectorVisible ? "bg-white/60 border-neutral-200/60 text-[#111]" : "bg-white/30 border-transparent text-neutral-500"
            }`}
        >
          Inspector
        </button>
        <button onClick={onAddRule} className="px-4 py-2 rounded-full bg-white/60 border border-neutral-200/60 text-sm font-medium text-[#111] hover:border-[#B9C7F5] transition-all">Add Rule</button>
        <button
          onClick={onSync}
          disabled={syncing}
          className={`px-4 py-2 rounded-full border text-sm font-medium transition-all ${syncing
              ? "bg-white/40 border-neutral-200/80 text-neutral-400 cursor-not-allowed"
              : "bg-white/60 border-neutral-200/60 text-[#111] hover:border-[#B9C7F5]"
            }`}
        >
          {syncing ? "Syncing…" : "Sync"}
        </button>
        <button onClick={onExport} className="px-4 py-2 rounded-full bg-white/60 border border-neutral-200/60 text-sm font-medium text-[#111] hover:border-[#B9C7F5] transition-all">Export Flow</button>
        {onToggleFullscreen && (
          <button
            onClick={onToggleFullscreen}
            className="px-4 py-2 rounded-full bg-white/60 border border-neutral-200/60 text-sm font-medium text-[#111] hover:border-[#B9C7F5] transition-all"
            title="Toggle Fullscreen"
          >
            {isFullscreen ? "Exit Fullscreen" : "Fullscreen"}
          </button>
        )}
      </div>
    </div>
  );
}
