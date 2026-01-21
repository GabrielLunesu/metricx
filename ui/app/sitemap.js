/**
 * Dynamic Sitemap Generator for metricx
 *
 * WHAT: Generates sitemap.xml for search engines
 * WHY: SEO - helps search engines discover and index all programmatic pages
 *
 * Next.js automatically serves this at /sitemap.xml
 *
 * Related files:
 * - lib/seo/content-loader.js - Content data loading
 * - content/ - JSON data files for programmatic pages
 *
 * @see https://nextjs.org/docs/app/api-reference/file-conventions/metadata/sitemap
 */

import {
  getGlossaryTerms,
  getCompetitors,
  getMetrics,
  getPlatforms,
  getIndustries,
  getIntegrations,
  getUseCases,
  getBlogCategories,
} from "@/lib/seo/content-loader";
import { allCalculators } from "@/components/tools";

const baseUrl = "https://www.metricx.ai";

/**
 * Generates the sitemap entries for all public pages.
 *
 * @returns {Promise<Array<{url: string, lastModified: Date, changeFrequency: string, priority: number}>>}
 */
export default async function sitemap() {
  const now = new Date();

  // Load all content data
  const [
    glossaryTerms,
    competitors,
    metrics,
    platforms,
    industries,
    integrations,
    useCases,
    blogCategories,
  ] = await Promise.all([
    getGlossaryTerms(),
    getCompetitors(),
    getMetrics(),
    getPlatforms(),
    getIndustries(),
    getIntegrations(),
    getUseCases(),
    getBlogCategories(),
  ]);

  // Static pages
  const staticPages = [
    // Homepage - highest priority
    {
      url: baseUrl,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 1.0,
    },
    // Authentication pages
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
    // Legal pages
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
  ];

  // Hub pages (high priority)
  const hubPages = [
    {
      url: `${baseUrl}/glossary`,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 0.9,
    },
    {
      url: `${baseUrl}/vs`,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 0.9,
    },
    {
      url: `${baseUrl}/alternatives`,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 0.8,
    },
    {
      url: `${baseUrl}/tools`,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 0.9,
    },
    {
      url: `${baseUrl}/metrics`,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 0.8,
    },
    {
      url: `${baseUrl}/platforms`,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 0.8,
    },
    {
      url: `${baseUrl}/industries`,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 0.8,
    },
    {
      url: `${baseUrl}/integrations`,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 0.8,
    },
    {
      url: `${baseUrl}/use-cases`,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 0.8,
    },
    {
      url: `${baseUrl}/blog`,
      lastModified: now,
      changeFrequency: "daily",
      priority: 0.9,
    },
  ];

  // Glossary term pages
  const glossaryPages = glossaryTerms.map((term) => ({
    url: `${baseUrl}/glossary/${term.slug}`,
    lastModified: now,
    changeFrequency: "monthly",
    priority: 0.7,
  }));

  // Comparison pages (vs)
  const comparisonPages = competitors.map((competitor) => ({
    url: `${baseUrl}/vs/${competitor.slug}`,
    lastModified: now,
    changeFrequency: "monthly",
    priority: 0.8,
  }));

  // Alternative pages
  const alternativePages = competitors.map((competitor) => ({
    url: `${baseUrl}/alternatives/${competitor.slug}`,
    lastModified: now,
    changeFrequency: "monthly",
    priority: 0.8,
  }));

  // Calculator tool pages
  const toolPages = allCalculators.map((calculator) => ({
    url: `${baseUrl}/tools/${calculator.slug}`,
    lastModified: now,
    changeFrequency: "monthly",
    priority: 0.8,
  }));

  // Metric pages
  const metricPages = metrics.map((metric) => ({
    url: `${baseUrl}/metrics/${metric.slug}`,
    lastModified: now,
    changeFrequency: "monthly",
    priority: 0.7,
  }));

  // Platform pages
  const platformPages = platforms.map((platform) => ({
    url: `${baseUrl}/platforms/${platform.slug}`,
    lastModified: now,
    changeFrequency: "monthly",
    priority: 0.7,
  }));

  // Industry pages
  const industryPages = industries.map((industry) => ({
    url: `${baseUrl}/industries/${industry.slug}`,
    lastModified: now,
    changeFrequency: "monthly",
    priority: 0.7,
  }));

  // Integration pages
  const integrationPages = integrations.map((integration) => ({
    url: `${baseUrl}/integrations/${integration.slug}`,
    lastModified: now,
    changeFrequency: "monthly",
    priority: 0.7,
  }));

  // Use case pages
  const useCasePages = useCases.map((useCase) => ({
    url: `${baseUrl}/use-cases/${useCase.slug}`,
    lastModified: now,
    changeFrequency: "monthly",
    priority: 0.7,
  }));

  // Blog category pages
  const blogCategoryPages = blogCategories.map((category) => ({
    url: `${baseUrl}/blog/${category.slug}`,
    lastModified: now,
    changeFrequency: "weekly",
    priority: 0.7,
  }));

  // Industry × Metric combination pages (2,160+ pages)
  const industryMetricPages = [];
  for (const industry of industries) {
    for (const metric of metrics) {
      industryMetricPages.push({
        url: `${baseUrl}/industries/${industry.slug}/${metric.slug}`,
        lastModified: now,
        changeFrequency: "monthly",
        priority: 0.6,
      });
    }
  }

  // Platform × Metric combination pages (160+ pages)
  const platformMetricPages = [];
  for (const platform of platforms) {
    for (const metric of metrics) {
      platformMetricPages.push({
        url: `${baseUrl}/platforms/${platform.slug}/${metric.slug}`,
        lastModified: now,
        changeFrequency: "monthly",
        priority: 0.6,
      });
    }
  }

  // Use Case × Industry combination pages (10,260+ pages)
  const useCaseIndustryPages = [];
  for (const useCase of useCases) {
    for (const industry of industries) {
      useCaseIndustryPages.push({
        url: `${baseUrl}/use-cases/${useCase.slug}/${industry.slug}`,
        lastModified: now,
        changeFrequency: "monthly",
        priority: 0.5,
      });
    }
  }

  // Integration × Industry combination pages (1,296+ pages)
  const integrationIndustryPages = [];
  for (const integration of integrations) {
    for (const industry of industries) {
      integrationIndustryPages.push({
        url: `${baseUrl}/integrations/${integration.slug}/${industry.slug}`,
        lastModified: now,
        changeFrequency: "monthly",
        priority: 0.5,
      });
    }
  }

  // Industry × Platform combination pages (864+ pages)
  const industryPlatformPages = [];
  for (const industry of industries) {
    for (const platform of platforms) {
      industryPlatformPages.push({
        url: `${baseUrl}/industries/${industry.slug}/platforms/${platform.slug}`,
        lastModified: now,
        changeFrequency: "monthly",
        priority: 0.5,
      });
    }
  }

  // Combine all pages
  const allPages = [
    ...staticPages,
    ...hubPages,
    ...glossaryPages,
    ...comparisonPages,
    ...alternativePages,
    ...toolPages,
    ...metricPages,
    ...platformPages,
    ...industryPages,
    ...integrationPages,
    ...useCasePages,
    ...blogCategoryPages,
    ...industryMetricPages,
    ...platformMetricPages,
    ...useCaseIndustryPages,
    ...integrationIndustryPages,
    ...industryPlatformPages,
  ];

  console.log(`Sitemap generated with ${allPages.length} URLs`);

  return allPages;
}
