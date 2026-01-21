/**
 * JSON-LD Schema Generation Utilities
 *
 * WHAT: Generates structured data (JSON-LD) for rich search results
 * WHY: Schema markup helps search engines understand content and can
 *      trigger rich snippets (FAQ, HowTo, Article, etc.) in search results
 *
 * Related files:
 * - lib/seo/metadata.js - Page metadata generation
 * - components/seo/JsonLd.jsx - JSON-LD rendering component
 *
 * Schema.org references:
 * - https://schema.org/Organization
 * - https://schema.org/Article
 * - https://schema.org/FAQPage
 * - https://schema.org/BreadcrumbList
 * - https://schema.org/HowTo
 * - https://schema.org/SoftwareApplication
 */

const BASE_URL = "https://www.metricx.ai";

/**
 * Generate Organization schema.
 *
 * WHAT: Creates Organization structured data for the website
 * WHY: Helps search engines understand the business and may trigger
 *      knowledge panel features
 *
 * @returns {Object} Organization schema object
 *
 * @example
 * // Use in root layout
 * <JsonLd schema={generateOrganizationSchema()} />
 */
export function generateOrganizationSchema() {
  return {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: "metricx",
    url: BASE_URL,
    logo: `${BASE_URL}/logo.png`,
    description:
      "AI-powered ad analytics platform for e-commerce. Unified Meta Ads, Google Ads, and Shopify analytics with real-time ROAS tracking.",
    foundingDate: "2024",
    sameAs: [
      "https://twitter.com/metricx_ai",
      "https://linkedin.com/company/metricx",
    ],
    contactPoint: {
      "@type": "ContactPoint",
      contactType: "customer service",
      email: "support@metricx.ai",
    },
  };
}

/**
 * Generate SoftwareApplication schema.
 *
 * WHAT: Creates SoftwareApplication structured data
 * WHY: Marks metricx as a software product with pricing info
 *
 * @returns {Object} SoftwareApplication schema object
 */
export function generateSoftwareApplicationSchema() {
  return {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    name: "metricx",
    applicationCategory: "BusinessApplication",
    operatingSystem: "Web",
    offers: {
      "@type": "Offer",
      price: "29.99",
      priceCurrency: "USD",
      priceValidUntil: "2026-12-31",
    },
    aggregateRating: {
      "@type": "AggregateRating",
      ratingValue: "4.9",
      ratingCount: "150",
    },
    description:
      "AI-powered ad analytics for e-commerce. Track Meta Ads, Google Ads, and Shopify in one dashboard.",
  };
}

/**
 * Generate Article schema for content pages.
 *
 * WHAT: Creates Article structured data for blog posts and articles
 * WHY: Can trigger article rich results with author info and publish date
 *
 * @param {Object} article - Article data
 * @param {string} article.title - Article title
 * @param {string} article.description - Article description/excerpt
 * @param {string} article.url - Full article URL
 * @param {string} [article.image] - Featured image URL
 * @param {string} [article.datePublished] - ISO date string
 * @param {string} [article.dateModified] - ISO date string
 * @param {Object} [article.author] - Author information
 * @returns {Object} Article schema object
 *
 * @example
 * <JsonLd schema={generateArticleSchema({
 *   title: "What is ROAS?",
 *   description: "Learn about Return on Ad Spend...",
 *   url: "https://www.metricx.ai/glossary/roas",
 *   datePublished: "2024-01-15",
 *   author: { name: "metricx Team" }
 * })} />
 */
export function generateArticleSchema(article) {
  return {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: article.title,
    description: article.description,
    url: article.url,
    image: article.image || `${BASE_URL}/og-image.png`,
    datePublished: article.datePublished || new Date().toISOString(),
    dateModified: article.dateModified || article.datePublished || new Date().toISOString(),
    author: {
      "@type": article.author?.type || "Organization",
      name: article.author?.name || "metricx",
      url: article.author?.url || BASE_URL,
    },
    publisher: {
      "@type": "Organization",
      name: "metricx",
      logo: {
        "@type": "ImageObject",
        url: `${BASE_URL}/logo.png`,
      },
    },
    mainEntityOfPage: {
      "@type": "WebPage",
      "@id": article.url,
    },
  };
}

/**
 * Generate FAQPage schema for FAQ sections.
 *
 * WHAT: Creates FAQPage structured data from FAQ array
 * WHY: Can trigger FAQ rich results with expandable answers in search
 *
 * @param {Array<{question: string, answer: string}>} faqs - Array of FAQ objects
 * @returns {Object} FAQPage schema object
 *
 * @example
 * <JsonLd schema={generateFAQSchema([
 *   { question: "What is a good ROAS?", answer: "A good ROAS depends on..." },
 *   { question: "How do I calculate ROAS?", answer: "ROAS = Revenue / Ad Spend..." }
 * ])} />
 */
export function generateFAQSchema(faqs) {
  if (!faqs || faqs.length === 0) return null;

  return {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: faqs.map((faq) => ({
      "@type": "Question",
      name: faq.question || faq.q,
      acceptedAnswer: {
        "@type": "Answer",
        text: faq.answer || faq.a,
      },
    })),
  };
}

/**
 * Generate BreadcrumbList schema for navigation.
 *
 * WHAT: Creates BreadcrumbList structured data
 * WHY: Helps search engines understand site hierarchy and can show
 *      breadcrumb trails in search results
 *
 * @param {Array<{name: string, url: string}>} items - Breadcrumb items
 * @returns {Object} BreadcrumbList schema object
 *
 * @example
 * <JsonLd schema={generateBreadcrumbSchema([
 *   { name: "Home", url: "https://www.metricx.ai" },
 *   { name: "Glossary", url: "https://www.metricx.ai/glossary" },
 *   { name: "ROAS", url: "https://www.metricx.ai/glossary/roas" }
 * ])} />
 */
export function generateBreadcrumbSchema(items) {
  if (!items || items.length === 0) return null;

  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: items.map((item, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: item.name,
      item: item.url,
    })),
  };
}

/**
 * Generate HowTo schema for calculator/tool pages.
 *
 * WHAT: Creates HowTo structured data for step-by-step guides
 * WHY: Can trigger HowTo rich results with step cards in search
 *
 * @param {Object} config - HowTo configuration
 * @param {string} config.name - Name of the how-to (e.g., "How to Calculate ROAS")
 * @param {string} config.description - Brief description
 * @param {Array<{name: string, text: string}>} config.steps - Array of steps
 * @param {string} [config.totalTime] - ISO 8601 duration (e.g., "PT5M" for 5 minutes)
 * @returns {Object} HowTo schema object
 *
 * @example
 * <JsonLd schema={generateHowToSchema({
 *   name: "How to Calculate ROAS",
 *   description: "Calculate your Return on Ad Spend in 3 easy steps",
 *   steps: [
 *     { name: "Enter Ad Spend", text: "Enter your total advertising spend" },
 *     { name: "Enter Revenue", text: "Enter the revenue generated from ads" },
 *     { name: "Get ROAS", text: "See your ROAS calculated instantly" }
 *   ],
 *   totalTime: "PT1M"
 * })} />
 */
export function generateHowToSchema({ name, description, steps, totalTime }) {
  return {
    "@context": "https://schema.org",
    "@type": "HowTo",
    name,
    description,
    totalTime: totalTime || "PT5M",
    step: steps.map((step, index) => ({
      "@type": "HowToStep",
      position: index + 1,
      name: step.name,
      text: step.text,
    })),
  };
}

/**
 * Generate DefinedTerm schema for glossary terms.
 *
 * WHAT: Creates DefinedTerm structured data
 * WHY: Marks glossary entries as defined terms for better understanding
 *
 * @param {Object} term - Term data
 * @param {string} term.term - The term being defined
 * @param {string} term.fullName - Full name/expansion
 * @param {string} term.definition - The definition
 * @param {string} term.url - Full URL to the term page
 * @returns {Object} DefinedTerm schema object
 */
export function generateDefinedTermSchema(term) {
  return {
    "@context": "https://schema.org",
    "@type": "DefinedTerm",
    name: term.term,
    alternateName: term.fullName,
    description: term.definition,
    url: term.url,
    inDefinedTermSet: {
      "@type": "DefinedTermSet",
      name: "Ad Analytics Glossary",
      url: `${BASE_URL}/glossary`,
    },
  };
}

/**
 * Generate WebPage schema with speakable markup.
 *
 * WHAT: Creates WebPage schema with speakable sections
 * WHY: Helps voice assistants identify key content to read aloud
 *
 * @param {Object} config - Page configuration
 * @param {string} config.name - Page name
 * @param {string} config.description - Page description
 * @param {string} config.url - Page URL
 * @param {string[]} [config.speakableSelectors] - CSS selectors for speakable content
 * @returns {Object} WebPage schema object
 */
export function generateWebPageSchema({ name, description, url, speakableSelectors }) {
  const schema = {
    "@context": "https://schema.org",
    "@type": "WebPage",
    name,
    description,
    url,
    publisher: {
      "@type": "Organization",
      name: "metricx",
    },
  };

  if (speakableSelectors && speakableSelectors.length > 0) {
    schema.speakable = {
      "@type": "SpeakableSpecification",
      cssSelector: speakableSelectors,
    };
  }

  return schema;
}

/**
 * Generate Product schema for comparison pages.
 *
 * WHAT: Creates Product schema for software comparison
 * WHY: Shows pricing and rating info in search results
 *
 * @param {Object} config - Product configuration
 * @returns {Object} Product schema object
 */
export function generateProductComparisonSchema() {
  return {
    "@context": "https://schema.org",
    "@type": "Product",
    name: "metricx",
    description: "AI-powered ad analytics platform for e-commerce",
    brand: {
      "@type": "Brand",
      name: "metricx",
    },
    offers: {
      "@type": "Offer",
      price: "29.99",
      priceCurrency: "USD",
      availability: "https://schema.org/InStock",
      priceValidUntil: "2026-12-31",
    },
    aggregateRating: {
      "@type": "AggregateRating",
      ratingValue: "4.9",
      reviewCount: "150",
    },
  };
}

/**
 * Combine multiple schemas into a single graph.
 *
 * WHAT: Merges multiple schema objects into one @graph array
 * WHY: Reduces script tags and properly links related schemas
 *
 * @param {Object[]} schemas - Array of schema objects to combine
 * @returns {Object} Combined schema with @graph
 *
 * @example
 * <JsonLd schema={combineSchemas([
 *   generateOrganizationSchema(),
 *   generateBreadcrumbSchema(breadcrumbs),
 *   generateArticleSchema(article)
 * ])} />
 */
export function combineSchemas(schemas) {
  const validSchemas = schemas.filter(Boolean);
  if (validSchemas.length === 0) return null;
  if (validSchemas.length === 1) return validSchemas[0];

  return {
    "@context": "https://schema.org",
    "@graph": validSchemas.map((schema) => {
      // Remove @context from individual schemas when combining
      const { "@context": _, ...rest } = schema;
      return rest;
    }),
  };
}
