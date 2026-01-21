/**
 * Use Cases Hub Page
 *
 * WHAT: Hub page for all metricx use cases
 * WHY: SEO hub for use case-related keyword targeting
 *
 * Related files:
 * - content/use-cases/data.json - Use case data
 * - lib/seo/content-loader.js - Data loading
 */

import Link from "next/link";
import { getUseCases } from "@/lib/seo/content-loader";
import { Breadcrumbs, CTABanner } from "@/components/seo";
import { JsonLd } from "@/components/seo/JsonLd";
import { generateBreadcrumbSchema, generateWebPageSchema } from "@/lib/seo/schemas";
import { Lightbulb, ArrowRight, CheckCircle2 } from "lucide-react";

/**
 * Generate metadata for the use cases hub page.
 */
export async function generateMetadata() {
  const useCases = await getUseCases();

  return {
    title: "Use Cases | How metricx Helps E-commerce Brands | metricx",
    description: `Discover ${useCases.length}+ ways metricx helps e-commerce brands track ROAS, verify revenue, and optimize ad spend across Meta, Google, and TikTok.`,
    keywords: [
      "ad analytics use cases",
      "ecommerce roas tracking",
      "multi-platform ad tracking",
      "ad spend optimization",
      "marketing attribution",
    ],
    openGraph: {
      title: "Use Cases | metricx",
      description: "See how metricx helps e-commerce brands succeed.",
      type: "website",
      url: "https://www.metricx.ai/use-cases",
    },
    alternates: {
      canonical: "https://www.metricx.ai/use-cases",
    },
  };
}

/**
 * Use case card component.
 */
function UseCaseCard({ useCase }) {
  return (
    <Link
      href={`/use-cases/${useCase.slug}`}
      className="group block bg-white border border-slate-200 rounded-xl p-6 hover:border-cyan-300 hover:shadow-lg transition-all"
    >
      <div className="flex items-start justify-between mb-4">
        <div className="p-2 bg-slate-100 rounded-lg group-hover:bg-cyan-100 transition-colors">
          <Lightbulb className="w-5 h-5 text-slate-600 group-hover:text-cyan-600" />
        </div>
        <span className="px-2 py-1 bg-slate-100 text-slate-600 text-xs font-medium rounded-full capitalize">
          {useCase.category}
        </span>
      </div>
      <h3 className="text-xl font-semibold text-slate-900 group-hover:text-cyan-700 mb-2">
        {useCase.name}
      </h3>
      <p className="text-cyan-600 text-sm font-medium mb-2">{useCase.tagline}</p>
      <p className="text-slate-600 text-sm mb-4 line-clamp-2">{useCase.description}</p>
      <div className="flex items-center text-sm text-cyan-600 font-medium">
        Learn more
        <ArrowRight className="w-4 h-4 ml-1 group-hover:translate-x-1 transition-transform" />
      </div>
    </Link>
  );
}

/**
 * Category section component.
 */
function CategorySection({ title, useCases, description }) {
  if (useCases.length === 0) return null;

  return (
    <section className="mb-12">
      <h2 className="text-2xl font-bold text-slate-900 mb-2">{title}</h2>
      {description && <p className="text-slate-600 mb-6">{description}</p>}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {useCases.map((useCase) => (
          <UseCaseCard key={useCase.slug} useCase={useCase} />
        ))}
      </div>
    </section>
  );
}

/**
 * Use Cases Hub Page Component
 */
export default async function UseCasesHubPage() {
  const useCases = await getUseCases();

  const breadcrumbItems = [
    { name: "Home", href: "/" },
    { name: "Use Cases", href: "/use-cases" },
  ];

  // Group by category
  const analyticsUseCases = useCases.filter((u) => u.category === "analytics");
  const attributionUseCases = useCases.filter((u) => u.category === "attribution");
  const aiUseCases = useCases.filter((u) => u.category === "ai");
  const reportingUseCases = useCases.filter((u) => u.category === "reporting");
  const optimizationUseCases = useCases.filter((u) => u.category === "optimization");
  const otherUseCases = useCases.filter(
    (u) => !["analytics", "attribution", "ai", "reporting", "optimization"].includes(u.category)
  );

  return (
    <>
      {/* Structured Data */}
      <JsonLd schema={generateBreadcrumbSchema(breadcrumbItems)} />
      <JsonLd
        schema={generateWebPageSchema({
          title: "Use Cases",
          description: "Discover how metricx helps e-commerce brands",
          url: "https://www.metricx.ai/use-cases",
        })}
      />

      {/* Breadcrumbs */}
      <Breadcrumbs items={breadcrumbItems} />

      {/* Hero Section */}
      <div className="mb-12">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-cyan-100 rounded-lg">
            <Lightbulb className="w-6 h-6 text-cyan-600" />
          </div>
          <span className="text-sm font-medium text-cyan-600">
            {useCases.length}+ Use Cases
          </span>
        </div>
        <h1 className="text-4xl font-bold text-slate-900 mb-4">
          How metricx Helps E-commerce Brands
        </h1>
        <p className="text-lg text-slate-600 max-w-3xl">
          From tracking ROAS across platforms to AI-powered optimization insights,
          discover all the ways metricx can help grow your business.
        </p>
      </div>

      {/* Key Benefits */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-12">
        <div className="bg-slate-50 rounded-xl p-4 text-center">
          <div className="text-3xl font-bold text-cyan-600 mb-1">5+</div>
          <div className="text-sm text-slate-600">Hours saved weekly</div>
        </div>
        <div className="bg-slate-50 rounded-xl p-4 text-center">
          <div className="text-3xl font-bold text-cyan-600 mb-1">30%</div>
          <div className="text-sm text-slate-600">Better ROAS accuracy</div>
        </div>
        <div className="bg-slate-50 rounded-xl p-4 text-center">
          <div className="text-3xl font-bold text-cyan-600 mb-1">3</div>
          <div className="text-sm text-slate-600">Platforms unified</div>
        </div>
        <div className="bg-slate-50 rounded-xl p-4 text-center">
          <div className="text-3xl font-bold text-cyan-600 mb-1">5 min</div>
          <div className="text-sm text-slate-600">Setup time</div>
        </div>
      </div>

      {/* Analytics Use Cases */}
      <CategorySection
        title="Analytics & Tracking"
        description="Track and analyze your ad performance across all platforms."
        useCases={analyticsUseCases}
      />

      {/* Attribution Use Cases */}
      <CategorySection
        title="Attribution & Verification"
        description="Know your true ROAS with revenue verification."
        useCases={attributionUseCases}
      />

      {/* AI Use Cases */}
      <CategorySection
        title="AI-Powered Insights"
        description="Get intelligent recommendations and answers."
        useCases={aiUseCases}
      />

      {/* Reporting Use Cases */}
      <CategorySection
        title="Reporting & Automation"
        description="Save time with automated reports and alerts."
        useCases={reportingUseCases}
      />

      {/* Optimization Use Cases */}
      <CategorySection
        title="Optimization"
        description="Improve campaign performance with data-driven decisions."
        useCases={optimizationUseCases}
      />

      {/* Other */}
      {otherUseCases.length > 0 && (
        <CategorySection title="More Use Cases" useCases={otherUseCases} />
      )}

      {/* CTA */}
      <CTABanner
        title="See metricx in Action"
        description="Start your free trial and experience these use cases firsthand."
        primaryCTA={{ text: "Start Free Trial", href: "/sign-up" }}
        secondaryCTA={{ text: "See Features", href: "/#features" }}
      />
    </>
  );
}
