/**
 * SEO Components Index
 *
 * WHAT: Exports all SEO-related React components
 * WHY: Single import point for SEO components
 *
 * @example
 * import { JsonLd, Breadcrumbs, FAQ, CTABanner } from '@/components/seo';
 */

export { JsonLd, MultiJsonLd } from "./JsonLd";
export { Breadcrumbs, CompactBreadcrumbs } from "./Breadcrumbs";
export { FAQ, FAQList } from "./FAQ";
export {
  RelatedContent,
  RelatedLinks,
  RelatedSidebar,
  FeaturedContent,
} from "./RelatedContent";
export {
  TableOfContents,
  FloatingTOC,
  extractHeadings,
} from "./TableOfContents";
export { AuthorCard, AuthorByline, defaultAuthor } from "./AuthorCard";
export {
  CTABanner,
  InlineCTA,
  ComparisonCTA,
  CalculatorCTA,
} from "./CTABanner";
export {
  ShareButtons,
  CompactShareButton,
  NativeShareButton,
} from "./ShareButtons";
