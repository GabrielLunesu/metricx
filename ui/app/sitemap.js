/**
 * Dynamic Sitemap Generator for metricx
 *
 * WHAT: Generates sitemap.xml for search engines including all blog posts
 * WHY: Helps search engines discover and index public pages
 *
 * Next.js automatically serves this at /sitemap.xml
 *
 * @see https://nextjs.org/docs/app/api-reference/file-conventions/metadata/sitemap
 */

import { getAllPosts } from "@/lib/blog";

const baseUrl = "https://www.metricx.ai";

/**
 * Generates sitemap entries for all public pages and blog posts.
 *
 * @returns {Array<{url: string, lastModified: Date, changeFrequency: string, priority: number}>}
 */
export default function sitemap() {
  const now = new Date();

  const staticPages = [
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

  const blogPosts = getAllPosts().map((post) => ({
    url: `${baseUrl}/blog/${post.slug}`,
    lastModified: new Date(post.updatedAt ?? post.publishedAt),
    changeFrequency: "monthly",
    priority: 0.7,
  }));

  return [...staticPages, ...blogPosts];
}
