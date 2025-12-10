/**
 * PlatformBadge Component
 * =======================
 *
 * WHAT: Displays ad platform icon and label (Meta, Google, etc.)
 * WHY: Consistent platform identification across campaigns UI
 *
 * PLATFORMS:
 *   - Meta/Facebook: Blue dot, Facebook icon
 *   - Google: Multi-color Google icon
 *   - YouTube: Red dot, YouTube icon
 *   - TikTok: Black dot
 *
 * REFERENCES:
 *   - ui/components/campaigns/CampaignRow.jsx
 *   - ui/components/campaigns/CampaignDetailModal.jsx
 */

import { Facebook, Instagram, Youtube, Search } from "lucide-react";

/**
 * Google SVG icon for proper branding.
 */
function GoogleIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.84z" fill="#FBBC05" />
      <path d="M12 4.6c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 1.09 14.97 0 12 0 7.7 0 3.99 2.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
    </svg>
  );
}

/**
 * Size configurations for the badge.
 */
const SIZE_CONFIG = {
  sm: {
    container: "gap-1.5 px-2.5 py-1 text-[10px]",
    dot: "w-1 h-1",
    icon: "w-3 h-3",
  },
  md: {
    container: "gap-2 px-3 py-1.5 text-xs",
    dot: "w-1.5 h-1.5",
    icon: "w-4 h-4",
  },
  lg: {
    container: "gap-2.5 p-3 text-sm rounded-2xl",
    dot: "w-2 h-2",
    icon: "w-6 h-6",
  },
};

/**
 * PlatformBadge - Displays platform icon/label badge.
 *
 * @param {Object} props
 * @param {string} props.platform - Platform name (meta, google, etc.)
 * @param {string} [props.size="sm"] - Size variant: "sm" | "md" | "lg"
 * @param {boolean} [props.iconOnly=false] - Show only icon (no label)
 * @param {string} [props.className] - Additional CSS classes
 *
 * @example
 * // Basic usage
 * <PlatformBadge platform="meta" />
 *
 * // Large variant for modal header
 * <PlatformBadge platform="google" size="lg" />
 */
export default function PlatformBadge({ platform, size = "sm", iconOnly = false, className = "" }) {
  const normalized = platform?.toLowerCase().replace(/\s+ads?$/i, "").trim() || "";
  const sizeClasses = SIZE_CONFIG[size] || SIZE_CONFIG.sm;

  let label = platform || "—";
  let dotColor = "bg-slate-400";
  let bgColor = "bg-white";
  let Icon = null;
  let useGoogleIcon = false;

  if (normalized === "meta" || normalized === "facebook") {
    label = "Meta";
    dotColor = "bg-blue-500";
    bgColor = size === "lg" ? "bg-blue-50" : "bg-white";
    Icon = Facebook;
  } else if (normalized === "instagram") {
    label = "Meta";
    dotColor = "bg-purple-500";
    bgColor = size === "lg" ? "bg-purple-50" : "bg-white";
    Icon = Instagram;
  } else if (normalized === "google") {
    label = "Google";
    dotColor = "bg-blue-500";
    bgColor = size === "lg" ? "bg-white border-slate-100" : "bg-white";
    useGoogleIcon = true;
  } else if (normalized === "youtube") {
    label = "YouTube";
    dotColor = "bg-red-500";
    bgColor = size === "lg" ? "bg-red-50" : "bg-white";
    Icon = Youtube;
  }

  // Large size renders as icon-only box
  if (size === "lg") {
    return (
      <div className={`${sizeClasses.container} ${bgColor} rounded-2xl border border-slate-100 shadow-sm ${className}`}>
        {useGoogleIcon ? (
          <GoogleIcon className={sizeClasses.icon} />
        ) : Icon ? (
          <Icon className={`${sizeClasses.icon} ${normalized === "meta" || normalized === "facebook" ? "text-blue-600" : normalized === "youtube" ? "text-red-600" : "text-slate-600"}`} />
        ) : (
          <span className={`${sizeClasses.dot} rounded-full ${dotColor}`} />
        )}
      </div>
    );
  }

  return (
    <span className={`inline-flex items-center ${sizeClasses.container} rounded-full border border-slate-200 ${bgColor} font-medium text-slate-600 ${className}`}>
      {!iconOnly && <span className={`${sizeClasses.dot} rounded-full ${dotColor}`} />}
      {useGoogleIcon ? (
        <GoogleIcon className={sizeClasses.icon} />
      ) : Icon ? (
        <Icon className={`${sizeClasses.icon} text-slate-500`} />
      ) : null}
      {!iconOnly && <span>{label}</span>}
    </span>
  );
}
