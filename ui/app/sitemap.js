/**
 * Dynamic Sitemap Generator for metricx
 *
 * This file generates a sitemap.xml that helps search engines discover and index
 * the public pages of the metricx website.
 *
 * Next.js automatically serves this at /sitemap.xml
 *
 * Note: Only public pages are included. Dashboard and authenticated routes
 * are excluded as they require login and shouldn't be indexed.
 *
 * @see https://nextjs.org/docs/app/api-reference/file-conventions/metadata/sitemap
 */

/**
 * Generates the sitemap entries for all public pages.
 *
 * @returns {Array<{url: string, lastModified: Date, changeFrequency: string, priority: number}>}
 *   Array of sitemap entries with URL, last modified date, change frequency, and priority.
 */
export default function sitemap() {
  const baseUrl = "https://www.metricx.ai";

  // Define all public (non-authenticated) routes
  // These are the only pages that should be indexed by search engines
  const publicRoutes = [
    // Homepage - highest priority
    {
      url: baseUrl,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 1.0,
    },
    // Authentication pages
    {
      url: `${baseUrl}/login`,
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 0.5,
    },
    // Legal pages
    {
      url: `${baseUrl}/privacy`,
      lastModified: new Date(),
      changeFrequency: "yearly",
      priority: 0.3,
    },
    {
      url: `${baseUrl}/terms`,
      lastModified: new Date(),
      changeFrequency: "yearly",
      priority: 0.3,
    },
  ];

  return publicRoutes;
}
