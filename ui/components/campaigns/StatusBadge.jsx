/**
 * StatusBadge Component
 * =====================
 *
 * WHAT: Displays campaign/entity status with appropriate styling
 * WHY: Unified status display across campaigns list and detail modal
 *
 * STATUS MAPPING:
 * - Meta: ACTIVE, PAUSED, ARCHIVED, DELETED, LEARNING (from effective_status)
 * - Google: ENABLED, PAUSED, REMOVED, LEARNING (from bidding_strategy_system_status)
 *
 * REFERENCES:
 *   - Meta Marketing API: effective_status field
 *   - Google Ads API: campaign.status, bidding_strategy_system_status
 *   - ui/app/(dashboard)/campaigns/page.jsx (parent consumer)
 */

import { Circle, Pause, Archive, Trash2, Zap, AlertCircle, Eye, Clock } from "lucide-react";

/**
 * Maps raw status strings to normalized status keys.
 * Handles variations from both Meta and Google APIs.
 *
 * @param {string} status - Raw status from API
 * @returns {string} Normalized status key
 */
export function normalizeStatus(status) {
  if (!status) return "unknown";
  const s = status.toLowerCase().trim();

  // Active states
  if (["active", "enabled", "delivering", "in_process", "with_issues"].includes(s)) {
    return "active";
  }

  // Paused states
  if (["paused", "campaign_paused", "adset_paused", "user_paused"].includes(s)) {
    return "paused";
  }

  // Learning states (Meta's effective_status or Google's bidding_strategy_system_status)
  if (["learning", "learning_limited", "pending"].includes(s)) {
    return "learning";
  }

  // Archived/Removed states
  if (["archived", "removed", "deleted"].includes(s)) {
    return "archived";
  }

  // Pending review states
  if (["pending_review", "in_review", "preapproved", "pending_billing_info"].includes(s)) {
    return "pending";
  }

  // Error/Disapproved states
  if (["disapproved", "rejected", "error", "misconfigured"].includes(s)) {
    return "error";
  }

  // Draft states
  if (["draft", "not_delivering"].includes(s)) {
    return "draft";
  }

  return "unknown";
}

/**
 * Status configuration with styling and icons.
 */
const STATUS_CONFIG = {
  active: {
    label: "Active",
    className: "bg-emerald-50 text-emerald-700 border-emerald-200",
    dotColor: "bg-emerald-500",
    Icon: Circle,
    iconFill: true,
  },
  paused: {
    label: "Paused",
    className: "bg-amber-50 text-amber-700 border-amber-200",
    dotColor: "bg-amber-500",
    Icon: Pause,
    iconFill: false,
  },
  learning: {
    label: "Learning",
    className: "bg-sky-50 text-sky-700 border-sky-200",
    dotColor: "bg-sky-500",
    Icon: Zap,
    iconFill: false,
    animate: true,
  },
  archived: {
    label: "Archived",
    className: "bg-slate-100 text-slate-500 border-slate-200",
    dotColor: "bg-slate-400",
    Icon: Archive,
    iconFill: false,
  },
  pending: {
    label: "Pending",
    className: "bg-violet-50 text-violet-700 border-violet-200",
    dotColor: "bg-violet-500",
    Icon: Clock,
    iconFill: false,
  },
  error: {
    label: "Error",
    className: "bg-red-50 text-red-700 border-red-200",
    dotColor: "bg-red-500",
    Icon: AlertCircle,
    iconFill: false,
  },
  draft: {
    label: "Draft",
    className: "bg-slate-50 text-slate-500 border-slate-200",
    dotColor: "bg-slate-400",
    Icon: Eye,
    iconFill: false,
  },
  unknown: {
    label: "Unknown",
    className: "bg-slate-50 text-slate-400 border-slate-200",
    dotColor: "bg-slate-300",
    Icon: Circle,
    iconFill: false,
  },
};

/**
 * StatusBadge - Displays campaign/entity status.
 *
 * @param {Object} props
 * @param {string} props.status - Raw status string from API
 * @param {string} [props.size="sm"] - Size variant: "sm" | "md" | "lg"
 * @param {boolean} [props.showIcon=true] - Whether to show status icon
 * @param {boolean} [props.showDot=false] - Show animated dot instead of icon
 * @param {string} [props.className] - Additional CSS classes
 *
 * @example
 * // Basic usage
 * <StatusBadge status="active" />
 *
 * // With dot indicator
 * <StatusBadge status="learning" showDot showIcon={false} />
 *
 * // Large variant for modals
 * <StatusBadge status="paused" size="lg" />
 */
export default function StatusBadge({
  status,
  size = "sm",
  showIcon = true,
  showDot = false,
  className = "",
}) {
  const normalizedStatus = normalizeStatus(status);
  const config = STATUS_CONFIG[normalizedStatus] || STATUS_CONFIG.unknown;
  const { label, className: statusClassName, dotColor, Icon, iconFill, animate } = config;

  // Size variants
  const sizeClasses = {
    sm: "px-2 py-0.5 text-[10px] gap-1",
    md: "px-2.5 py-1 text-xs gap-1.5",
    lg: "px-3 py-1.5 text-sm gap-2",
  };

  const iconSizes = {
    sm: "w-2.5 h-2.5",
    md: "w-3 h-3",
    lg: "w-3.5 h-3.5",
  };

  const dotSizes = {
    sm: "w-1.5 h-1.5",
    md: "w-2 h-2",
    lg: "w-2.5 h-2.5",
  };

  return (
    <span
      className={`
        inline-flex items-center font-medium rounded-md border
        ${statusClassName}
        ${sizeClasses[size]}
        ${className}
      `}
    >
      {showDot && (
        <span className={`${dotSizes[size]} ${dotColor} rounded-full ${animate ? "animate-pulse" : ""}`} />
      )}
      {showIcon && !showDot && (
        <Icon
          className={`${iconSizes[size]} ${animate ? "animate-pulse" : ""}`}
          fill={iconFill ? "currentColor" : "none"}
        />
      )}
      <span>{label}</span>
    </span>
  );
}

/**
 * StatusDot - Minimal status indicator (just a colored dot).
 *
 * @param {Object} props
 * @param {string} props.status - Raw status string from API
 * @param {string} [props.size="sm"] - Size variant
 * @param {string} [props.className] - Additional CSS classes
 *
 * @example
 * <StatusDot status="active" />
 */
export function StatusDot({ status, size = "sm", className = "" }) {
  const normalizedStatus = normalizeStatus(status);
  const config = STATUS_CONFIG[normalizedStatus] || STATUS_CONFIG.unknown;
  const { dotColor, animate } = config;

  const dotSizes = {
    sm: "w-1.5 h-1.5",
    md: "w-2 h-2",
    lg: "w-2.5 h-2.5",
  };

  return (
    <span
      className={`
        inline-block rounded-full
        ${dotColor}
        ${dotSizes[size]}
        ${animate ? "animate-pulse" : ""}
        ${className}
      `}
    />
  );
}
