/**
 * Blog Hub Page
 *
 * WHAT: Hub page for all blog content
 * WHY: SEO hub for blog-related keyword targeting
 *
 * Related files:
 * - content/blog/categories.json - Blog categories
 * - content/blog/authors.json - Author profiles
 * - lib/seo/content-loader.js - Data loading
 */

import Link from "next/link";
import { getBlogCategories } from "@/lib/seo/content-loader";
import { Breadcrumbs, CTABanner } from "@/components/seo";
import { JsonLd } from "@/components/seo/JsonLd";
import { generateBreadcrumbSchema, generateWebPageSchema } from "@/lib/seo/schemas";
import { BookOpen, ArrowRight, FileText, TrendingUp } from "lucide-react";

/**
 * Generate metadata for the blog hub page.
 */
export async function generateMetadata() {
  return {
    title: "Blog | E-commerce Ad Analytics Insights | metricx",
    description: "Expert insights on e-commerce advertising, ROAS optimization, multi-platform tracking, and ad analytics best practices.",
    keywords: [
      "ecommerce advertising blog",
      "roas optimization tips",
      "ad analytics insights",
      "marketing analytics blog",
      "dtc advertising",
    ],
    openGraph: {
      title: "Blog | metricx",
      description: "Expert insights on e-commerce advertising and analytics.",
      type: "website",
      url: "https://www.metricx.ai/blog",
    },
    alternates: {
      canonical: "https://www.metricx.ai/blog",
    },
  };
}

/**
 * Category card component.
 */
function CategoryCard({ category }) {
  return (
    <Link
      href={`/blog/${category.slug}`}
      className="group block bg-white border border-slate-200 rounded-xl p-6 hover:border-cyan-300 hover:shadow-lg transition-all"
    >
      <div className="flex items-start justify-between mb-4">
        <div className="p-2 bg-slate-100 rounded-lg group-hover:bg-cyan-100 transition-colors">
          <FileText className="w-5 h-5 text-slate-600 group-hover:text-cyan-600" />
        </div>
        <ArrowRight className="w-5 h-5 text-slate-300 group-hover:text-cyan-500" />
      </div>
      <h3 className="text-xl font-semibold text-slate-900 group-hover:text-cyan-700 mb-2">
        {category.name}
      </h3>
      <p className="text-slate-600 text-sm mb-4">{category.description}</p>
      <div className="flex flex-wrap gap-2">
        {category.topics?.slice(0, 3).map((topic) => (
          <span
            key={topic}
            className="px-2 py-1 bg-slate-100 text-slate-600 text-xs rounded-full"
          >
            {topic}
          </span>
        ))}
      </div>
    </Link>
  );
}

/**
 * Featured topics section component.
 */
function FeaturedTopics() {
  const topics = [
    { name: "ROAS Optimization", href: "/glossary/roas" },
    { name: "Multi-Platform Tracking", href: "/use-cases/track-roas-across-platforms" },
    { name: "Attribution", href: "/use-cases/verify-platform-revenue" },
    { name: "Meta Ads", href: "/platforms/meta-ads" },
    { name: "Google Ads", href: "/platforms/google-ads" },
    { name: "TikTok Ads", href: "/platforms/tiktok-ads" },
  ];

  return (
    <div className="flex flex-wrap gap-2">
      {topics.map((topic) => (
        <Link
          key={topic.name}
          href={topic.href}
          className="px-3 py-2 bg-white border border-slate-200 rounded-lg text-slate-700 hover:border-cyan-300 hover:text-cyan-700 transition-colors"
        >
          {topic.name}
        </Link>
      ))}
    </div>
  );
}

/**
 * Blog Hub Page Component
 */
export default async function BlogHubPage() {
  const categories = await getBlogCategories();

  const breadcrumbItems = [
    { name: "Home", href: "/" },
    { name: "Blog", href: "/blog" },
  ];

  return (
    <>
      {/* Structured Data */}
      <JsonLd schema={generateBreadcrumbSchema(breadcrumbItems)} />
      <JsonLd
        schema={generateWebPageSchema({
          title: "Blog",
          description: "E-commerce ad analytics insights and best practices",
          url: "https://www.metricx.ai/blog",
        })}
      />

      {/* Breadcrumbs */}
      <Breadcrumbs items={breadcrumbItems} />

      {/* Hero Section */}
      <div className="mb-12">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-cyan-100 rounded-lg">
            <BookOpen className="w-6 h-6 text-cyan-600" />
          </div>
          <span className="text-sm font-medium text-cyan-600">Blog</span>
        </div>
        <h1 className="text-4xl font-bold text-slate-900 mb-4">
          E-commerce Ad Analytics Insights
        </h1>
        <p className="text-lg text-slate-600 max-w-3xl">
          Expert insights, guides, and best practices for e-commerce advertising.
          Learn how to optimize ROAS, track performance across platforms, and grow
          your business with data-driven decisions.
        </p>
      </div>

      {/* Featured Topics */}
      <section className="mb-12">
        <h2 className="text-xl font-semibold text-slate-900 mb-4">
          Popular Topics
        </h2>
        <FeaturedTopics />
      </section>

      {/* Browse by Category */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-slate-900 mb-6">
          Browse by Category
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {categories.map((category) => (
            <CategoryCard key={category.slug} category={category} />
          ))}
        </div>
      </section>

      {/* Resources Section */}
      <section className="mb-12 bg-slate-50 rounded-xl p-8">
        <h2 className="text-2xl font-bold text-slate-900 mb-6">
          More Resources
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Link
            href="/glossary"
            className="flex items-start gap-3 p-4 bg-white rounded-lg border border-slate-200 hover:border-cyan-300 transition-colors group"
          >
            <BookOpen className="w-5 h-5 text-cyan-500 mt-1" />
            <div>
              <h3 className="font-semibold text-slate-900 group-hover:text-cyan-700">
                Glossary
              </h3>
              <p className="text-sm text-slate-600">
                500+ ad analytics terms explained
              </p>
            </div>
          </Link>
          <Link
            href="/tools"
            className="flex items-start gap-3 p-4 bg-white rounded-lg border border-slate-200 hover:border-cyan-300 transition-colors group"
          >
            <TrendingUp className="w-5 h-5 text-cyan-500 mt-1" />
            <div>
              <h3 className="font-semibold text-slate-900 group-hover:text-cyan-700">
                Free Calculators
              </h3>
              <p className="text-sm text-slate-600">
                ROAS, CPA, CPM, and more
              </p>
            </div>
          </Link>
          <Link
            href="/use-cases"
            className="flex items-start gap-3 p-4 bg-white rounded-lg border border-slate-200 hover:border-cyan-300 transition-colors group"
          >
            <FileText className="w-5 h-5 text-cyan-500 mt-1" />
            <div>
              <h3 className="font-semibold text-slate-900 group-hover:text-cyan-700">
                Use Cases
              </h3>
              <p className="text-sm text-slate-600">
                See how metricx helps brands
              </p>
            </div>
          </Link>
        </div>
      </section>

      {/* CTA */}
      <CTABanner
        title="Ready to Optimize Your Ads?"
        description="Start your free trial and see your ad performance in a whole new way."
        primaryCTA={{ text: "Start Free Trial", href: "/sign-up" }}
        secondaryCTA={{ text: "See Features", href: "/#features" }}
      />
    </>
  );
}
