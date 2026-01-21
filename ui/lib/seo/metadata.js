/**
 * SEO Metadata Generation Utilities
 *
 * WHAT: Generates dynamic, unique metadata for programmatic SEO pages
 * WHY: Ensures every page has optimized, intent-matched titles and descriptions
 *      that prevent duplicate content and keyword cannibalization
 *
 * Related files:
 * - lib/seo/schemas.js - JSON-LD schema generation
 * - lib/seo/content-loader.js - Content data loading
 * - app/(marketing)/layout.tsx - Marketing pages layout
 */

const BASE_URL = "https://www.metricx.ai";
const SITE_NAME = "metricx";
const DEFAULT_OG_IMAGE = `${BASE_URL}/og-image.png`;

/**
 * Generate canonical URL for a page.
 *
 * WHAT: Creates the canonical URL for any given path
 * WHY: Ensures consistent URL references across the site for SEO
 *
 * @param {string} path - The page path (e.g., "/glossary/roas")
 * @returns {string} Full canonical URL
 *
 * @example
 * generateCanonical("/glossary/roas") // => "https://www.metricx.ai/glossary/roas"
 */
export function generateCanonical(path) {
  // Remove trailing slash except for root
  const cleanPath = path === "/" ? "/" : path.replace(/\/$/, "");
  return `${BASE_URL}${cleanPath}`;
}

/**
 * Generate Open Graph metadata.
 *
 * WHAT: Creates OG metadata object for social sharing
 * WHY: Optimizes appearance when pages are shared on social media
 *
 * @param {Object} config - Configuration object
 * @param {string} config.title - Page title
 * @param {string} config.description - Page description
 * @param {string} config.path - Page path
 * @param {string} [config.image] - OG image URL
 * @param {string} [config.type] - OG type (default: "website")
 * @returns {Object} Open Graph metadata object
 */
export function generateOpenGraph({ title, description, path, image, type = "website" }) {
  return {
    title,
    description,
    url: generateCanonical(path),
    siteName: SITE_NAME,
    images: [
      {
        url: image || DEFAULT_OG_IMAGE,
        width: 1200,
        height: 630,
        alt: title,
      },
    ],
    locale: "en_US",
    type,
  };
}

/**
 * Generate Twitter Card metadata.
 *
 * WHAT: Creates Twitter Card metadata for sharing
 * WHY: Optimizes appearance when pages are shared on Twitter/X
 *
 * @param {Object} config - Configuration object
 * @param {string} config.title - Page title
 * @param {string} config.description - Page description
 * @param {string} [config.image] - Card image URL
 * @returns {Object} Twitter Card metadata object
 */
export function generateTwitterCard({ title, description, image }) {
  return {
    card: "summary_large_image",
    title,
    description,
    images: [image || DEFAULT_OG_IMAGE],
    creator: "@metricx_ai",
    site: "@metricx_ai",
  };
}

/**
 * Generate robots meta directives.
 *
 * WHAT: Creates robots meta configuration
 * WHY: Controls search engine indexing behavior per page
 *
 * @param {Object} [config] - Configuration object
 * @param {boolean} [config.index=true] - Allow indexing
 * @param {boolean} [config.follow=true] - Follow links
 * @returns {Object} Robots metadata object
 */
export function generateRobots({ index = true, follow = true } = {}) {
  return {
    index,
    follow,
    googleBot: {
      index,
      follow,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  };
}

/**
 * Generate complete page metadata for Next.js.
 *
 * WHAT: Creates full metadata object for Next.js generateMetadata
 * WHY: Centralized metadata generation ensures consistency and prevents duplicates
 *
 * @param {Object} config - Configuration object
 * @param {string} config.title - Page title (will be appended with " | metricx")
 * @param {string} config.description - Meta description (150-160 chars ideal)
 * @param {string} config.path - Page path for canonical URL
 * @param {string[]} [config.keywords] - Page-specific keywords
 * @param {string} [config.image] - OG image URL
 * @param {string} [config.type] - OG type
 * @param {boolean} [config.noIndex] - Prevent indexing
 * @returns {Object} Next.js Metadata object
 *
 * @example
 * generatePageMetadata({
 *   title: "ROAS (Return on Ad Spend) - Definition & Formula",
 *   description: "Learn what ROAS means in advertising...",
 *   path: "/glossary/roas",
 *   keywords: ["roas", "return on ad spend", "roas formula"]
 * })
 */
export function generatePageMetadata({
  title,
  description,
  path,
  keywords = [],
  image,
  type = "website",
  noIndex = false,
}) {
  const fullTitle = title.includes(SITE_NAME) ? title : `${title} | ${SITE_NAME}`;

  return {
    title: fullTitle,
    description,
    keywords: [
      ...keywords,
      "ad analytics",
      "advertising analytics",
      "metricx",
    ],
    alternates: {
      canonical: generateCanonical(path),
    },
    openGraph: generateOpenGraph({
      title: fullTitle,
      description,
      path,
      image,
      type,
    }),
    twitter: generateTwitterCard({
      title: fullTitle,
      description,
      image,
    }),
    robots: generateRobots({ index: !noIndex, follow: !noIndex }),
  };
}

/**
 * Generate metadata for glossary term pages.
 *
 * WHAT: Creates optimized metadata for glossary term pages
 * WHY: Ensures each glossary term has unique, keyword-rich metadata
 *
 * @param {Object} term - Glossary term data
 * @param {string} term.term - Short term (e.g., "ROAS")
 * @param {string} term.fullName - Full name (e.g., "Return on Ad Spend")
 * @param {string} term.slug - URL slug
 * @param {string} term.definition - Term definition
 * @returns {Object} Next.js Metadata object
 */
export function generateGlossaryMetadata(term) {
  const title = term.fullName
    ? `${term.term} (${term.fullName}) - Definition & Formula`
    : `${term.term} - Definition, Formula & Examples`;

  const description = `Learn what ${term.term}${term.fullName ? ` (${term.fullName})` : ""} means in advertising. ${term.definition.slice(0, 120)}...`;

  return generatePageMetadata({
    title,
    description,
    path: `/glossary/${term.slug}`,
    keywords: [
      term.term.toLowerCase(),
      term.fullName?.toLowerCase(),
      `what is ${term.term.toLowerCase()}`,
      `${term.term.toLowerCase()} formula`,
      `${term.term.toLowerCase()} calculator`,
    ].filter(Boolean),
    type: "article",
  });
}

/**
 * Generate metadata for competitor comparison pages.
 *
 * WHAT: Creates optimized metadata for vs/comparison pages
 * WHY: Targets high-intent "[competitor] alternative" keywords
 *
 * @param {Object} competitor - Competitor data
 * @param {string} competitor.name - Competitor name (e.g., "Triple Whale")
 * @param {string} competitor.slug - URL slug
 * @param {string} competitor.pricing - Competitor pricing
 * @returns {Object} Next.js Metadata object
 */
export function generateComparisonMetadata(competitor) {
  const title = `metricx vs ${competitor.name}: Comparison (2026) | Save 77%`;
  const description = `Compare metricx and ${competitor.name}. See why e-commerce brands choose metricx for ad analytics. ${competitor.name} starts at ${competitor.pricing}, metricx is just $29.99/month.`;

  return generatePageMetadata({
    title,
    description,
    path: `/vs/${competitor.slug}`,
    keywords: [
      `${competitor.name.toLowerCase()} alternative`,
      `${competitor.name.toLowerCase()} vs metricx`,
      `metricx vs ${competitor.name.toLowerCase()}`,
      `${competitor.name.toLowerCase()} pricing`,
      `${competitor.name.toLowerCase()} competitor`,
    ],
    type: "article",
  });
}

/**
 * Generate metadata for alternative pages.
 *
 * WHAT: Creates metadata for "Alternative to X" pages
 * WHY: Captures "alternative to [competitor]" search intent
 *
 * @param {Object} competitor - Competitor data
 * @returns {Object} Next.js Metadata object
 */
export function generateAlternativeMetadata(competitor) {
  const title = `Best ${competitor.name} Alternative (2026) | metricx`;
  const description = `Looking for a ${competitor.name} alternative? metricx offers the same features at 77% less. AI-powered ad analytics starting at $29.99/month.`;

  return generatePageMetadata({
    title,
    description,
    path: `/alternatives/${competitor.slug}`,
    keywords: [
      `${competitor.name.toLowerCase()} alternative`,
      `${competitor.name.toLowerCase()} alternatives`,
      `best ${competitor.name.toLowerCase()} alternative`,
      `cheaper than ${competitor.name.toLowerCase()}`,
    ],
    type: "article",
  });
}

/**
 * Generate metadata for metric deep-dive pages.
 *
 * WHAT: Creates metadata for metric explanation pages
 * WHY: Targets "what is [metric]" and "[metric] benchmarks" queries
 *
 * @param {Object} metric - Metric data
 * @param {string} metric.name - Metric name
 * @param {string} metric.slug - URL slug
 * @param {string} metric.description - Metric description
 * @returns {Object} Next.js Metadata object
 */
export function generateMetricMetadata(metric) {
  const title = `${metric.name}: Complete Guide, Benchmarks & Best Practices`;
  const description = `Everything you need to know about ${metric.name}. ${metric.description.slice(0, 100)}... Learn benchmarks, formulas, and optimization strategies.`;

  return generatePageMetadata({
    title,
    description,
    path: `/metrics/${metric.slug}`,
    keywords: [
      metric.name.toLowerCase(),
      `${metric.name.toLowerCase()} benchmark`,
      `good ${metric.name.toLowerCase()}`,
      `${metric.name.toLowerCase()} by industry`,
    ],
    type: "article",
  });
}

/**
 * Generate metadata for platform guide pages.
 *
 * WHAT: Creates metadata for platform-specific pages
 * WHY: Targets "[platform] analytics" search queries
 *
 * @param {Object} platform - Platform data
 * @param {string} platform.name - Platform name (e.g., "Meta Ads")
 * @param {string} platform.slug - URL slug
 * @param {string} platform.description - Platform description
 * @returns {Object} Next.js Metadata object
 */
export function generatePlatformMetadata(platform) {
  const title = `${platform.name} Analytics & Reporting | metricx`;
  const description = `Track and optimize your ${platform.name} campaigns with metricx. Real-time ROAS, AI insights, and unified analytics. ${platform.description.slice(0, 80)}`;

  return generatePageMetadata({
    title,
    description,
    path: `/platforms/${platform.slug}`,
    keywords: [
      `${platform.name.toLowerCase()} analytics`,
      `${platform.name.toLowerCase()} reporting`,
      `${platform.name.toLowerCase()} dashboard`,
      `${platform.name.toLowerCase()} roas`,
    ],
    type: "article",
  });
}

/**
 * Generate metadata for industry pages.
 *
 * WHAT: Creates metadata for industry-specific landing pages
 * WHY: Targets "[industry] ad analytics" search queries
 *
 * @param {Object} industry - Industry data
 * @param {string} industry.name - Industry name
 * @param {string} industry.slug - URL slug
 * @param {string} industry.description - Industry description
 * @returns {Object} Next.js Metadata object
 */
export function generateIndustryMetadata(industry) {
  const title = `Ad Analytics for ${industry.name} | metricx`;
  const description = `${industry.name} ad analytics made simple. Track Meta, Google & TikTok ads in one dashboard. AI-powered insights for ${industry.name.toLowerCase()} brands.`;

  return generatePageMetadata({
    title,
    description,
    path: `/industries/${industry.slug}`,
    keywords: [
      `${industry.name.toLowerCase()} analytics`,
      `${industry.name.toLowerCase()} ad tracking`,
      `${industry.name.toLowerCase()} marketing analytics`,
    ],
    type: "article",
  });
}

/**
 * Generate metadata for calculator/tool pages.
 *
 * WHAT: Creates metadata for interactive tool pages
 * WHY: Targets "[metric] calculator" high-intent queries
 *
 * @param {Object} tool - Tool data
 * @param {string} tool.name - Tool name
 * @param {string} tool.slug - URL slug
 * @param {string} tool.description - Tool description
 * @returns {Object} Next.js Metadata object
 */
export function generateToolMetadata(tool) {
  const title = `Free ${tool.name} | Calculate Instantly | metricx`;
  const description = `Use our free ${tool.name} to ${tool.description.slice(0, 100)}. Instant results, no signup required.`;

  return generatePageMetadata({
    title,
    description,
    path: `/tools/${tool.slug}`,
    keywords: [
      tool.name.toLowerCase(),
      `free ${tool.name.toLowerCase()}`,
      `${tool.name.toLowerCase()} online`,
    ],
    type: "website",
  });
}

/**
 * Generate metadata for blog posts.
 *
 * WHAT: Creates metadata for blog articles
 * WHY: Optimizes blog posts for search and social sharing
 *
 * @param {Object} post - Blog post data
 * @param {string} post.title - Post title
 * @param {string} post.slug - URL slug
 * @param {string} post.category - Post category
 * @param {string} post.excerpt - Post excerpt
 * @param {string} [post.image] - Featured image URL
 * @param {string[]} [post.tags] - Post tags
 * @returns {Object} Next.js Metadata object
 */
export function generateBlogMetadata(post) {
  return generatePageMetadata({
    title: post.title,
    description: post.excerpt.slice(0, 155),
    path: `/blog/${post.category}/${post.slug}`,
    keywords: post.tags || [],
    image: post.image,
    type: "article",
  });
}
