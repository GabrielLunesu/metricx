/**
 * Content Validation Utilities
 *
 * WHAT: Validates content to prevent SEO issues
 * WHY: Ensures no thin content, duplicate titles, or keyword cannibalization
 *      that would hurt search rankings
 *
 * Related files:
 * - lib/seo/content-loader.js - Content data loading
 * - scripts/validate-content.js - CLI validation script
 */

/**
 * Validation issue types.
 */
export const ValidationIssueType = {
  THIN_CONTENT: "thin_content",
  DUPLICATE_TITLE: "duplicate_title",
  DUPLICATE_DESCRIPTION: "duplicate_description",
  KEYWORD_CANNIBALIZATION: "keyword_cannibalization",
  MISSING_REQUIRED_FIELD: "missing_required_field",
  TITLE_TOO_LONG: "title_too_long",
  DESCRIPTION_TOO_LONG: "description_too_long",
  MISSING_FAQ: "missing_faq",
  BROKEN_LINK: "broken_link",
};

/**
 * Minimum word counts by content type.
 */
const MIN_WORD_COUNTS = {
  glossary: 200,
  blog: 800,
  comparison: 500,
  metric: 400,
  platform: 400,
  industry: 400,
  integration: 300,
  useCase: 300,
  tool: 200,
};

/**
 * Maximum lengths for SEO fields.
 */
const MAX_LENGTHS = {
  title: 60,
  description: 160,
};

/**
 * Count words in a text string.
 *
 * WHAT: Counts words in content
 * WHY: Used to check minimum word count requirements
 *
 * @param {string} text - Text to count
 * @returns {number} Word count
 */
export function countWords(text) {
  if (!text) return 0;
  return text
    .trim()
    .split(/\s+/)
    .filter((word) => word.length > 0).length;
}

/**
 * Validate a single content item.
 *
 * WHAT: Validates a content item for SEO issues
 * WHY: Catches problems before they hurt rankings
 *
 * @param {Object} item - Content item to validate
 * @param {string} contentType - Type of content (glossary, blog, etc.)
 * @param {Object} [context] - Additional context for validation
 * @param {Set} [context.existingTitles] - Set of already-used titles
 * @param {Set} [context.existingDescriptions] - Set of already-used descriptions
 * @param {Map} [context.primaryKeywords] - Map of keyword -> page using it
 * @returns {Object} Validation result with issues array
 *
 * @example
 * const result = validateContent(term, "glossary", {
 *   existingTitles: new Set(["ROAS - Definition"]),
 *   primaryKeywords: new Map([["roas", "/glossary/roas"]])
 * });
 * if (!result.valid) {
 *   console.log(result.issues);
 * }
 */
export function validateContent(item, contentType, context = {}) {
  const issues = [];
  const {
    existingTitles = new Set(),
    existingDescriptions = new Set(),
    primaryKeywords = new Map(),
  } = context;

  // Check required fields based on content type
  const requiredFields = getRequiredFields(contentType);
  requiredFields.forEach((field) => {
    if (!item[field]) {
      issues.push({
        type: ValidationIssueType.MISSING_REQUIRED_FIELD,
        message: `Missing required field: ${field}`,
        field,
      });
    }
  });

  // Check word count (combine all text content)
  const textContent = getTextContent(item, contentType);
  const wordCount = countWords(textContent);
  const minWords = MIN_WORD_COUNTS[contentType] || 200;

  if (wordCount < minWords) {
    issues.push({
      type: ValidationIssueType.THIN_CONTENT,
      message: `Content too thin: ${wordCount} words (minimum: ${minWords})`,
      wordCount,
      minWords,
    });
  }

  // Check title length and duplicates
  const title = getTitle(item, contentType);
  if (title) {
    if (title.length > MAX_LENGTHS.title) {
      issues.push({
        type: ValidationIssueType.TITLE_TOO_LONG,
        message: `Title too long: ${title.length} chars (maximum: ${MAX_LENGTHS.title})`,
        title,
        length: title.length,
      });
    }

    if (existingTitles.has(title.toLowerCase())) {
      issues.push({
        type: ValidationIssueType.DUPLICATE_TITLE,
        message: `Duplicate title: "${title}"`,
        title,
      });
    }
  }

  // Check description length and duplicates
  const description = getDescription(item, contentType);
  if (description) {
    if (description.length > MAX_LENGTHS.description) {
      issues.push({
        type: ValidationIssueType.DESCRIPTION_TOO_LONG,
        message: `Description too long: ${description.length} chars (maximum: ${MAX_LENGTHS.description})`,
        description,
        length: description.length,
      });
    }

    if (existingDescriptions.has(description.toLowerCase())) {
      issues.push({
        type: ValidationIssueType.DUPLICATE_DESCRIPTION,
        message: `Duplicate description`,
        description,
      });
    }
  }

  // Check keyword cannibalization
  const primaryKeyword = getPrimaryKeyword(item, contentType);
  if (primaryKeyword && primaryKeywords.has(primaryKeyword.toLowerCase())) {
    const existingPage = primaryKeywords.get(primaryKeyword.toLowerCase());
    issues.push({
      type: ValidationIssueType.KEYWORD_CANNIBALIZATION,
      message: `Keyword "${primaryKeyword}" already targeted by ${existingPage}`,
      keyword: primaryKeyword,
      existingPage,
    });
  }

  // Check FAQs for content types that should have them
  if (["glossary", "metric", "comparison"].includes(contentType)) {
    if (!item.faqs || item.faqs.length === 0) {
      issues.push({
        type: ValidationIssueType.MISSING_FAQ,
        message: "Missing FAQ section (recommended for rich snippets)",
      });
    }
  }

  return {
    valid: issues.length === 0,
    issues,
    wordCount,
    slug: item.slug,
    contentType,
  };
}

/**
 * Get required fields for a content type.
 *
 * @param {string} contentType - Content type
 * @returns {string[]} Array of required field names
 */
function getRequiredFields(contentType) {
  const fields = {
    glossary: ["term", "slug", "definition"],
    blog: ["title", "slug", "content", "category"],
    comparison: ["name", "slug", "pricing"],
    metric: ["name", "slug", "description"],
    platform: ["name", "slug", "description"],
    industry: ["name", "slug", "description"],
    integration: ["name", "slug", "description"],
    useCase: ["name", "slug", "description"],
    tool: ["name", "slug", "description"],
  };

  return fields[contentType] || ["slug"];
}

/**
 * Extract text content for word counting.
 *
 * @param {Object} item - Content item
 * @param {string} contentType - Content type
 * @returns {string} Combined text content
 */
function getTextContent(item, contentType) {
  const textFields = {
    glossary: ["definition", "example", "formula"],
    blog: ["content", "excerpt"],
    comparison: ["description", "pros", "cons"],
    metric: ["description", "formula", "example"],
    platform: ["description", "features"],
    industry: ["description", "challenges", "solutions"],
    integration: ["description", "features"],
    useCase: ["description", "solution"],
    tool: ["description", "howToUse"],
  };

  const fields = textFields[contentType] || ["description"];
  return fields
    .map((field) => {
      const value = item[field];
      if (Array.isArray(value)) return value.join(" ");
      return value || "";
    })
    .join(" ");
}

/**
 * Get the title for a content item.
 *
 * @param {Object} item - Content item
 * @param {string} contentType - Content type
 * @returns {string|null} Title
 */
function getTitle(item, contentType) {
  if (contentType === "glossary") {
    return item.term;
  }
  return item.title || item.name || null;
}

/**
 * Get the description for a content item.
 *
 * @param {Object} item - Content item
 * @param {string} contentType - Content type
 * @returns {string|null} Description
 */
function getDescription(item, contentType) {
  if (contentType === "glossary") {
    return item.definition?.slice(0, 160);
  }
  return item.description?.slice(0, 160) || item.excerpt?.slice(0, 160) || null;
}

/**
 * Get the primary keyword for a content item.
 *
 * @param {Object} item - Content item
 * @param {string} contentType - Content type
 * @returns {string|null} Primary keyword
 */
function getPrimaryKeyword(item, contentType) {
  if (contentType === "glossary") {
    return item.term?.toLowerCase();
  }
  return item.primaryKeyword || item.name?.toLowerCase() || null;
}

/**
 * Validate all content in a collection.
 *
 * WHAT: Validates an entire content collection
 * WHY: Batch validation for pre-build checks
 *
 * @param {Array} items - Array of content items
 * @param {string} contentType - Content type
 * @returns {Object} Validation results with summary
 */
export function validateCollection(items, contentType) {
  const existingTitles = new Set();
  const existingDescriptions = new Set();
  const primaryKeywords = new Map();
  const results = [];

  items.forEach((item) => {
    const result = validateContent(item, contentType, {
      existingTitles,
      existingDescriptions,
      primaryKeywords,
    });

    results.push(result);

    // Track for duplicate detection
    const title = getTitle(item, contentType);
    if (title) existingTitles.add(title.toLowerCase());

    const description = getDescription(item, contentType);
    if (description) existingDescriptions.add(description.toLowerCase());

    const keyword = getPrimaryKeyword(item, contentType);
    if (keyword) primaryKeywords.set(keyword, `/${contentType}/${item.slug}`);
  });

  const validCount = results.filter((r) => r.valid).length;
  const invalidCount = results.filter((r) => !r.valid).length;
  const allIssues = results.flatMap((r) => r.issues);

  return {
    valid: invalidCount === 0,
    total: items.length,
    validCount,
    invalidCount,
    results,
    issuesByType: groupIssuesByType(allIssues),
  };
}

/**
 * Group issues by type for reporting.
 *
 * @param {Array} issues - Array of issues
 * @returns {Object} Issues grouped by type
 */
function groupIssuesByType(issues) {
  const grouped = {};

  issues.forEach((issue) => {
    if (!grouped[issue.type]) {
      grouped[issue.type] = [];
    }
    grouped[issue.type].push(issue);
  });

  return grouped;
}

/**
 * Generate a validation report.
 *
 * WHAT: Creates a human-readable validation report
 * WHY: For CLI output and CI/CD checks
 *
 * @param {Object} validationResult - Result from validateCollection
 * @param {string} contentType - Content type
 * @returns {string} Formatted report
 */
export function generateValidationReport(validationResult, contentType) {
  const lines = [
    `\n=== ${contentType.toUpperCase()} VALIDATION REPORT ===`,
    `Total items: ${validationResult.total}`,
    `Valid: ${validationResult.validCount}`,
    `Invalid: ${validationResult.invalidCount}`,
    "",
  ];

  if (validationResult.valid) {
    lines.push("✅ All content passes validation!");
  } else {
    lines.push("❌ Validation issues found:\n");

    Object.entries(validationResult.issuesByType).forEach(([type, issues]) => {
      lines.push(`${type} (${issues.length}):`);
      issues.forEach((issue) => {
        lines.push(`  - ${issue.message}`);
      });
      lines.push("");
    });
  }

  return lines.join("\n");
}
