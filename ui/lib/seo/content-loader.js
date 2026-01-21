/**
 * Content Loading Utilities
 *
 * WHAT: Loads and manages JSON content data for programmatic SEO pages
 * WHY: Centralizes content access for consistent data handling across
 *      all programmatic page templates
 *
 * Related files:
 * - content/glossary/terms.json - Glossary term definitions
 * - content/competitors/data.json - Competitor comparison data
 * - content/metrics/data.json - Metric definitions
 * - content/platforms/data.json - Platform data
 * - content/industries/data.json - Industry data
 * - content/integrations/data.json - Integration data
 */

import { cache } from "react";

/**
 * In-memory cache for content data.
 * Uses React cache() for request deduplication in Server Components.
 */

/**
 * Load glossary terms from JSON.
 *
 * WHAT: Fetches all glossary terms from the content file
 * WHY: Provides term data for glossary pages and cross-referencing
 *
 * @returns {Promise<Array>} Array of glossary term objects
 *
 * @example
 * const terms = await getGlossaryTerms();
 * // [{ term: "ROAS", fullName: "Return on Ad Spend", slug: "roas", ... }]
 */
export const getGlossaryTerms = cache(async () => {
  try {
    const data = await import("@/content/glossary/terms.json");
    // Convert object to array if needed
    if (Array.isArray(data.default)) {
      return data.default;
    }
    return Object.values(data.default);
  } catch (error) {
    console.error("Failed to load glossary terms:", error);
    return [];
  }
});

/**
 * Get a single glossary term by slug.
 *
 * WHAT: Fetches a specific glossary term
 * WHY: Used by individual term pages to get term data
 *
 * @param {string} slug - Term slug
 * @returns {Promise<Object|null>} Term object or null if not found
 */
export const getGlossaryTerm = cache(async (slug) => {
  const terms = await getGlossaryTerms();
  return terms.find((term) => term.slug === slug) || null;
});

/**
 * Get glossary terms grouped by first letter.
 *
 * WHAT: Groups terms alphabetically for A-Z index
 * WHY: Used by glossary hub page for alphabetical navigation
 *
 * @returns {Promise<Object>} Terms grouped by letter
 */
export const getGlossaryTermsByLetter = cache(async () => {
  const terms = await getGlossaryTerms();
  const grouped = {};

  terms.forEach((term) => {
    const letter = term.term.charAt(0).toUpperCase();
    if (!grouped[letter]) {
      grouped[letter] = [];
    }
    grouped[letter].push(term);
  });

  // Sort each group
  Object.keys(grouped).forEach((letter) => {
    grouped[letter].sort((a, b) => a.term.localeCompare(b.term));
  });

  return grouped;
});

/**
 * Get glossary terms grouped by category.
 *
 * WHAT: Groups all terms by their category
 * WHY: Enables category-based filtering and navigation
 *
 * @returns {Promise<Object>} Terms grouped by category
 */
export const getGlossaryTermsGroupedByCategory = cache(async () => {
  const terms = await getGlossaryTerms();
  const grouped = {};

  terms.forEach((term) => {
    const category = term.category || "other";
    if (!grouped[category]) {
      grouped[category] = [];
    }
    grouped[category].push(term);
  });

  return grouped;
});

/**
 * Get glossary terms for a specific category.
 *
 * WHAT: Returns terms filtered by a specific category
 * WHY: Used by term pages to show related terms in same category
 *
 * @param {string} category - Category to filter by
 * @returns {Promise<Array>} Array of terms in the category
 */
export const getGlossaryTermsByCategory = cache(async (category) => {
  const terms = await getGlossaryTerms();
  return terms.filter((term) => (term.category || "other") === category);
});

/**
 * Load competitor data from JSON.
 *
 * WHAT: Fetches competitor comparison data
 * WHY: Provides data for vs/ and alternatives/ pages
 *
 * @returns {Promise<Array>} Array of competitor objects
 */
export const getCompetitors = cache(async () => {
  try {
    const data = await import("@/content/competitors/data.json");
    if (Array.isArray(data.default)) {
      return data.default;
    }
    return Object.values(data.default);
  } catch (error) {
    console.error("Failed to load competitors:", error);
    return [];
  }
});

/**
 * Get a single competitor by slug.
 *
 * @param {string} slug - Competitor slug
 * @returns {Promise<Object|null>} Competitor object or null
 */
export const getCompetitor = cache(async (slug) => {
  const competitors = await getCompetitors();
  return competitors.find((c) => c.slug === slug) || null;
});

/**
 * Load metrics data from JSON.
 *
 * WHAT: Fetches metric definitions and data
 * WHY: Provides data for metrics deep-dive pages
 *
 * @returns {Promise<Array>} Array of metric objects
 */
export const getMetrics = cache(async () => {
  try {
    const data = await import("@/content/metrics/data.json");
    if (Array.isArray(data.default)) {
      return data.default;
    }
    return Object.values(data.default);
  } catch (error) {
    console.error("Failed to load metrics:", error);
    return [];
  }
});

/**
 * Get a single metric by slug.
 *
 * @param {string} slug - Metric slug
 * @returns {Promise<Object|null>} Metric object or null
 */
export const getMetric = cache(async (slug) => {
  const metrics = await getMetrics();
  return metrics.find((m) => m.slug === slug) || null;
});

/**
 * Load platform data from JSON.
 *
 * WHAT: Fetches ad platform data
 * WHY: Provides data for platform guide pages
 *
 * @returns {Promise<Array>} Array of platform objects
 */
export const getPlatforms = cache(async () => {
  try {
    const data = await import("@/content/platforms/data.json");
    if (Array.isArray(data.default)) {
      return data.default;
    }
    return Object.values(data.default);
  } catch (error) {
    console.error("Failed to load platforms:", error);
    return [];
  }
});

/**
 * Get a single platform by slug.
 *
 * @param {string} slug - Platform slug
 * @returns {Promise<Object|null>} Platform object or null
 */
export const getPlatform = cache(async (slug) => {
  const platforms = await getPlatforms();
  return platforms.find((p) => p.slug === slug) || null;
});

/**
 * Load industry data from JSON.
 *
 * WHAT: Fetches industry-specific data
 * WHY: Provides data for industry landing pages
 *
 * @returns {Promise<Array>} Array of industry objects
 */
export const getIndustries = cache(async () => {
  try {
    const data = await import("@/content/industries/data.json");
    if (Array.isArray(data.default)) {
      return data.default;
    }
    return Object.values(data.default);
  } catch (error) {
    console.error("Failed to load industries:", error);
    return [];
  }
});

/**
 * Get a single industry by slug.
 *
 * @param {string} slug - Industry slug
 * @returns {Promise<Object|null>} Industry object or null
 */
export const getIndustry = cache(async (slug) => {
  const industries = await getIndustries();
  return industries.find((i) => i.slug === slug) || null;
});

/**
 * Load integration data from JSON.
 *
 * WHAT: Fetches integration data
 * WHY: Provides data for integration pages
 *
 * @returns {Promise<Array>} Array of integration objects
 */
export const getIntegrations = cache(async () => {
  try {
    const data = await import("@/content/integrations/data.json");
    if (Array.isArray(data.default)) {
      return data.default;
    }
    return Object.values(data.default);
  } catch (error) {
    console.error("Failed to load integrations:", error);
    return [];
  }
});

/**
 * Get a single integration by slug.
 *
 * @param {string} slug - Integration slug
 * @returns {Promise<Object|null>} Integration object or null
 */
export const getIntegration = cache(async (slug) => {
  const integrations = await getIntegrations();
  return integrations.find((i) => i.slug === slug) || null;
});

/**
 * Load use case data from JSON.
 *
 * WHAT: Fetches use case scenarios
 * WHY: Provides data for use case pages
 *
 * @returns {Promise<Array>} Array of use case objects
 */
export const getUseCases = cache(async () => {
  try {
    const data = await import("@/content/use-cases/data.json");
    if (Array.isArray(data.default)) {
      return data.default;
    }
    return Object.values(data.default);
  } catch (error) {
    console.error("Failed to load use cases:", error);
    return [];
  }
});

/**
 * Get a single use case by slug.
 *
 * @param {string} slug - Use case slug
 * @returns {Promise<Object|null>} Use case object or null
 */
export const getUseCase = cache(async (slug) => {
  const useCases = await getUseCases();
  return useCases.find((u) => u.slug === slug) || null;
});

/**
 * Load calculator/tool configurations from JSON.
 *
 * WHAT: Fetches calculator configurations
 * WHY: Provides data for tool pages
 *
 * @returns {Promise<Array>} Array of tool objects
 */
export const getTools = cache(async () => {
  try {
    const data = await import("@/content/tools/calculators.json");
    if (Array.isArray(data.default)) {
      return data.default;
    }
    return Object.values(data.default);
  } catch (error) {
    console.error("Failed to load tools:", error);
    return [];
  }
});

/**
 * Get a single tool by slug.
 *
 * @param {string} slug - Tool slug
 * @returns {Promise<Object|null>} Tool object or null
 */
export const getTool = cache(async (slug) => {
  const tools = await getTools();
  return tools.find((t) => t.slug === slug) || null;
});

/**
 * Load blog categories from JSON.
 *
 * WHAT: Fetches blog category definitions
 * WHY: Provides data for blog navigation and category pages
 *
 * @returns {Promise<Array>} Array of category objects
 */
export const getBlogCategories = cache(async () => {
  try {
    const data = await import("@/content/blog/categories.json");
    if (Array.isArray(data.default)) {
      return data.default;
    }
    return Object.values(data.default);
  } catch (error) {
    console.error("Failed to load blog categories:", error);
    return [];
  }
});

/**
 * Load author data from JSON.
 *
 * WHAT: Fetches author profiles for E-E-A-T
 * WHY: Provides author data for blog posts and content attribution
 *
 * @returns {Promise<Array>} Array of author objects
 */
export const getAuthors = cache(async () => {
  try {
    const data = await import("@/content/blog/authors.json");
    if (Array.isArray(data.default)) {
      return data.default;
    }
    return Object.values(data.default);
  } catch (error) {
    console.error("Failed to load authors:", error);
    return [];
  }
});

/**
 * Get an author by slug.
 *
 * @param {string} slug - Author slug
 * @returns {Promise<Object|null>} Author object or null
 */
export const getAuthor = cache(async (slug) => {
  const authors = await getAuthors();
  return authors.find((a) => a.slug === slug) || null;
});

/**
 * Get all content for sitemap generation.
 *
 * WHAT: Fetches all content across all sections
 * WHY: Used by sitemap.js to generate complete sitemap
 *
 * @returns {Promise<Object>} All content by section
 */
export const getAllContent = cache(async () => {
  const [
    glossaryTerms,
    competitors,
    metrics,
    platforms,
    industries,
    integrations,
    useCases,
    tools,
    blogCategories,
  ] = await Promise.all([
    getGlossaryTerms(),
    getCompetitors(),
    getMetrics(),
    getPlatforms(),
    getIndustries(),
    getIntegrations(),
    getUseCases(),
    getTools(),
    getBlogCategories(),
  ]);

  return {
    glossary: glossaryTerms,
    competitors,
    metrics,
    platforms,
    industries,
    integrations,
    useCases,
    tools,
    blogCategories,
  };
});

/**
 * Get content counts for hub pages.
 *
 * WHAT: Returns count of items in each content section
 * WHY: Used for displaying "500+ terms" type stats
 *
 * @returns {Promise<Object>} Counts by section
 */
export const getContentCounts = cache(async () => {
  const content = await getAllContent();

  return {
    glossary: content.glossary.length,
    competitors: content.competitors.length,
    metrics: content.metrics.length,
    platforms: content.platforms.length,
    industries: content.industries.length,
    integrations: content.integrations.length,
    useCases: content.useCases.length,
    tools: content.tools.length,
  };
});
