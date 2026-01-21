/**
 * Breadcrumb Path Generation Utilities
 *
 * WHAT: Generates breadcrumb navigation paths for SEO pages
 * WHY: Breadcrumbs improve navigation UX and provide structured data
 *      for search engines to understand site hierarchy
 *
 * Related files:
 * - lib/seo/schemas.js - BreadcrumbList schema generation
 * - components/seo/Breadcrumbs.jsx - Breadcrumb rendering component
 */

const BASE_URL = "https://www.metricx.ai";

/**
 * Route configuration for breadcrumb generation.
 * Maps route segments to display names.
 */
const ROUTE_LABELS = {
  glossary: "Glossary",
  blog: "Blog",
  vs: "Comparisons",
  alternatives: "Alternatives",
  metrics: "Metrics",
  platforms: "Platforms",
  industries: "Industries",
  integrations: "Integrations",
  tools: "Tools",
  "use-cases": "Use Cases",
};

/**
 * Category display names for blog and other categorized content.
 */
const CATEGORY_LABELS = {
  // Blog categories
  "roas-optimization": "ROAS Optimization",
  "meta-ads": "Meta Ads",
  "google-ads": "Google Ads",
  "analytics": "Analytics",
  "attribution": "Attribution",
  "ecommerce": "E-commerce",
  "strategy": "Strategy",
  "tutorials": "Tutorials",
};

/**
 * Generate breadcrumb items from a URL path.
 *
 * WHAT: Creates an array of breadcrumb items from a path
 * WHY: Automatically generates breadcrumb hierarchy from URL structure
 *
 * @param {string} path - The URL path (e.g., "/glossary/roas")
 * @param {Object} [options] - Configuration options
 * @param {string} [options.currentTitle] - Custom title for current page
 * @returns {Array<{name: string, href: string, url: string}>} Breadcrumb items
 *
 * @example
 * getBreadcrumbPath("/glossary/roas", { currentTitle: "ROAS" })
 * // Returns:
 * // [
 * //   { name: "Home", href: "/", url: "https://www.metricx.ai" },
 * //   { name: "Glossary", href: "/glossary", url: "https://www.metricx.ai/glossary" },
 * //   { name: "ROAS", href: "/glossary/roas", url: "https://www.metricx.ai/glossary/roas" }
 * // ]
 */
export function getBreadcrumbPath(path, { currentTitle } = {}) {
  // Start with home
  const breadcrumbs = [
    { name: "Home", href: "/", url: BASE_URL },
  ];

  // Skip if we're on the homepage
  if (path === "/" || path === "") {
    return breadcrumbs;
  }

  // Split path into segments
  const segments = path.split("/").filter(Boolean);

  // Build breadcrumb trail
  let currentPath = "";

  segments.forEach((segment, index) => {
    currentPath += `/${segment}`;
    const isLast = index === segments.length - 1;

    // Determine the display name
    let name;
    if (isLast && currentTitle) {
      // Use custom title for current page if provided
      name = currentTitle;
    } else if (ROUTE_LABELS[segment]) {
      // Use route label if available
      name = ROUTE_LABELS[segment];
    } else if (CATEGORY_LABELS[segment]) {
      // Use category label if available
      name = CATEGORY_LABELS[segment];
    } else {
      // Convert slug to title case
      name = slugToTitle(segment);
    }

    breadcrumbs.push({
      name,
      href: currentPath,
      url: `${BASE_URL}${currentPath}`,
    });
  });

  return breadcrumbs;
}

/**
 * Convert a URL slug to title case.
 *
 * WHAT: Transforms slugs like "roas-calculator" to "ROAS Calculator"
 * WHY: Provides readable display names from URL segments
 *
 * @param {string} slug - URL slug
 * @returns {string} Title-cased string
 */
export function slugToTitle(slug) {
  // Handle common acronyms
  const acronyms = ["roas", "cpc", "cpm", "ctr", "cpa", "cac", "ltv", "aov", "roi", "kpi", "api", "ai", "seo"];

  return slug
    .split("-")
    .map((word) => {
      const lower = word.toLowerCase();
      if (acronyms.includes(lower)) {
        return word.toUpperCase();
      }
      return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
    })
    .join(" ");
}

/**
 * Generate breadcrumbs for glossary term pages.
 *
 * WHAT: Creates breadcrumb path for glossary terms
 * WHY: Consistent breadcrumb structure for all glossary pages
 *
 * @param {Object} term - Term data
 * @param {string} term.term - Display term
 * @param {string} term.slug - URL slug
 * @returns {Array} Breadcrumb items
 */
export function getGlossaryBreadcrumbs(term) {
  return getBreadcrumbPath(`/glossary/${term.slug}`, {
    currentTitle: term.term,
  });
}

/**
 * Generate breadcrumbs for comparison pages.
 *
 * WHAT: Creates breadcrumb path for vs/comparison pages
 * WHY: Consistent breadcrumb structure for competitor comparisons
 *
 * @param {Object} competitor - Competitor data
 * @param {string} competitor.name - Competitor name
 * @param {string} competitor.slug - URL slug
 * @returns {Array} Breadcrumb items
 */
export function getComparisonBreadcrumbs(competitor) {
  return getBreadcrumbPath(`/vs/${competitor.slug}`, {
    currentTitle: `metricx vs ${competitor.name}`,
  });
}

/**
 * Generate breadcrumbs for alternative pages.
 *
 * WHAT: Creates breadcrumb path for alternative-to pages
 * WHY: Consistent breadcrumb structure for alternative pages
 *
 * @param {Object} competitor - Competitor data
 * @returns {Array} Breadcrumb items
 */
export function getAlternativeBreadcrumbs(competitor) {
  return getBreadcrumbPath(`/alternatives/${competitor.slug}`, {
    currentTitle: `${competitor.name} Alternative`,
  });
}

/**
 * Generate breadcrumbs for blog posts.
 *
 * WHAT: Creates breadcrumb path for blog articles
 * WHY: Shows blog > category > post hierarchy
 *
 * @param {Object} post - Blog post data
 * @param {string} post.title - Post title
 * @param {string} post.category - Post category slug
 * @param {string} post.slug - Post slug
 * @returns {Array} Breadcrumb items
 */
export function getBlogBreadcrumbs(post) {
  return getBreadcrumbPath(`/blog/${post.category}/${post.slug}`, {
    currentTitle: post.title,
  });
}

/**
 * Generate breadcrumbs for metric pages.
 *
 * WHAT: Creates breadcrumb path for metric deep-dive pages
 * WHY: Consistent breadcrumb structure for metrics section
 *
 * @param {Object} metric - Metric data
 * @param {string} metric.name - Metric name
 * @param {string} metric.slug - URL slug
 * @returns {Array} Breadcrumb items
 */
export function getMetricBreadcrumbs(metric) {
  return getBreadcrumbPath(`/metrics/${metric.slug}`, {
    currentTitle: metric.name,
  });
}

/**
 * Generate breadcrumbs for platform pages.
 *
 * WHAT: Creates breadcrumb path for platform guide pages
 * WHY: Consistent breadcrumb structure for platforms section
 *
 * @param {Object} platform - Platform data
 * @param {string} platform.name - Platform name
 * @param {string} platform.slug - URL slug
 * @returns {Array} Breadcrumb items
 */
export function getPlatformBreadcrumbs(platform) {
  return getBreadcrumbPath(`/platforms/${platform.slug}`, {
    currentTitle: platform.name,
  });
}

/**
 * Generate breadcrumbs for industry pages.
 *
 * WHAT: Creates breadcrumb path for industry landing pages
 * WHY: Consistent breadcrumb structure for industries section
 *
 * @param {Object} industry - Industry data
 * @param {string} industry.name - Industry name
 * @param {string} industry.slug - URL slug
 * @returns {Array} Breadcrumb items
 */
export function getIndustryBreadcrumbs(industry) {
  return getBreadcrumbPath(`/industries/${industry.slug}`, {
    currentTitle: industry.name,
  });
}

/**
 * Generate breadcrumbs for tool pages.
 *
 * WHAT: Creates breadcrumb path for calculator/tool pages
 * WHY: Consistent breadcrumb structure for tools section
 *
 * @param {Object} tool - Tool data
 * @param {string} tool.name - Tool name
 * @param {string} tool.slug - URL slug
 * @returns {Array} Breadcrumb items
 */
export function getToolBreadcrumbs(tool) {
  return getBreadcrumbPath(`/tools/${tool.slug}`, {
    currentTitle: tool.name,
  });
}

/**
 * Generate breadcrumbs for integration pages.
 *
 * WHAT: Creates breadcrumb path for integration pages
 * WHY: Consistent breadcrumb structure for integrations section
 *
 * @param {Object} integration - Integration data
 * @param {string} integration.name - Integration name
 * @param {string} integration.slug - URL slug
 * @returns {Array} Breadcrumb items
 */
export function getIntegrationBreadcrumbs(integration) {
  return getBreadcrumbPath(`/integrations/${integration.slug}`, {
    currentTitle: integration.name,
  });
}

/**
 * Generate breadcrumbs for use case pages.
 *
 * WHAT: Creates breadcrumb path for use case pages
 * WHY: Consistent breadcrumb structure for use-cases section
 *
 * @param {Object} useCase - Use case data
 * @param {string} useCase.name - Use case name
 * @param {string} useCase.slug - URL slug
 * @returns {Array} Breadcrumb items
 */
export function getUseCaseBreadcrumbs(useCase) {
  return getBreadcrumbPath(`/use-cases/${useCase.slug}`, {
    currentTitle: useCase.name,
  });
}
