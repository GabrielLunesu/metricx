/**
 * Metrics Hub Page
 *
 * WHAT: Hub page for all advertising metrics deep dives
 * WHY: SEO hub for metric-related keyword targeting
 *
 * Related files:
 * - content/metrics/data.json - Metric data
 * - lib/seo/content-loader.js - Data loading
 */

import Link from "next/link";
import { getMetrics } from "@/lib/seo/content-loader";
import { Breadcrumbs, CTABanner } from "@/components/seo";
import { JsonLd } from "@/components/seo/JsonLd";
import { generateBreadcrumbSchema, generateWebPageSchema } from "@/lib/seo/schemas";
import { TrendingUp, ArrowRight, DollarSign, Eye, Users, BarChart3 } from "lucide-react";

/**
 * Generate metadata for the metrics hub page.
 */
export async function generateMetadata() {
  const metrics = await getMetrics();

  return {
    title: "Ad Metrics Explained | ROAS, CPA, CTR, CPM Guides | metricx",
    description: `Deep dive into ${metrics.length}+ advertising metrics. Learn formulas, benchmarks, and optimization strategies for ROAS, CPA, CTR, CPM, and more.`,
    keywords: [
      "advertising metrics",
      "roas explained",
      "cpa explained",
      "ctr explained",
      "ad metrics guide",
      "marketing metrics",
    ],
    openGraph: {
      title: "Ad Metrics Explained | metricx",
      description: "Comprehensive guides for every advertising metric.",
      type: "website",
      url: "https://www.metricx.ai/metrics",
    },
    alternates: {
      canonical: "https://www.metricx.ai/metrics",
    },
  };
}

/**
 * Get icon for metric category.
 */
function getCategoryIcon(category) {
  const icons = {
    performance: TrendingUp,
    cost: DollarSign,
    engagement: Eye,
    revenue: BarChart3,
    reach: Users,
  };
  return icons[category] || TrendingUp;
}

/**
 * Metric card component.
 */
function MetricCard({ metric }) {
  const Icon = getCategoryIcon(metric.category);

  return (
    <Link
      href={`/metrics/${metric.slug}`}
      className="group block bg-white border border-slate-200 rounded-xl p-6 hover:border-cyan-300 hover:shadow-lg transition-all"
    >
      <div className="flex items-start justify-between mb-4">
        <div className="p-2 bg-slate-100 rounded-lg group-hover:bg-cyan-100 transition-colors">
          <Icon className="w-5 h-5 text-slate-600 group-hover:text-cyan-600" />
        </div>
        <span className="text-sm text-slate-500 capitalize">{metric.category}</span>
      </div>
      <h3 className="text-xl font-semibold text-slate-900 group-hover:text-cyan-700 mb-1">
        {metric.abbreviation || metric.name}
      </h3>
      <p className="text-sm text-slate-500 mb-2">{metric.name}</p>
      <p className="text-slate-600 line-clamp-2">{metric.description}</p>
    </Link>
  );
}

/**
 * Metrics Hub Page Component
 */
export default async function MetricsHubPage() {
  const metrics = await getMetrics();

  // Group by category
  const categories = {
    performance: metrics.filter((m) => m.category === "performance"),
    cost: metrics.filter((m) => m.category === "cost"),
    engagement: metrics.filter((m) => m.category === "engagement"),
    revenue: metrics.filter((m) => m.category === "revenue"),
    reach: metrics.filter((m) => m.category === "reach"),
    other: metrics.filter((m) => !["performance", "cost", "engagement", "revenue", "reach"].includes(m.category)),
  };

  const breadcrumbItems = [
    { name: "Home", href: "/" },
    { name: "Metrics", href: "/metrics" },
  ];

  return (
    <>
      {/* Structured Data */}
      <JsonLd schema={generateBreadcrumbSchema(breadcrumbItems)} />
      <JsonLd
        schema={generateWebPageSchema({
          title: "Ad Metrics Explained",
          description: "Comprehensive guides for advertising metrics",
          url: "https://www.metricx.ai/metrics",
        })}
      />

      {/* Breadcrumbs */}
      <Breadcrumbs items={breadcrumbItems} />

      {/* Hero Section */}
      <div className="mb-12">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-cyan-100 rounded-lg">
            <TrendingUp className="w-6 h-6 text-cyan-600" />
          </div>
          <span className="text-sm font-medium text-cyan-600">
            {metrics.length}+ Metrics
          </span>
        </div>
        <h1 className="text-4xl font-bold text-slate-900 mb-4">
          Advertising Metrics Explained
        </h1>
        <p className="text-lg text-slate-600 max-w-3xl">
          Deep dive into every advertising metric. Learn formulas, see benchmarks,
          and discover optimization strategies to improve your ad performance.
        </p>
      </div>

      {/* Metrics by Category */}
      {Object.entries(categories).map(([category, categoryMetrics]) => {
        if (categoryMetrics.length === 0) return null;
        const Icon = getCategoryIcon(category);

        return (
          <section key={category} className="mb-12">
            <div className="flex items-center gap-2 mb-6">
              <Icon className="w-5 h-5 text-slate-600" />
              <h2 className="text-2xl font-bold text-slate-900 capitalize">
                {category} Metrics
              </h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {categoryMetrics.map((metric) => (
                <MetricCard key={metric.slug} metric={metric} />
              ))}
            </div>
          </section>
        );
      })}

      {/* CTA */}
      <CTABanner
        title="Track All Metrics in One Dashboard"
        description="metricx automatically tracks ROAS, CPA, CTR, and all key metrics across Meta, Google, and TikTok."
        primaryCTA={{ text: "Start Free Trial", href: "/sign-up" }}
        secondaryCTA={{ text: "See Features", href: "/#features" }}
      />
    </>
  );
}
