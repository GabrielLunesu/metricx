"use client";
// WHAT: Canvas route entry — lazy loads React Flow viewport with mock data (flagged off by default)
// WHY: Provide a standalone page for the Campaign Canvas without impacting existing pages
// REFERENCES: docs/canvas/01-functional-spec.md, ui/lib/features.js

import React, { Suspense, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { currentUser } from "@/lib/workspace";
import features from "@/lib/features";
import { useRouter } from "next/navigation";

// Feature components (local imports)
import CanvasShell from "@/features/canvas/components/CanvasShell";
import Toolbar from "@/features/canvas/components/Toolbar";
import SidebarLeft from "@/features/canvas/components/Sidebar.Left";
import SidebarRight from "@/features/canvas/components/Sidebar.Right";
import NodeCampaign from "@/features/canvas/components/Node.Campaign";
import NodeAdSet from "@/features/canvas/components/Node.AdSet";
import NodeAd from "@/features/canvas/components/Node.Ad";
import useCanvasData from "@/features/canvas/hooks/useCanvasData";
import Legends from "@/features/canvas/components/Legends";

// Lazy-load React Flow viewport to keep initial bundle lean
const FlowViewport = dynamic(() => import("@/features/canvas/components/FlowViewport"), { ssr: false });

export default function CanvasPage() {
  const [user, setUser] = React.useState(null);
  const [workspaceId, setWorkspaceId] = React.useState(null);
  const [filters, setFilters] = useState({
    timeframe: "7d",
    status: "active",
    platform: null,
    showEdges: true,
    showAds: true,
    query: "",
    platforms: { meta: true, google: true, tiktok: false },
  });
  const [selection, setSelection] = useState(null);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [inspectorOpen, setInspectorOpen] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const router = useRouter();
  const containerRef = useRef(null);

  const updateFilters = React.useCallback((updater) => {
    setFilters((prev) => {
      const resolved = typeof updater === "function" ? updater(prev) : updater;
      const selectedPlatforms = Object.entries(resolved.platforms || {}).filter(([, enabled]) => enabled);
      const platform = selectedPlatforms.length === 1 ? selectedPlatforms[0][0] : null;
      return { ...resolved, platform };
    });
  }, []);

  React.useEffect(() => {
    let mounted = true;
    currentUser().then((u) => {
      if (!mounted) return;
      setUser(u);
      setWorkspaceId(u?.workspace_id || null);
    }).catch(() => { if (mounted) { setUser(null); setWorkspaceId(null); } });
    return () => { mounted = false; };
  }, []);

  const { nodes, edges, loading, error, reload, lastSyncedAt } = useCanvasData({ workspaceId, filters });

  const filteredGraph = useMemo(() => {
    if (!filters.query) return { nodes, edges };
    const term = filters.query.toLowerCase();
    const matched = new Set();
    nodes.forEach((node) => {
      if (node?.data?.name?.toLowerCase().includes(term)) {
        matched.add(node.id);
      }
    });
    if (matched.size === 0) {
      return { nodes: [], edges: [] };
    }
    const related = new Set(matched);
    edges.forEach((edge) => {
      if (matched.has(edge.source) || matched.has(edge.target)) {
        related.add(edge.source);
        related.add(edge.target);
      }
    });
    const nextNodes = nodes.filter((node) => related.has(node.id));
    const nextEdges = edges.filter((edge) => related.has(edge.source) && related.has(edge.target));
    return { nodes: nextNodes, edges: nextEdges };
  }, [nodes, edges, filters.query]);

  React.useEffect(() => {
    if (!selection) return;
    const exists = filteredGraph.nodes.some((node) => node.id === selection.id);
    if (!exists) {
      setSelection(null);
    }
  }, [filteredGraph.nodes, selection]);

  const nodeTypes = useMemo(() => ({
    campaign: NodeCampaign,
    adset: NodeAdSet,
    ad: NodeAd,
  }), []);

  const handleNodeClick = React.useCallback((_, node) => {
    setSelection(node);
    setInspectorOpen(true);
  }, []);

  const handlePaneClick = React.useCallback(() => {
    setSelection(null);
  }, []);

  const handleSync = React.useCallback(() => {
    if (!workspaceId) return;
    setIsSyncing(true);
    reload();
  }, [workspaceId, reload]);

  React.useEffect(() => {
    if (!isSyncing) return;
    if (!loading) {
      setIsSyncing(false);
    }
  }, [loading, isSyncing]);

  const lastSyncDisplay = React.useMemo(() => {
    if (!lastSyncedAt) return "Never";
    // Append 'Z' to indicate UTC if no timezone is present (backend stores UTC)
    const dateStr = typeof lastSyncedAt === 'string' && !lastSyncedAt.includes('Z') && !lastSyncedAt.includes('+')
      ? lastSyncedAt + 'Z'
      : lastSyncedAt;
    const timestamp = lastSyncedAt instanceof Date ? lastSyncedAt : new Date(dateStr);
    if (Number.isNaN(timestamp.getTime())) return "Never";
    return timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }, [lastSyncedAt]);

  if (!features.canvas) {
    return (
      <div className="p-12 text-center">
        <div className="glass-card rounded-3xl border border-neutral-200/60 p-6 max-w-md mx-auto">
          <h2 className="text-xl font-medium mb-2 text-neutral-900">Canvas feature is disabled</h2>
          <p className="text-neutral-600 text-sm">Enable <code>features.canvas</code> to preview this page.</p>
        </div>
      </div>
    );
  }

  return (
    <CanvasShell
      immersive
      showLeftSidebar={filtersOpen}
      showRightSidebar={inspectorOpen}
      toolbar={(
        <Toolbar
          filtersVisible={filtersOpen}
          inspectorVisible={inspectorOpen}
          onToggleFilters={() => setFiltersOpen((prev) => !prev)}
          onToggleInspector={() => setInspectorOpen((prev) => !prev)}
          onBack={() => router.push("/dashboard")}
          backLabel="Back to Dashboard"
          onSync={handleSync}
          syncing={isSyncing || (loading && !lastSyncedAt)}
        >
          <div className="relative">
            <input
              type="text"
              value={filters.query || ""}
              placeholder="Search campaigns or rules…"
              onChange={(e) => updateFilters((prev) => ({ ...prev, query: e.target.value }))}
              className="w-full px-4 py-2 rounded-full bg-white/60 border border-neutral-200/60 text-sm text-[#111] placeholder-neutral-400 focus:outline-none focus:border-[#B9C7F5] transition-all"
            />
          </div>
        </Toolbar>
      )}
      leftSidebar={(
        <SidebarLeft filters={filters} onChange={updateFilters} />
      )}
      rightSidebar={(
        <SidebarRight
          selection={selection}
          onClose={() => {
            setInspectorOpen(false);
            setSelection(null);
          }}
          onSaveDraft={() => {}}
        />
      )}
    >
      <div ref={containerRef} className="flex-1 min-h-0 overflow-hidden flex rounded-3xl" style={{ height: "calc(100vh - 112px)" }}>
        {loading && (
          <div className="flex items-center justify-center flex-1 text-neutral-500 text-sm">Loading canvas…</div>
        )}
        {error && (
          <div className="flex items-center justify-center flex-1 text-red-500 text-sm">{error}</div>
        )}
        {!loading && !error && (
          <Suspense fallback={<div className="flex items-center justify-center flex-1 text-neutral-500">Loading canvas…</div>}>
            <FlowViewport
              className="h-full flex-1"
              initialNodes={filteredGraph.nodes}
              initialEdges={filteredGraph.edges}
              nodeTypes={nodeTypes}
              options={{
                fitView: false, // Disable auto-centering to respect our manual positioning
                defaultViewport: { x: 0, y: 0, zoom: 0.8 }, // Start at top-left to show left-positioned campaigns
                minZoom: 0.4,
                maxZoom: 1.8,
                defaultEdgeOptions: {
                  type: "bezier",
                  animated: true,
                  style: { stroke: "#B9C7F5", strokeWidth: 1.5, opacity: 0.85 },
                },
                panOnDrag: true,
                snapGrid: [10, 10],
                snapToGrid: true,
              }}
              onNodeClick={handleNodeClick}
              onPaneClick={handlePaneClick}
            />
          </Suspense>
        )}
      </div>

      <div className="flex items-center justify-between text-xs text-neutral-600 px-2">
        <Legends />
        <span>Last Sync: {lastSyncDisplay}</span>
      </div>
    </CanvasShell>
  );
}
