/**
 * SEO Utilities Index
 *
 * WHAT: Exports all SEO utilities for easy importing
 * WHY: Single import point for SEO functionality
 *
 * @example
 * import { generatePageMetadata, generateFAQSchema, getBreadcrumbPath } from '@/lib/seo';
 */

// Metadata generation
export {
  generateCanonical,
  generateOpenGraph,
  generateTwitterCard,
  generateRobots,
  generatePageMetadata,
  generateGlossaryMetadata,
  generateComparisonMetadata,
  generateAlternativeMetadata,
  generateMetricMetadata,
  generatePlatformMetadata,
  generateIndustryMetadata,
  generateToolMetadata,
  generateBlogMetadata,
} from "./metadata.js";

// JSON-LD Schema generation
export {
  generateOrganizationSchema,
  generateSoftwareApplicationSchema,
  generateArticleSchema,
  generateFAQSchema,
  generateBreadcrumbSchema,
  generateHowToSchema,
  generateDefinedTermSchema,
  generateWebPageSchema,
  generateProductComparisonSchema,
  combineSchemas,
} from "./schemas.js";

// Breadcrumb utilities
export {
  getBreadcrumbPath,
  slugToTitle,
  getGlossaryBreadcrumbs,
  getComparisonBreadcrumbs,
  getAlternativeBreadcrumbs,
  getBlogBreadcrumbs,
  getMetricBreadcrumbs,
  getPlatformBreadcrumbs,
  getIndustryBreadcrumbs,
  getToolBreadcrumbs,
  getIntegrationBreadcrumbs,
  getUseCaseBreadcrumbs,
} from "./breadcrumbs.js";

// Internal linking utilities
export {
  LinkTypes,
  getRelatedGlossaryTerms,
  getSiblingPages,
  getParentHub,
  findGlossaryTermsInText,
  getLinkSuggestions,
  buildSectionNav,
  getFeaturedLinks,
  buildLinkMap,
} from "./internal-links.js";

// Content loading utilities
export {
  getGlossaryTerms,
  getGlossaryTerm,
  getGlossaryTermsByLetter,
  getGlossaryTermsByCategory,
  getCompetitors,
  getCompetitor,
  getMetrics,
  getMetric,
  getPlatforms,
  getPlatform,
  getIndustries,
  getIndustry,
  getIntegrations,
  getIntegration,
  getUseCases,
  getUseCase,
  getTools,
  getTool,
  getBlogCategories,
  getAuthors,
  getAuthor,
  getAllContent,
  getContentCounts,
} from "./content-loader.js";

// Content validation utilities
export {
  ValidationIssueType,
  countWords,
  validateContent,
  validateCollection,
  generateValidationReport,
} from "./validators.js";
