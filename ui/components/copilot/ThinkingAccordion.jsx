"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, Check, Loader2, AlertCircle, Database, Globe, Building2 } from "lucide-react";

/**
 * ThinkingAccordion - Collapsible panel showing agent's reasoning steps
 *
 * WHAT: ChatGPT-style collapsible "thinking" block that shows tool calls
 * WHY: Users can see what the agent is doing without cluttering the main answer
 *
 * PROPS:
 *   steps: Array of step objects:
 *     - { type: "tool_start", tool: "query_metrics", description: "Fetching spend, roas for 7d", timestamp: Date }
 *     - { type: "tool_end", tool: "query_metrics", preview: "spend: $1,234", success: true, duration_ms: 234, data_source: "snapshots" }
 *   isThinking: Boolean - whether agent is still processing
 *   defaultOpen: Boolean - whether to start expanded (default: true while thinking)
 */
export default function ThinkingAccordion({ steps = [], isThinking = false, defaultOpen = null }) {
  // Auto-expand while thinking, collapse when done
  const [isOpen, setIsOpen] = useState(defaultOpen ?? isThinking);

  // Group steps into pairs (start + end)
  const groupedSteps = groupSteps(steps);

  // Don't render if no steps
  if (groupedSteps.length === 0 && !isThinking) {
    return null;
  }

  // Calculate total time
  const totalTime = groupedSteps.reduce((sum, step) => sum + (step.duration_ms || 0), 0);

  return (
    <div className="mb-3">
      {/* Accordion Header */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 text-xs text-slate-500 hover:text-slate-700 transition-colors group"
      >
        <motion.div
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <ChevronDown className="w-3.5 h-3.5" />
        </motion.div>

        {isThinking ? (
          <span className="flex items-center gap-1.5">
            <Loader2 className="w-3 h-3 animate-spin text-blue-500" />
            <span className="text-blue-600 font-medium">Thinking...</span>
          </span>
        ) : (
          <span className="flex items-center gap-1.5">
            <Check className="w-3 h-3 text-green-500" />
            <span>
              {groupedSteps.length} step{groupedSteps.length !== 1 ? "s" : ""}
              {totalTime > 0 && (
                <span className="text-slate-400 ml-1">
                  ({formatDuration(totalTime)})
                </span>
              )}
            </span>
          </span>
        )}
      </button>

      {/* Accordion Content */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="mt-2 ml-1 pl-3 border-l-2 border-slate-200 space-y-2">
              {groupedSteps.map((step, index) => (
                <StepItem key={index} step={step} isLast={index === groupedSteps.length - 1} />
              ))}

              {/* Show pending step while thinking */}
              {isThinking && steps.length > 0 && !steps[steps.length - 1]?.type?.includes("end") && (
                <div className="flex items-center gap-2 text-xs text-slate-500">
                  <Loader2 className="w-3 h-3 animate-spin text-blue-500" />
                  <span className="italic">Processing...</span>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/**
 * Individual step item
 */
function StepItem({ step, isLast }) {
  const getIcon = () => {
    if (step.data_source?.includes("google")) {
      return <Globe className="w-3 h-3 text-blue-500" />;
    }
    if (step.data_source?.includes("meta")) {
      return <Globe className="w-3 h-3 text-blue-600" />;
    }
    if (step.data_source === "workspace_settings") {
      return <Building2 className="w-3 h-3 text-purple-500" />;
    }
    return <Database className="w-3 h-3 text-emerald-500" />;
  };

  const getStatusIcon = () => {
    if (step.success === false) {
      return <AlertCircle className="w-3 h-3 text-red-500" />;
    }
    if (step.success === true) {
      return <Check className="w-3 h-3 text-green-500" />;
    }
    return <Loader2 className="w-3 h-3 animate-spin text-blue-500" />;
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      className="flex items-start gap-2 text-xs"
    >
      {/* Icon */}
      <div className="mt-0.5 flex-shrink-0">
        {getIcon()}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        {/* Tool name and description */}
        <div className="flex items-center gap-1.5">
          <span className="font-medium text-slate-700">
            {formatToolName(step.tool)}
          </span>
          {step.duration_ms && (
            <span className="text-slate-400">
              {formatDuration(step.duration_ms)}
            </span>
          )}
          {getStatusIcon()}
        </div>

        {/* Description or preview */}
        {step.description && !step.preview && (
          <p className="text-slate-500 truncate">{step.description}</p>
        )}
        {step.preview && (
          <p className="text-slate-600 truncate">{step.preview}</p>
        )}

        {/* Data source badge */}
        {step.data_source && (
          <span className="inline-block mt-1 px-1.5 py-0.5 bg-slate-100 text-slate-500 rounded text-[10px]">
            {formatDataSource(step.data_source)}
          </span>
        )}
      </div>
    </motion.div>
  );
}

/**
 * Group tool_start and tool_end events into single step objects
 */
function groupSteps(steps) {
  const grouped = [];
  const pending = new Map(); // tool_name -> start event

  for (const step of steps) {
    if (step.type === "tool_start") {
      pending.set(step.tool, step);
    } else if (step.type === "tool_end") {
      const start = pending.get(step.tool);
      if (start) {
        grouped.push({
          tool: step.tool,
          description: start.description,
          preview: step.preview,
          success: step.success,
          duration_ms: step.duration_ms,
          data_source: step.data_source,
        });
        pending.delete(step.tool);
      } else {
        // No matching start, just add the end
        grouped.push(step);
      }
    }
  }

  // Add any pending starts that haven't finished
  for (const [tool, start] of pending) {
    grouped.push({
      tool,
      description: start.description,
      success: null, // Still running
    });
  }

  return grouped;
}

/**
 * Format tool name for display
 */
function formatToolName(toolName) {
  const names = {
    query_metrics: "Query Metrics",
    google_ads_query: "Google Ads",
    meta_ads_query: "Meta Ads",
    list_entities: "Find Campaigns",
    get_business_context: "Business Profile",
  };
  return names[toolName] || toolName;
}

/**
 * Format data source for display
 */
function formatDataSource(dataSource) {
  if (dataSource?.includes("snapshots")) return "Cached data";
  if (dataSource?.includes("live_google")) return "Live from Google";
  if (dataSource?.includes("live_meta")) return "Live from Meta";
  if (dataSource === "database") return "Database";
  if (dataSource === "workspace_settings") return "Settings";
  return dataSource;
}

/**
 * Format duration in human-readable form
 */
function formatDuration(ms) {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}
