"use client";

/**
 * AgentPreviewCard Component
 *
 * WHAT: Renders agent creation preview with confirm/edit actions.
 *
 * WHY: Provides deterministic UI for agent creation instead of relying
 * on LLM to follow instructions. Users see exactly what will be created
 * and can confirm or edit before the agent is active.
 *
 * FLOW:
 * 1. User asks copilot to create an agent
 * 2. Backend returns preview data (not created yet)
 * 3. This card renders with Create/Edit buttons
 * 4. User clicks Create → API call creates agent
 * 5. User clicks Edit → Opens agent wizard with pre-filled values
 *
 * REFERENCES:
 * - backend/app/agent/tools.py (create_agent tool)
 * - ui/app/(dashboard)/agents/new/page.jsx (wizard)
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Bot, Check, Pencil, Zap, Bell, Clock, Target } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { createAgent } from "@/lib/api";
import { toast } from "sonner";
import { motion } from "framer-motion";

export default function AgentPreviewCard({ preview, workspaceId, onCreated }) {
  const router = useRouter();
  const [isCreating, setIsCreating] = useState(false);
  const [isCreated, setIsCreated] = useState(false);

  const handleCreate = async () => {
    setIsCreating(true);
    try {
      // Build agent payload from preview
      const agentPayload = {
        workspaceId,
        name: preview.name,
        description: `Created via Copilot`,
        scope_type: "all",
        scope_config: {
          level: "campaign",
          provider: preview.scope?.includes("Google")
            ? "google"
            : preview.scope?.includes("Meta")
            ? "meta"
            : undefined,
        },
        condition: {
          type: "threshold",
          metric: extractMetric(preview.condition),
          operator: extractOperator(preview.condition),
          value: extractValue(preview.condition),
        },
        accumulation: {
          required: 1,
          unit: "evaluations",
          mode: "consecutive",
        },
        trigger: {
          mode: "once",
        },
        actions: [
          {
            type: "email",
            config: {
              subject_template: `Agent "${preview.name}" triggered on {{entity_name}}`,
              body_template: `Your monitoring agent has triggered.\n\nCondition: ${preview.condition}`,
            },
          },
        ],
        status: "active",
      };

      const agent = await createAgent(agentPayload);
      setIsCreated(true);
      toast.success(`Agent "${preview.name}" created successfully!`);

      if (onCreated) {
        onCreated(agent);
      }
    } catch (err) {
      console.error("Failed to create agent:", err);
      toast.error("Failed to create agent. Please try again.");
    } finally {
      setIsCreating(false);
    }
  };

  const handleEdit = () => {
    // Navigate to wizard with pre-filled values via query params
    const params = new URLSearchParams();
    params.set("name", preview.name || "");
    params.set("condition", preview.condition || "");
    params.set("scope", preview.scope || "");
    router.push(`/agents/new?${params.toString()}`);
  };

  if (isCreated) {
    return (
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.3 }}
      >
        <Card className="bg-emerald-50/80 border-emerald-200/50">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3 text-emerald-700">
              <div className="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center">
                <Check className="w-5 h-5" />
              </div>
              <div>
                <p className="font-medium">Agent Created!</p>
                <p className="text-sm text-emerald-600">
                  "{preview.name}" is now active and monitoring.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ y: 10, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.4, ease: [0.23, 1, 0.32, 1] }}
    >
      <Card className="bg-gradient-to-br from-blue-50/80 to-indigo-50/60 border-blue-200/50 overflow-hidden">
        <CardHeader className="pb-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white shadow-lg shadow-blue-500/25">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <CardTitle className="text-base font-semibold text-slate-800">
                Create Agent
              </CardTitle>
              <p className="text-xs text-slate-500">
                Review and confirm before activating
              </p>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* Agent Name */}
          <div className="bg-white/60 rounded-lg p-3 border border-slate-200/50">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-1">
              Agent Name
            </p>
            <p className="text-sm font-semibold text-slate-800">{preview.name}</p>
          </div>

          {/* Configuration Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {/* Condition */}
            <div className="bg-white/60 rounded-lg p-3 border border-slate-200/50">
              <div className="flex items-center gap-2 mb-1">
                <Target className="w-3.5 h-3.5 text-blue-500" />
                <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">
                  Condition
                </p>
              </div>
              <p className="text-sm text-slate-700">{preview.condition}</p>
            </div>

            {/* Scope */}
            <div className="bg-white/60 rounded-lg p-3 border border-slate-200/50">
              <div className="flex items-center gap-2 mb-1">
                <Zap className="w-3.5 h-3.5 text-amber-500" />
                <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">
                  Scope
                </p>
              </div>
              <p className="text-sm text-slate-700">{preview.scope}</p>
            </div>

            {/* Action */}
            <div className="bg-white/60 rounded-lg p-3 border border-slate-200/50">
              <div className="flex items-center gap-2 mb-1">
                <Bell className="w-3.5 h-3.5 text-emerald-500" />
                <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">
                  Action
                </p>
              </div>
              <p className="text-sm text-slate-700">{preview.action || "Email notification"}</p>
            </div>

            {/* Frequency */}
            <div className="bg-white/60 rounded-lg p-3 border border-slate-200/50">
              <div className="flex items-center gap-2 mb-1">
                <Clock className="w-3.5 h-3.5 text-purple-500" />
                <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">
                  Frequency
                </p>
              </div>
              <p className="text-sm text-slate-700">{preview.frequency || "Every 15 minutes"}</p>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 pt-2">
            <Button
              onClick={handleCreate}
              disabled={isCreating}
              className="flex-1 bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white shadow-lg shadow-blue-500/25"
            >
              {isCreating ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2" />
                  Creating...
                </>
              ) : (
                <>
                  <Check className="w-4 h-4 mr-2" />
                  Create Agent
                </>
              )}
            </Button>
            <Button
              onClick={handleEdit}
              variant="outline"
              className="border-slate-300 hover:bg-slate-100"
            >
              <Pencil className="w-4 h-4 mr-2" />
              Edit
            </Button>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

// Helper functions to parse condition string
function extractMetric(condition) {
  const metrics = ["roas", "cpc", "ctr", "cpa", "spend", "revenue", "conversions"];
  const lower = (condition || "").toLowerCase();
  for (const m of metrics) {
    if (lower.includes(m)) return m;
  }
  return "roas";
}

function extractOperator(condition) {
  const lower = (condition || "").toLowerCase();
  if (lower.includes("above") || lower.includes(">")) return ">";
  if (lower.includes("below") || lower.includes("<")) return "<";
  return "<";
}

function extractValue(condition) {
  const match = (condition || "").match(/\$?([\d.]+)/);
  return match ? parseFloat(match[1]) : 0;
}
