/**
 * Internal Linking Utilities
 *
 * WHAT: Manages intelligent internal linking for SEO pages
 * WHY: Strong internal linking improves crawlability, distributes page authority,
 *      and helps users discover related content (hub-and-spoke model)
 *
 * Related files:
 * - lib/seo/content-loader.js - Content data loading
 * - components/seo/RelatedContent.jsx - Related content display
 */

import { getGlossaryTerms } from "./content-loader.js";

/**
 * Link relationship types for internal linking.
 */
export const LinkTypes = {
  RELATED: "related",      // Topically related content
  SIBLING: "sibling",      // Same category/level
  PARENT: "parent",        // Parent hub page
  CHILD: "child",          // Child detail page
  DEFINITION: "definition", // Links to glossary definitions
};

/**
 * Get related glossary terms for a given term.
 *
 * WHAT: Finds glossary terms related to a specific term
 * WHY: Creates cross-linking between related concepts
 *
 * @param {string} termSlug - Current term's slug
 * @param {string[]} relatedSlugs - Array of related term slugs from content
 * @param {number} [limit=5] - Maximum number of related terms
 * @returns {Promise<Array>} Array of related term objects
 *
 * @example
 * const related = await getRelatedGlossaryTerms("roas", ["cac", "ltv", "cpa"]);
 */
export async function getRelatedGlossaryTerms(termSlug, relatedSlugs = [], limit = 5) {
  const allTerms = await getGlossaryTerms();

  // First, get explicitly related terms
  const explicitlyRelated = relatedSlugs
    .map((slug) => allTerms.find((t) => t.slug === slug))
    .filter(Boolean);

  // If we need more, find terms in the same category
  if (explicitlyRelated.length < limit) {
    const currentTerm = allTerms.find((t) => t.slug === termSlug);
    if (currentTerm) {
      const sameCategoryTerms = allTerms
        .filter(
          (t) =>
            t.category === currentTerm.category &&
            t.slug !== termSlug &&
            !relatedSlugs.includes(t.slug)
        )
        .slice(0, limit - explicitlyRelated.length);

      return [...explicitlyRelated, ...sameCategoryTerms].slice(0, limit);
    }
  }

  return explicitlyRelated.slice(0, limit);
}

/**
 * Get sibling pages within a category.
 *
 * WHAT: Finds pages at the same level within a content category
 * WHY: Enables "See also" and navigation between related pages
 *
 * @param {string} category - Content category (e.g., "glossary", "metrics")
 * @param {string} currentSlug - Current page's slug
 * @param {Array} allItems - All items in the category
 * @param {number} [limit=6] - Maximum number of siblings
 * @returns {Array} Array of sibling page objects
 */
export function getSiblingPages(category, currentSlug, allItems, limit = 6) {
  return allItems
    .filter((item) => item.slug !== currentSlug)
    .slice(0, limit)
    .map((item) => ({
      name: item.name || item.term || item.title,
      slug: item.slug,
      href: `/${category}/${item.slug}`,
    }));
}

/**
 * Get parent hub page for a detail page.
 *
 * WHAT: Returns the hub page for a given content section
 * WHY: Enables "Back to [Hub]" navigation and breadcrumb structure
 *
 * @param {string} section - Content section (e.g., "glossary", "blog")
 * @returns {Object} Parent hub page info
 */
export function getParentHub(section) {
  const hubs = {
    glossary: { name: "Glossary", href: "/glossary" },
    blog: { name: "Blog", href: "/blog" },
    vs: { name: "Comparisons", href: "/vs" },
    alternatives: { name: "Alternatives", href: "/alternatives" },
    metrics: { name: "Metrics", href: "/metrics" },
    platforms: { name: "Platforms", href: "/platforms" },
    industries: { name: "Industries", href: "/industries" },
    integrations: { name: "Integrations", href: "/integrations" },
    tools: { name: "Tools", href: "/tools" },
    "use-cases": { name: "Use Cases", href: "/use-cases" },
  };

  return hubs[section] || null;
}

/**
 * Find glossary terms mentioned in text content.
 *
 * WHAT: Scans text and finds matching glossary terms
 * WHY: Enables auto-linking of glossary terms within content
 *
 * @param {string} text - Text content to scan
 * @param {Array} glossaryTerms - All glossary terms
 * @param {string[]} [excludeSlugs=[]] - Slugs to exclude (e.g., current page)
 * @returns {Array} Array of found terms with positions
 */
export function findGlossaryTermsInText(text, glossaryTerms, excludeSlugs = []) {
  const found = [];
  const textLower = text.toLowerCase();

  glossaryTerms.forEach((term) => {
    if (excludeSlugs.includes(term.slug)) return;

    // Check for term and fullName matches
    const searchTerms = [term.term, term.fullName].filter(Boolean);

    searchTerms.forEach((searchTerm) => {
      const searchLower = searchTerm.toLowerCase();
      let position = textLower.indexOf(searchLower);

      if (position !== -1) {
        // Only add if not already found
        if (!found.some((f) => f.slug === term.slug)) {
          found.push({
            slug: term.slug,
            term: term.term,
            fullName: term.fullName,
            position,
            matchedText: searchTerm,
            href: `/glossary/${term.slug}`,
          });
        }
      }
    });
  });

  // Sort by position in text
  return found.sort((a, b) => a.position - b.position);
}

/**
 * Generate contextual link suggestions for a page.
 *
 * WHAT: Suggests internal links based on page content and type
 * WHY: Ensures pages link to relevant content across the site
 *
 * @param {Object} config - Page configuration
 * @param {string} config.pageType - Type of page (glossary, blog, metrics, etc.)
 * @param {string[]} config.tags - Page tags/keywords
 * @param {string} config.currentSlug - Current page slug
 * @returns {Object} Link suggestions by category
 */
export function getLinkSuggestions({ pageType, tags = [], currentSlug }) {
  const suggestions = {
    glossary: [],
    metrics: [],
    tools: [],
    blog: [],
    comparisons: [],
  };

  // Map tags to relevant sections
  const tagToSection = {
    roas: ["glossary/roas", "tools/roas-calculator", "metrics/roas"],
    cpa: ["glossary/cpa", "tools/cpa-calculator", "metrics/cpa"],
    cpc: ["glossary/cpc", "tools/cpc-calculator"],
    cpm: ["glossary/cpm", "tools/cpm-calculator"],
    ctr: ["glossary/ctr", "tools/ctr-calculator"],
    meta: ["platforms/meta-ads"],
    google: ["platforms/google-ads"],
    shopify: ["integrations/shopify"],
    ecommerce: ["industries/ecommerce"],
  };

  tags.forEach((tag) => {
    const tagLower = tag.toLowerCase();
    const links = tagToSection[tagLower];
    if (links) {
      links.forEach((link) => {
        const [section, slug] = link.split("/");
        if (`${section}/${slug}` !== `${pageType}/${currentSlug}`) {
          if (section === "glossary") suggestions.glossary.push({ href: `/${link}`, slug });
          else if (section === "tools") suggestions.tools.push({ href: `/${link}`, slug });
          else if (section === "metrics") suggestions.metrics.push({ href: `/${link}`, slug });
        }
      });
    }
  });

  return suggestions;
}

/**
 * Build a navigation menu for a content section.
 *
 * WHAT: Creates navigation items for section sidebar/menu
 * WHY: Improves discoverability and internal linking for crawlers
 *
 * @param {string} section - Content section
 * @param {Array} items - All items in the section
 * @param {Object} [options] - Options
 * @param {number} [options.limit] - Max items to show
 * @param {boolean} [options.groupByCategory] - Group items by category
 * @returns {Array} Navigation items
 */
export function buildSectionNav(section, items, { limit, groupByCategory = false } = {}) {
  let navItems = items.map((item) => ({
    name: item.name || item.term || item.title,
    slug: item.slug,
    href: `/${section}/${item.slug}`,
    category: item.category,
  }));

  if (limit) {
    navItems = navItems.slice(0, limit);
  }

  if (groupByCategory) {
    const grouped = {};
    navItems.forEach((item) => {
      const cat = item.category || "other";
      if (!grouped[cat]) grouped[cat] = [];
      grouped[cat].push(item);
    });
    return grouped;
  }

  return navItems;
}

/**
 * Get featured/popular links for hub pages.
 *
 * WHAT: Returns curated links for hub page featured sections
 * WHY: Highlights important content and guides user navigation
 *
 * @param {string} section - Content section
 * @returns {Array} Featured link objects
 */
export function getFeaturedLinks(section) {
  const featured = {
    glossary: [
      { name: "ROAS", href: "/glossary/roas", description: "Return on Ad Spend" },
      { name: "CPA", href: "/glossary/cpa", description: "Cost Per Acquisition" },
      { name: "CTR", href: "/glossary/ctr", description: "Click-Through Rate" },
      { name: "CPM", href: "/glossary/cpm", description: "Cost Per Mille" },
      { name: "CAC", href: "/glossary/cac", description: "Customer Acquisition Cost" },
      { name: "LTV", href: "/glossary/ltv", description: "Lifetime Value" },
    ],
    tools: [
      { name: "ROAS Calculator", href: "/tools/roas-calculator", description: "Calculate your Return on Ad Spend" },
      { name: "CPA Calculator", href: "/tools/cpa-calculator", description: "Calculate Cost Per Acquisition" },
      { name: "Break-even ROAS", href: "/tools/break-even-roas-calculator", description: "Find your break-even point" },
    ],
    vs: [
      { name: "vs Triple Whale", href: "/vs/triple-whale", description: "Compare with Triple Whale" },
      { name: "vs Northbeam", href: "/vs/northbeam", description: "Compare with Northbeam" },
      { name: "vs Madgicx", href: "/vs/madgicx", description: "Compare with Madgicx" },
    ],
    platforms: [
      { name: "Meta Ads", href: "/platforms/meta-ads", description: "Facebook & Instagram advertising" },
      { name: "Google Ads", href: "/platforms/google-ads", description: "Google advertising" },
      { name: "TikTok Ads", href: "/platforms/tiktok-ads", description: "TikTok advertising" },
    ],
  };

  return featured[section] || [];
}

/**
 * Create a link map for content cross-referencing.
 *
 * WHAT: Builds a map of all internal links for validation
 * WHY: Helps identify orphan pages and validate internal link structure
 *
 * @param {Object} allContent - All content by section
 * @returns {Map} Map of URL to link data
 */
export function buildLinkMap(allContent) {
  const linkMap = new Map();

  Object.entries(allContent).forEach(([section, items]) => {
    items.forEach((item) => {
      const href = `/${section}/${item.slug}`;
      linkMap.set(href, {
        href,
        name: item.name || item.term || item.title,
        section,
        slug: item.slug,
        inboundLinks: [],
        outboundLinks: item.relatedTerms || item.related || [],
      });
    });
  });

  return linkMap;
}
