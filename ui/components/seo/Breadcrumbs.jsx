/**
 * Breadcrumb Navigation Component
 *
 * WHAT: Renders semantic breadcrumb navigation with JSON-LD schema
 * WHY: Breadcrumbs improve UX, help crawlers understand site structure,
 *      and can appear as rich snippets in search results
 *
 * Related files:
 * - lib/seo/breadcrumbs.js - Breadcrumb path generation
 * - lib/seo/schemas.js - BreadcrumbList schema generation
 *
 * @example
 * import { Breadcrumbs } from '@/components/seo/Breadcrumbs';
 * import { getGlossaryBreadcrumbs } from '@/lib/seo';
 *
 * <Breadcrumbs items={getGlossaryBreadcrumbs(term)} />
 */

import Link from "next/link";
import { ChevronRight, Home } from "lucide-react";
import { JsonLd } from "./JsonLd";
import { generateBreadcrumbSchema } from "@/lib/seo/schemas";

/**
 * Breadcrumb navigation with schema markup.
 *
 * @param {Object} props - Component props
 * @param {Array<{name: string, href: string, url?: string}>} props.items - Breadcrumb items
 * @param {string} [props.className] - Additional CSS classes
 * @param {boolean} [props.showSchema=true] - Whether to include JSON-LD schema
 * @param {boolean} [props.showHome=true] - Whether to show home icon
 * @returns {JSX.Element} Breadcrumb navigation
 */
export function Breadcrumbs({
  items,
  className = "",
  showSchema = true,
  showHome = true,
}) {
  if (!items || items.length === 0) return null;

  // Prepare items with URLs for schema
  const schemaItems = items.map((item) => ({
    name: item.name,
    url: item.url || `https://www.metricx.ai${item.href}`,
  }));

  return (
    <>
      {/* JSON-LD Structured Data */}
      {showSchema && <JsonLd schema={generateBreadcrumbSchema(schemaItems)} />}

      {/* Visual Breadcrumb Navigation */}
      <nav
        aria-label="Breadcrumb"
        className={`flex items-center text-sm text-gray-400 mb-6 ${className}`}
      >
        <ol
          className="flex items-center flex-wrap gap-1"
          itemScope
          itemType="https://schema.org/BreadcrumbList"
        >
          {items.map((item, index) => {
            const isLast = index === items.length - 1;
            const isFirst = index === 0;

            return (
              <li
                key={item.href}
                className="flex items-center"
                itemProp="itemListElement"
                itemScope
                itemType="https://schema.org/ListItem"
              >
                {/* Separator (except for first item) */}
                {!isFirst && (
                  <ChevronRight
                    className="w-4 h-4 mx-1 text-gray-300 flex-shrink-0"
                    aria-hidden="true"
                  />
                )}

                {/* Breadcrumb Link or Text */}
                {isLast ? (
                  // Current page - not a link
                  <span
                    className="text-gray-900 font-medium truncate max-w-[200px]"
                    itemProp="name"
                    aria-current="page"
                  >
                    {item.name}
                  </span>
                ) : (
                  // Link to ancestor page
                  <Link
                    href={item.href}
                    className="hover:text-gray-900 transition-colors flex items-center"
                    itemProp="item"
                  >
                    {isFirst && showHome ? (
                      <>
                        <Home className="w-4 h-4" aria-hidden="true" />
                        <span className="sr-only" itemProp="name">
                          {item.name}
                        </span>
                      </>
                    ) : (
                      <span itemProp="name">{item.name}</span>
                    )}
                  </Link>
                )}

                {/* Hidden position for schema */}
                <meta itemProp="position" content={String(index + 1)} />
              </li>
            );
          })}
        </ol>
      </nav>
    </>
  );
}

/**
 * Compact breadcrumb for mobile/small spaces.
 *
 * @param {Object} props - Component props
 * @param {Array} props.items - Breadcrumb items
 * @returns {JSX.Element} Compact breadcrumb
 */
export function CompactBreadcrumbs({ items }) {
  if (!items || items.length < 2) return null;

  // Only show parent and current
  const parent = items[items.length - 2];

  return (
    <nav aria-label="Breadcrumb" className="flex items-center text-sm">
      <Link
        href={parent.href}
        className="text-gray-400 hover:text-gray-900 flex items-center"
      >
        <ChevronRight className="w-4 h-4 rotate-180 mr-1" />
        {parent.name}
      </Link>
    </nav>
  );
}

export default Breadcrumbs;
