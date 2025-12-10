// Workspace summary block shows current workspace and quick meta
// WHY: Container component that fetches workspace info from API
// This allows the sidebar to show real-time sync status

import { useEffect, useState, useTransition } from "react";
import { fetchWorkspaceInfo } from "../lib/api";
import WorkspaceSwitcher from "./WorkspaceSwitcher";
import { currentUser } from "../lib/workspace";

export default function WorkspaceSummary({ workspaceId }) {
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [user, setUser] = useState(null);
  const [refreshing, startTransition] = useTransition();

  useEffect(() => {
    if (!workspaceId) return;

    let mounted = true;

    const load = async () => {
      try {
        const u = await currentUser();
        if (mounted) setUser(u);
      } catch {
        // ignore
      }

      fetchWorkspaceInfo(workspaceId)
        .then((data) => {
          if (mounted) {
            setInfo(data);
            setError(null);
          }
        })
        .catch((err) => {
          if (mounted) {
            setError(err.message);
          }
        })
        .finally(() => {
          if (mounted) {
            setLoading(false);
          }
        });
    };

    load();

    return () => {
      mounted = false;
    };
  }, [workspaceId]);

  // Format last sync time
  const formatLastSync = (timestamp) => {
    if (!timestamp) return "Never";
    
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins} min ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    
    // For older dates, show the actual date
    return date.toLocaleDateString();
  };

  if (loading) {
    return (
      <div className="rounded-xl p-4 border border-slate-800/60 bg-slate-900/40">
        <h4 className="text-sm font-medium text-slate-300 mb-3">Current Workspace</h4>
        <div className="space-y-2 text-xs text-slate-400">
          <div className="animate-pulse">
            <div className="h-4 bg-slate-700 rounded w-24 mb-2"></div>
            <div className="h-3 bg-slate-700 rounded w-32"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl p-4 border border-red-800/60 bg-red-900/20">
        <h4 className="text-sm font-medium text-red-300 mb-1">Workspace Error</h4>
        <div className="text-xs text-red-400">{error}</div>
      </div>
    );
  }

  if (!info) return null;

  return (
    <div className="rounded-xl p-4 border border-slate-800/60 bg-slate-900/40 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h4 className="text-sm font-medium text-slate-300">Current Workspace</h4>
          <div className="text-xs text-slate-400 mt-1">Last sync: {formatLastSync(info.last_sync)}</div>
        </div>
        {user && <WorkspaceSwitcher user={user} />}
      </div>
      <div className="space-y-2 text-xs text-slate-400">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400" aria-hidden />
          <span className="text-slate-200">{info.name}</span>
        </div>
        <div className="flex items-center justify-between pt-2">
          <span>Active: {user?.active_workspace_id === workspaceId ? "Yes" : "No"}</span>
          <button
            className="hover:text-white transition-colors"
            aria-label="Refresh"
            onClick={() => startTransition(() => window.location.reload())}
          >
            {refreshing ? "…" : "↻"}
          </button>
        </div>
      </div>
    </div>
  );
}
