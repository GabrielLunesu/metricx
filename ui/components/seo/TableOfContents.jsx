/**
 * Table of Contents Component
 *
 * WHAT: Renders a navigable table of contents for long-form content
 * WHY: Improves UX on long pages, helps users find relevant sections,
 *      and can be used for in-page anchor linking (good for SEO)
 *
 * @example
 * import { TableOfContents } from '@/components/seo/TableOfContents';
 *
 * <TableOfContents
 *   headings={[
 *     { id: "what-is-roas", text: "What is ROAS?", level: 2 },
 *     { id: "roas-formula", text: "ROAS Formula", level: 2 },
 *     { id: "examples", text: "Examples", level: 3 }
 *   ]}
 * />
 */

"use client";

import { useState, useEffect } from "react";
import { List, ChevronDown, ChevronUp } from "lucide-react";

/**
 * Table of Contents navigation.
 *
 * @param {Object} props - Component props
 * @param {Array<{id: string, text: string, level: number}>} props.headings - Content headings
 * @param {string} [props.title="On this page"] - Section title
 * @param {string} [props.className] - Additional CSS classes
 * @param {boolean} [props.sticky=false] - Make TOC sticky on scroll
 * @param {boolean} [props.collapsible=false] - Allow collapsing on mobile
 * @returns {JSX.Element} Table of contents
 */
export function TableOfContents({
  headings,
  title = "On this page",
  className = "",
  sticky = false,
  collapsible = false,
}) {
  const [activeId, setActiveId] = useState("");
  const [isCollapsed, setIsCollapsed] = useState(true);

  // Track active section on scroll
  useEffect(() => {
    if (!headings || headings.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setActiveId(entry.target.id);
          }
        });
      },
      {
        rootMargin: "-80px 0px -80% 0px",
        threshold: 0,
      }
    );

    headings.forEach((heading) => {
      const element = document.getElementById(heading.id);
      if (element) {
        observer.observe(element);
      }
    });

    return () => observer.disconnect();
  }, [headings]);

  if (!headings || headings.length === 0) return null;

  const handleClick = (id) => {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "start" });
      // Update URL hash without scrolling
      window.history.pushState(null, "", `#${id}`);
    }
  };

  return (
    <nav
      className={`toc ${sticky ? "sticky top-24" : ""} ${className}`}
      aria-label="Table of contents"
    >
      {/* Header */}
      <div
        className={`flex items-center justify-between ${
          collapsible ? "cursor-pointer" : ""
        }`}
        onClick={collapsible ? () => setIsCollapsed(!isCollapsed) : undefined}
      >
        <h2 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
          <List className="w-4 h-4" aria-hidden="true" />
          {title}
        </h2>
        {collapsible && (
          <button
            className="lg:hidden p-1"
            aria-label={isCollapsed ? "Expand" : "Collapse"}
          >
            {isCollapsed ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronUp className="w-4 h-4" />
            )}
          </button>
        )}
      </div>

      {/* TOC List */}
      <ul
        className={`mt-3 space-y-2 ${
          collapsible && isCollapsed ? "hidden lg:block" : ""
        }`}
      >
        {headings.map((heading) => {
          const isActive = activeId === heading.id;
          const indent = heading.level > 2 ? "pl-4" : "";

          return (
            <li key={heading.id} className={indent}>
              <button
                onClick={() => handleClick(heading.id)}
                className={`text-sm text-left transition-colors w-full ${
                  isActive
                    ? "text-cyan-600 font-medium"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                {heading.text}
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

/**
 * Floating TOC for long articles.
 *
 * @param {Object} props - Component props
 * @param {Array} props.headings - Content headings
 * @returns {JSX.Element} Floating TOC
 */
export function FloatingTOC({ headings }) {
  const [isOpen, setIsOpen] = useState(false);

  if (!headings || headings.length === 0) return null;

  return (
    <div className="fixed bottom-6 right-6 z-50">
      {/* Toggle Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-12 h-12 bg-cyan-600 text-white rounded-full shadow-lg flex items-center justify-center hover:bg-cyan-700 transition-colors"
        aria-label="Toggle table of contents"
      >
        <List className="w-5 h-5" />
      </button>

      {/* Popup TOC */}
      {isOpen && (
        <div className="absolute bottom-16 right-0 w-64 bg-white rounded-lg shadow-xl border border-slate-200 p-4 max-h-80 overflow-y-auto">
          <TableOfContents headings={headings} />
        </div>
      )}
    </div>
  );
}

/**
 * Extract headings from HTML content.
 *
 * WHAT: Parses HTML content to extract h2/h3 headings
 * WHY: Automatically generates TOC from content
 *
 * @param {string} html - HTML content
 * @returns {Array<{id: string, text: string, level: number}>} Extracted headings
 */
export function extractHeadings(html) {
  if (typeof window === "undefined") return [];

  const parser = new DOMParser();
  const doc = parser.parseFromString(html, "text/html");
  const headings = [];

  doc.querySelectorAll("h2, h3").forEach((heading) => {
    const text = heading.textContent || "";
    const id = heading.id || text.toLowerCase().replace(/\s+/g, "-");

    headings.push({
      id,
      text,
      level: parseInt(heading.tagName.charAt(1), 10),
    });
  });

  return headings;
}

export default TableOfContents;
