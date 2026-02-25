/**
 * Dynamic Sitemap Generator for metricx
 *
 * WHAT: Generates sitemap.xml for search engines
 * WHY: Helps search engines discover and index public pages
 *
 * Next.js automatically serves this at /sitemap.xml
 *
 * @see https://nextjs.org/docs/app/api-reference/file-conventions/metadata/sitemap
 */

const baseUrl = "https://www.metricx.ai";

/**
 * Generates sitemap entries for all public pages.
 *
 * @returns {Array<{url: string, lastModified: Date, changeFrequency: string, priority: number}>}
 */
export default function sitemap() {
  const now = new Date();

  return [
    {
      url: baseUrl,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 1.0,
    },
    {
      url: `${baseUrl}/sign-in`,
      lastModified: now,
      changeFrequency: "monthly",
      priority: 0.5,
    },
    {
      url: `${baseUrl}/sign-up`,
      lastModified: now,
      changeFrequency: "monthly",
      priority: 0.6,
    },
    {
      url: `${baseUrl}/privacy`,
      lastModified: now,
      changeFrequency: "yearly",
      priority: 0.3,
    },
    {
      url: `${baseUrl}/terms`,
      lastModified: now,
      changeFrequency: "yearly",
      priority: 0.3,
    },
    {
      url: `${baseUrl}/blog`,
      lastModified: now,
      changeFrequency: "daily",
      priority: 0.9,
    },
  ];
}
