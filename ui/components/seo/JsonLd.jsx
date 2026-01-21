/**
 * JSON-LD Structured Data Component
 *
 * WHAT: Renders JSON-LD structured data in the document head
 * WHY: Structured data helps search engines understand content and can
 *      trigger rich snippets (FAQ, HowTo, Article) in search results
 *
 * Related files:
 * - lib/seo/schemas.js - Schema generation utilities
 *
 * @example
 * import { JsonLd } from '@/components/seo/JsonLd';
 * import { generateFAQSchema } from '@/lib/seo';
 *
 * <JsonLd schema={generateFAQSchema(faqs)} />
 */

/**
 * Renders JSON-LD structured data.
 *
 * @param {Object} props - Component props
 * @param {Object|null} props.schema - JSON-LD schema object to render
 * @returns {JSX.Element|null} Script tag with JSON-LD or null if no schema
 */
export function JsonLd({ schema }) {
  // Don't render if no schema provided
  if (!schema) return null;

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{
        __html: JSON.stringify(schema, null, 0),
      }}
    />
  );
}

/**
 * Renders multiple JSON-LD schemas.
 *
 * WHAT: Convenience component for rendering multiple schemas
 * WHY: Some pages need multiple schema types (e.g., Article + FAQ + Breadcrumb)
 *
 * @param {Object} props - Component props
 * @param {Object[]} props.schemas - Array of schema objects
 * @returns {JSX.Element} Fragment with multiple JsonLd components
 *
 * @example
 * <MultiJsonLd schemas={[
 *   generateArticleSchema(article),
 *   generateFAQSchema(faqs),
 *   generateBreadcrumbSchema(breadcrumbs)
 * ]} />
 */
export function MultiJsonLd({ schemas }) {
  return (
    <>
      {schemas.filter(Boolean).map((schema, index) => (
        <JsonLd key={index} schema={schema} />
      ))}
    </>
  );
}

export default JsonLd;
