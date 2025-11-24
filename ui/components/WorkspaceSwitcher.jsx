"use client";

import { useEffect, useState, useTransition } from "react";
import { ChevronDown, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { currentUser } from "@/lib/auth";

/**
 * Workspace switcher dropdown.
 * Pulls memberships from currentUser(). Switch calls backend /workspaces/{id}/switch.
 */
export default function WorkspaceSwitcher({ user }) {
  const [memberships, setMemberships] = useState(user?.memberships || []);
  const [activeId, setActiveId] = useState(user?.active_workspace_id || user?.workspace_id);
  const [pending, startTransition] = useTransition();

  useEffect(() => {
    setMemberships(user?.memberships || []);
    setActiveId(user?.active_workspace_id || user?.workspace_id);
  }, [user]);

  const handleSwitch = (workspaceId) => {
    if (!workspaceId || workspaceId === activeId) return;
    startTransition(() => {
      fetch(`${process.env.NEXT_PUBLIC_API_BASE}/workspaces/${workspaceId}/switch`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
      })
        .then((res) => {
          if (!res.ok) return res.text().then((t) => Promise.reject(t));
          return res.json();
        })
        .then(() => currentUser()) // refresh user context
        .then((fresh) => {
          setActiveId(fresh.active_workspace_id || fresh.workspace_id);
          setMemberships(fresh.memberships || []);
          toast.success("Workspace switched");
          // Hard refresh to reload data in new workspace
          window.location.reload();
        })
        .catch((err) => {
          console.error("Workspace switch failed", err);
          toast.error("Unable to switch workspace");
        });
    });
  };

  if (!memberships || memberships.length === 0) return null;

  const active = memberships.find((m) => m.workspace_id === activeId) || memberships[0];

  return (
    <div className="relative inline-block text-left">
      <button
        className="inline-flex items-center gap-2 px-3 py-2 rounded-xl border border-slate-200 bg-white shadow-sm text-sm font-medium text-slate-700 hover:border-cyan-200 hover:text-cyan-700 transition-colors"
        disabled={pending}
      >
        {pending ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
        <span className="truncate max-w-[220px]">{active?.workspace_name || active?.name || "Workspace"}</span>
        <ChevronDown className="w-4 h-4 text-slate-400" />
      </button>
      <div className="absolute right-0 mt-2 w-64 origin-top-right rounded-2xl border border-slate-200 bg-white shadow-lg z-20">
        <div className="py-2">
          {memberships.map((m) => {
            const isActive = m.workspace_id === activeId;
            return (
              <button
                key={m.workspace_id}
                onClick={() => handleSwitch(m.workspace_id)}
                className={`w-full text-left px-3 py-2 text-sm flex items-center justify-between hover:bg-slate-50 ${
                  isActive ? "text-cyan-700 font-semibold" : "text-slate-700"
                }`}
              >
                <span className="truncate max-w-[200px]">
                  {m.workspace_name || m.name || "Workspace"}
                </span>
                <span className="text-xs text-slate-400 capitalize">{m.role?.toLowerCase?.() || m.role}</span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
