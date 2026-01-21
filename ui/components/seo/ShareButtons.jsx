/**
 * Social Share Buttons Component
 *
 * WHAT: Renders social sharing buttons for content pages
 * WHY: Social shares can drive traffic and indirectly support SEO
 *      through increased visibility and potential backlinks
 *
 * @example
 * import { ShareButtons } from '@/components/seo/ShareButtons';
 *
 * <ShareButtons
 *   url="https://www.metricx.ai/glossary/roas"
 *   title="What is ROAS?"
 *   description="Learn about Return on Ad Spend..."
 * />
 */

"use client";

import { useState } from "react";
import {
  Twitter,
  Linkedin,
  Facebook,
  Link2,
  Check,
  Share2,
} from "lucide-react";

/**
 * Social share button group.
 *
 * @param {Object} props - Component props
 * @param {string} props.url - URL to share
 * @param {string} props.title - Share title
 * @param {string} [props.description] - Share description
 * @param {string} [props.className] - Additional CSS classes
 * @param {"horizontal" | "vertical"} [props.layout] - Button layout
 * @param {boolean} [props.showLabels] - Show button labels
 * @returns {JSX.Element} Share buttons
 */
export function ShareButtons({
  url,
  title,
  description = "",
  className = "",
  layout = "horizontal",
  showLabels = false,
}) {
  const [copied, setCopied] = useState(false);

  const encodedUrl = encodeURIComponent(url);
  const encodedTitle = encodeURIComponent(title);
  const encodedDescription = encodeURIComponent(description);

  const shareLinks = [
    {
      name: "Twitter",
      icon: Twitter,
      href: `https://twitter.com/intent/tweet?url=${encodedUrl}&text=${encodedTitle}`,
      color: "hover:bg-sky-100 hover:text-sky-600",
    },
    {
      name: "LinkedIn",
      icon: Linkedin,
      href: `https://www.linkedin.com/sharing/share-offsite/?url=${encodedUrl}`,
      color: "hover:bg-blue-100 hover:text-blue-600",
    },
    {
      name: "Facebook",
      icon: Facebook,
      href: `https://www.facebook.com/sharer/sharer.php?u=${encodedUrl}`,
      color: "hover:bg-indigo-100 hover:text-indigo-600",
    },
  ];

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy link:", err);
    }
  };

  const layoutClass =
    layout === "vertical" ? "flex-col" : "flex-row flex-wrap";

  return (
    <div className={`share-buttons flex ${layoutClass} gap-2 ${className}`}>
      {shareLinks.map((link) => (
        <a
          key={link.name}
          href={link.href}
          target="_blank"
          rel="noopener noreferrer"
          className={`inline-flex items-center gap-2 px-3 py-2 text-sm text-slate-600 bg-slate-100 rounded-lg transition-colors ${link.color}`}
          aria-label={`Share on ${link.name}`}
        >
          <link.icon className="w-4 h-4" />
          {showLabels && <span>{link.name}</span>}
        </a>
      ))}

      {/* Copy Link Button */}
      <button
        onClick={handleCopyLink}
        className={`inline-flex items-center gap-2 px-3 py-2 text-sm text-slate-600 bg-slate-100 rounded-lg transition-colors ${
          copied
            ? "bg-emerald-100 text-emerald-600"
            : "hover:bg-slate-200"
        }`}
        aria-label="Copy link"
      >
        {copied ? (
          <>
            <Check className="w-4 h-4" />
            {showLabels && <span>Copied!</span>}
          </>
        ) : (
          <>
            <Link2 className="w-4 h-4" />
            {showLabels && <span>Copy Link</span>}
          </>
        )}
      </button>
    </div>
  );
}

/**
 * Compact share button with dropdown.
 *
 * @param {Object} props - Component props
 * @param {string} props.url - URL to share
 * @param {string} props.title - Share title
 * @returns {JSX.Element} Compact share button
 */
export function CompactShareButton({ url, title }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="inline-flex items-center gap-2 px-3 py-1.5 text-sm text-slate-600 hover:text-slate-900 transition-colors"
        aria-label="Share"
      >
        <Share2 className="w-4 h-4" />
        <span>Share</span>
      </button>

      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />

          {/* Dropdown */}
          <div className="absolute right-0 top-full mt-2 z-20 bg-white rounded-lg shadow-lg border border-slate-200 p-2 min-w-[160px]">
            <ShareButtons
              url={url}
              title={title}
              layout="vertical"
              showLabels
              className="flex-col"
            />
          </div>
        </>
      )}
    </div>
  );
}

/**
 * Native share button (uses Web Share API when available).
 *
 * @param {Object} props - Component props
 * @param {string} props.url - URL to share
 * @param {string} props.title - Share title
 * @param {string} [props.description] - Share description
 * @returns {JSX.Element|null} Native share button or null if not supported
 */
export function NativeShareButton({ url, title, description }) {
  const canShare =
    typeof navigator !== "undefined" &&
    navigator.share &&
    navigator.canShare?.({ url, title });

  if (!canShare) return null;

  const handleShare = async () => {
    try {
      await navigator.share({
        url,
        title,
        text: description,
      });
    } catch (err) {
      // User cancelled or share failed
      if (err.name !== "AbortError") {
        console.error("Share failed:", err);
      }
    }
  };

  return (
    <button
      onClick={handleShare}
      className="inline-flex items-center gap-2 px-3 py-1.5 text-sm text-slate-600 hover:text-cyan-600 transition-colors"
      aria-label="Share"
    >
      <Share2 className="w-4 h-4" />
      <span>Share</span>
    </button>
  );
}

export default ShareButtons;
