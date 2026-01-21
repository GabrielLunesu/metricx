/**
 * Blog Category Page
 *
 * WHAT: Category-specific blog listing page
 * WHY: SEO page for blog category keywords
 *
 * Related files:
 * - content/blog/categories.json - Blog categories
 * - lib/seo/content-loader.js - Data loading
 */

import { notFound } from "next/navigation";
import Link from "next/link";
import { getBlogCategories } from "@/lib/seo/content-loader";
import { Breadcrumbs, CTABanner } from "@/components/seo";
import { JsonLd } from "@/components/seo/JsonLd";
import { generateBreadcrumbSchema, generateWebPageSchema } from "@/lib/seo/schemas";
import { FileText, ArrowRight, BookOpen, Calendar } from "lucide-react";

/**
 * Get a single category by slug.
 */
async function getCategory(slug) {
  const categories = await getBlogCategories();
  return categories.find((c) => c.slug === slug) || null;
}

/**
 * Generate static params for all categories.
 */
export async function generateStaticParams() {
  const categories = await getBlogCategories();
  return categories.map((c) => ({
    category: c.slug,
  }));
}

/**
 * Generate metadata for category page.
 */
export async function generateMetadata({ params }) {
  const { category: slug } = await params;
  const category = await getCategory(slug);

  if (!category) {
    return {
      title: "Category Not Found | metricx Blog",
    };
  }

  return {
    title: `${category.name} | metricx Blog`,
    description: `${category.description} Browse articles about ${category.topics?.join(", ") || category.name.toLowerCase()}.`,
    keywords: [
      category.name.toLowerCase(),
      ...(category.topics || []).map((t) => t.toLowerCase()),
      "ecommerce advertising",
      "ad analytics",
    ],
    openGraph: {
      title: `${category.name} | metricx Blog`,
      description: category.description,
      type: "website",
      url: `https://www.metricx.ai/blog/${category.slug}`,
    },
    alternates: {
      canonical: `https://www.metricx.ai/blog/${category.slug}`,
    },
  };
}

/**
 * Related resources component.
 */
function RelatedResources({ category }) {
  // Map category to relevant resources
  const resourceMap = {
    "roas-optimization": [
      { name: "ROAS Calculator", href: "/tools/roas-calculator" },
      { name: "ROAS Explained", href: "/glossary/roas" },
      { name: "Break-even ROAS", href: "/tools/break-even-roas-calculator" },
    ],
    "platform-guides": [
      { name: "Meta Ads Guide", href: "/platforms/meta-ads" },
      { name: "Google Ads Guide", href: "/platforms/google-ads" },
      { name: "TikTok Ads Guide", href: "/platforms/tiktok-ads" },
    ],
    attribution: [
      { name: "Verify Revenue", href: "/use-cases/verify-platform-revenue" },
      { name: "Cross-Platform Tracking", href: "/use-cases/track-roas-across-platforms" },
    ],
    default: [
      { name: "All Glossary Terms", href: "/glossary" },
      { name: "Free Calculators", href: "/tools" },
      { name: "Use Cases", href: "/use-cases" },
    ],
  };

  const resources = resourceMap[category.slug] || resourceMap.default;

  return (
    <div className="bg-slate-50 rounded-xl p-6">
      <h3 className="text-lg font-semibold text-slate-900 mb-4">Related Resources</h3>
      <div className="space-y-2">
        {resources.map((resource) => (
          <Link
            key={resource.href}
            href={resource.href}
            className="flex items-center justify-between p-3 bg-white rounded-lg border border-slate-200 hover:border-cyan-300 transition-colors group"
          >
            <span className="font-medium text-slate-900 group-hover:text-cyan-700">
              {resource.name}
            </span>
            <ArrowRight className="w-4 h-4 text-slate-300 group-hover:text-cyan-500" />
          </Link>
        ))}
      </div>
    </div>
  );
}

/**
 * Blog Category Page Component
 */
export default async function BlogCategoryPage({ params }) {
  const { category: slug } = await params;
  const category = await getCategory(slug);
  const allCategories = await getBlogCategories();

  if (!category) {
    notFound();
  }

  const breadcrumbItems = [
    { name: "Home", href: "/" },
    { name: "Blog", href: "/blog" },
    { name: category.name, href: `/blog/${category.slug}` },
  ];

  // Other categories for sidebar
  const otherCategories = allCategories.filter((c) => c.slug !== slug).slice(0, 5);

  return (
    <>
      {/* Structured Data */}
      <JsonLd schema={generateBreadcrumbSchema(breadcrumbItems)} />
      <JsonLd
        schema={generateWebPageSchema({
          title: category.name,
          description: category.description,
          url: `https://www.metricx.ai/blog/${category.slug}`,
        })}
      />

      {/* Breadcrumbs */}
      <Breadcrumbs items={breadcrumbItems} />

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Content Column */}
        <div className="lg:col-span-2">
          {/* Header */}
          <header className="mb-8">
            <div className="flex items-center gap-2 text-sm text-slate-500 mb-2">
              <Link href="/blog" className="hover:text-cyan-600">
                Blog
              </Link>
            </div>
            <h1 className="text-4xl font-bold text-slate-900 mb-4">
              {category.name}
            </h1>
            <p className="text-lg text-slate-600">{category.description}</p>
          </header>

          {/* Topics */}
          {category.topics && category.topics.length > 0 && (
            <section className="mb-8">
              <h2 className="text-xl font-semibold text-slate-900 mb-4">
                Topics Covered
              </h2>
              <div className="flex flex-wrap gap-2">
                {category.topics.map((topic) => (
                  <span
                    key={topic}
                    className="px-3 py-1 bg-cyan-50 text-cyan-700 rounded-full text-sm"
                  >
                    {topic}
                  </span>
                ))}
              </div>
            </section>
          )}

          {/* Coming Soon Message */}
          <div className="bg-slate-50 rounded-xl p-8 text-center mb-8">
            <FileText className="w-12 h-12 text-slate-300 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-slate-900 mb-2">
              Articles Coming Soon
            </h2>
            <p className="text-slate-600 mb-4">
              We're working on comprehensive guides and articles for this category.
              In the meantime, explore our other resources.
            </p>
            <div className="flex justify-center gap-4">
              <Link
                href="/glossary"
                className="px-4 py-2 bg-white border border-slate-200 rounded-lg text-slate-700 hover:border-cyan-300 transition-colors"
              >
                Browse Glossary
              </Link>
              <Link
                href="/tools"
                className="px-4 py-2 bg-cyan-500 text-white rounded-lg hover:bg-cyan-600 transition-colors"
              >
                Try Calculators
              </Link>
            </div>
          </div>

          {/* CTA */}
          <CTABanner
            title="Get Notified When We Publish"
            description="Sign up for metricx and be the first to know when new articles are published."
            primaryCTA={{ text: "Start Free Trial", href: "/sign-up" }}
            secondaryCTA={{ text: "Back to Blog", href: "/blog" }}
            variant="inline"
          />
        </div>

        {/* Sidebar */}
        <aside className="space-y-6">
          {/* Related Resources */}
          <RelatedResources category={category} />

          {/* Other Categories */}
          <div className="bg-slate-50 rounded-xl p-6">
            <h3 className="text-lg font-semibold text-slate-900 mb-4">
              Other Categories
            </h3>
            <div className="space-y-2">
              {otherCategories.map((c) => (
                <Link
                  key={c.slug}
                  href={`/blog/${c.slug}`}
                  className="flex items-center justify-between p-3 bg-white rounded-lg border border-slate-200 hover:border-cyan-300 transition-colors group"
                >
                  <span className="font-medium text-slate-900 group-hover:text-cyan-700">
                    {c.name}
                  </span>
                  <ArrowRight className="w-4 h-4 text-slate-300 group-hover:text-cyan-500" />
                </Link>
              ))}
            </div>
          </div>

          {/* Back to Blog */}
          <Link
            href="/blog"
            className="flex items-center justify-center gap-2 p-4 bg-cyan-50 text-cyan-700 rounded-xl hover:bg-cyan-100 transition-colors font-medium"
          >
            Back to Blog
            <ArrowRight className="w-4 h-4" />
          </Link>
        </aside>
      </div>
    </>
  );
}
