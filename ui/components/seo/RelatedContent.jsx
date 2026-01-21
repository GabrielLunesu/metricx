/**
 * Related Content Component
 *
 * WHAT: Displays related pages for internal linking
 * WHY: Strong internal linking improves crawlability, distributes page
 *      authority, and keeps users engaged with relevant content
 *
 * Related files:
 * - lib/seo/internal-links.js - Related content utilities
 *
 * @example
 * import { RelatedContent } from '@/components/seo/RelatedContent';
 *
 * <RelatedContent
 *   title="Related Terms"
 *   items={relatedTerms}
 *   basePath="/glossary"
 * />
 */

import Link from "next/link";
import { ArrowRight, ExternalLink } from "lucide-react";

/**
 * Grid of related content cards.
 *
 * @param {Object} props - Component props
 * @param {string} [props.title] - Section title
 * @param {Array<{name: string, slug: string, description?: string, href?: string}>} props.items - Related items
 * @param {string} [props.basePath] - Base path for links (e.g., "/glossary")
 * @param {string} [props.className] - Additional CSS classes
 * @param {number} [props.columns=3] - Number of columns (2, 3, or 4)
 * @param {boolean} [props.showDescription=true] - Show item descriptions
 * @returns {JSX.Element} Related content grid
 */
export function RelatedContent({
  title = "Related Content",
  items,
  basePath = "",
  className = "",
  columns = 3,
  showDescription = true,
}) {
  if (!items || items.length === 0) return null;

  const gridCols = {
    2: "grid-cols-1 sm:grid-cols-2",
    3: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3",
    4: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-4",
  };

  return (
    <section className={`related-content ${className}`}>
      {title && (
        <h2 className="text-xl font-bold text-slate-900 mb-4">{title}</h2>
      )}

      <div className={`grid ${gridCols[columns] || gridCols[3]} gap-4`}>
        {items.map((item) => {
          const href = item.href || `${basePath}/${item.slug}`;

          return (
            <Link
              key={item.slug || item.name}
              href={href}
              className="group p-4 bg-white border border-slate-200 rounded-lg hover:border-cyan-300 hover:shadow-sm transition-all"
            >
              <h3 className="font-semibold text-slate-900 group-hover:text-cyan-600 transition-colors flex items-center justify-between">
                {item.name || item.term || item.title}
                <ArrowRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" />
              </h3>
              {showDescription && item.description && (
                <p className="mt-1 text-sm text-slate-500 line-clamp-2">
                  {item.description}
                </p>
              )}
            </Link>
          );
        })}
      </div>
    </section>
  );
}

/**
 * Compact related links list.
 *
 * @param {Object} props - Component props
 * @param {string} [props.title] - Section title
 * @param {Array} props.items - Related items
 * @param {string} [props.basePath] - Base path for links
 * @returns {JSX.Element} Compact link list
 */
export function RelatedLinks({ title = "See Also", items, basePath = "" }) {
  if (!items || items.length === 0) return null;

  return (
    <div className="related-links">
      {title && (
        <h3 className="text-sm font-semibold text-slate-700 mb-2">{title}</h3>
      )}
      <ul className="flex flex-wrap gap-2">
        {items.map((item) => {
          const href = item.href || `${basePath}/${item.slug}`;

          return (
            <li key={item.slug || item.name}>
              <Link
                href={href}
                className="inline-flex items-center px-3 py-1 text-sm bg-slate-100 text-slate-700 rounded-full hover:bg-cyan-100 hover:text-cyan-700 transition-colors"
              >
                {item.name || item.term || item.title}
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/**
 * Related content sidebar.
 *
 * @param {Object} props - Component props
 * @param {string} [props.title] - Sidebar title
 * @param {Array} props.items - Related items
 * @param {string} [props.basePath] - Base path for links
 * @returns {JSX.Element} Sidebar list
 */
export function RelatedSidebar({ title = "Related", items, basePath = "" }) {
  if (!items || items.length === 0) return null;

  return (
    <aside className="related-sidebar">
      {title && (
        <h3 className="font-semibold text-slate-900 mb-3">{title}</h3>
      )}
      <ul className="space-y-2">
        {items.map((item) => {
          const href = item.href || `${basePath}/${item.slug}`;

          return (
            <li key={item.slug || item.name}>
              <Link
                href={href}
                className="block text-slate-600 hover:text-cyan-600 transition-colors"
              >
                {item.name || item.term || item.title}
              </Link>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}

/**
 * Featured content cards with larger display.
 *
 * @param {Object} props - Component props
 * @param {string} [props.title] - Section title
 * @param {Array} props.items - Featured items with extended data
 * @param {string} [props.basePath] - Base path for links
 * @returns {JSX.Element} Featured content cards
 */
export function FeaturedContent({ title, items, basePath = "" }) {
  if (!items || items.length === 0) return null;

  return (
    <section className="featured-content">
      {title && (
        <h2 className="text-2xl font-bold text-slate-900 mb-6">{title}</h2>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {items.map((item) => {
          const href = item.href || `${basePath}/${item.slug}`;

          return (
            <Link
              key={item.slug || item.name}
              href={href}
              className="group block p-6 bg-gradient-to-br from-slate-50 to-white border border-slate-200 rounded-xl hover:border-cyan-300 hover:shadow-md transition-all"
            >
              {item.icon && (
                <div className="w-10 h-10 bg-cyan-100 rounded-lg flex items-center justify-center mb-4 group-hover:bg-cyan-200 transition-colors">
                  <item.icon className="w-5 h-5 text-cyan-600" />
                </div>
              )}
              <h3 className="text-lg font-semibold text-slate-900 group-hover:text-cyan-600 transition-colors">
                {item.name || item.title}
              </h3>
              {item.description && (
                <p className="mt-2 text-slate-600 text-sm">
                  {item.description}
                </p>
              )}
            </Link>
          );
        })}
      </div>
    </section>
  );
}

export default RelatedContent;
