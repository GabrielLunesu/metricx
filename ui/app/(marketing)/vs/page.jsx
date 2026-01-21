/**
 * Comparisons Hub Page
 *
 * WHAT: Hub page for all competitor comparison pages
 * WHY: SEO hub targeting "X vs Y" and "X alternative" keywords
 *
 * Related files:
 * - content/competitors/data.json - Competitor data
 * - lib/seo/content-loader.js - Data loading
 * - components/seo/ - SEO components
 */

import Link from "next/link";
import { getCompetitors } from "@/lib/seo/content-loader";
import { Breadcrumbs, CTABanner } from "@/components/seo";
import { JsonLd } from "@/components/seo/JsonLd";
import { generateBreadcrumbSchema, generateWebPageSchema } from "@/lib/seo/schemas";
import { GitCompare, Check, X, ArrowRight, DollarSign, Users, Zap } from "lucide-react";

/**
 * Generate metadata for the comparisons hub page.
 */
export async function generateMetadata() {
  const competitors = await getCompetitors();

  return {
    title: "metricx vs Competitors | Triple Whale, Northbeam, Madgicx Alternatives",
    description: `Compare metricx to ${competitors.map((c) => c.name).join(", ")}. See why e-commerce brands switch to metricx for simpler, more affordable ad analytics.`,
    keywords: [
      "triple whale alternative",
      "northbeam alternative",
      "madgicx alternative",
      "ad analytics comparison",
      "ecommerce analytics tools",
    ],
    openGraph: {
      title: "metricx vs Competitors | Ad Analytics Comparison",
      description: "See how metricx compares to Triple Whale, Northbeam, and other ad analytics tools.",
      type: "website",
      url: "https://www.metricx.ai/vs",
    },
    twitter: {
      card: "summary_large_image",
      title: "metricx vs Competitors",
      description: "Compare metricx to popular ad analytics tools.",
    },
    alternates: {
      canonical: "https://www.metricx.ai/vs",
    },
  };
}

/**
 * Competitor card component.
 */
function CompetitorCard({ competitor }) {
  const price = competitor.comparisonPoints?.price;

  return (
    <Link
      href={`/vs/${competitor.slug}`}
      className="group block bg-white border border-slate-200 rounded-xl p-6 hover:border-cyan-300 hover:shadow-lg transition-all"
    >
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-xl font-semibold text-slate-900 group-hover:text-cyan-700">
            metricx vs {competitor.name}
          </h3>
          <p className="text-sm text-slate-500">{competitor.targetAudience}</p>
        </div>
        <ArrowRight className="w-5 h-5 text-slate-300 group-hover:text-cyan-500 transition-colors" />
      </div>

      <p className="text-slate-600 mb-4 line-clamp-2">{competitor.description}</p>

      {/* Quick Comparison */}
      <div className="grid grid-cols-2 gap-4 pt-4 border-t border-slate-100">
        <div>
          <div className="text-sm text-slate-500 mb-1">{competitor.name}</div>
          <div className="font-semibold text-slate-900">{competitor.pricing}</div>
        </div>
        <div>
          <div className="text-sm text-slate-500 mb-1">metricx</div>
          <div className="font-semibold text-cyan-600">$29.99/month</div>
        </div>
      </div>

      {price?.savings && (
        <div className="mt-4 inline-flex items-center gap-1 px-3 py-1 bg-emerald-100 text-emerald-700 text-sm font-medium rounded-full">
          <DollarSign className="w-3 h-3" />
          Save {price.savings}
        </div>
      )}
    </Link>
  );
}

/**
 * Quick comparison table component.
 */
function QuickComparisonTable({ competitors }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-slate-200">
            <th className="text-left py-4 px-4 font-semibold text-slate-900">
              Platform
            </th>
            <th className="text-left py-4 px-4 font-semibold text-slate-900">
              Starting Price
            </th>
            <th className="text-left py-4 px-4 font-semibold text-slate-900">
              Target Market
            </th>
            <th className="text-center py-4 px-4 font-semibold text-slate-900">
              AI Copilot
            </th>
            <th className="text-left py-4 px-4 font-semibold text-slate-900">
              Setup Time
            </th>
          </tr>
        </thead>
        <tbody>
          {/* metricx row */}
          <tr className="bg-cyan-50 border-b border-cyan-100">
            <td className="py-4 px-4">
              <span className="font-semibold text-cyan-700">metricx</span>
            </td>
            <td className="py-4 px-4 font-semibold text-cyan-700">$29.99/month</td>
            <td className="py-4 px-4 text-slate-600">SMB to Mid-market</td>
            <td className="py-4 px-4 text-center">
              <Check className="w-5 h-5 text-emerald-500 mx-auto" />
            </td>
            <td className="py-4 px-4 text-slate-600">5 minutes</td>
          </tr>
          {/* Competitor rows */}
          {competitors.map((competitor) => (
            <tr key={competitor.slug} className="border-b border-slate-100">
              <td className="py-4 px-4">
                <Link
                  href={`/vs/${competitor.slug}`}
                  className="font-medium text-slate-900 hover:text-cyan-600"
                >
                  {competitor.name}
                </Link>
              </td>
              <td className="py-4 px-4 text-slate-600">{competitor.pricing}</td>
              <td className="py-4 px-4 text-slate-600">{competitor.targetAudience}</td>
              <td className="py-4 px-4 text-center">
                {competitor.features?.aiInsights ? (
                  <Check className="w-5 h-5 text-emerald-500 mx-auto" />
                ) : (
                  <X className="w-5 h-5 text-slate-300 mx-auto" />
                )}
              </td>
              <td className="py-4 px-4 text-slate-600">
                {competitor.comparisonPoints?.setupTime?.them || "Varies"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/**
 * Comparisons Hub Page Component
 */
export default async function ComparisonsHubPage() {
  const competitors = await getCompetitors();

  const breadcrumbItems = [
    { name: "Home", href: "/" },
    { name: "Comparisons", href: "/vs" },
  ];

  // Group by pricing tier
  const enterprise = competitors.filter(
    (c) => c.pricing.includes("500") || c.pricing.includes("1000")
  );
  const midMarket = competitors.filter(
    (c) =>
      !c.pricing.includes("500") &&
      !c.pricing.includes("1000") &&
      (c.pricing.includes("100") || c.pricing.includes("200") || c.pricing.includes("250"))
  );
  const starter = competitors.filter(
    (c) =>
      !enterprise.includes(c) && !midMarket.includes(c)
  );

  return (
    <>
      {/* Structured Data */}
      <JsonLd schema={generateBreadcrumbSchema(breadcrumbItems)} />
      <JsonLd
        schema={generateWebPageSchema({
          title: "metricx vs Competitors",
          description: "Compare metricx to popular ad analytics tools",
          url: "https://www.metricx.ai/vs",
        })}
      />

      {/* Breadcrumbs */}
      <Breadcrumbs items={breadcrumbItems} />

      {/* Hero Section */}
      <div className="mb-12">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-cyan-100 rounded-lg">
            <GitCompare className="w-6 h-6 text-cyan-600" />
          </div>
          <span className="text-sm font-medium text-cyan-600">
            {competitors.length} Comparisons
          </span>
        </div>
        <h1 className="text-4xl font-bold text-slate-900 mb-4">
          metricx vs Competitors
        </h1>
        <p className="text-lg text-slate-600 max-w-3xl">
          See how metricx compares to Triple Whale, Northbeam, Madgicx, and other
          ad analytics platforms. We believe in transparency—here's exactly how we stack up.
        </p>
      </div>

      {/* Key Differentiators */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
        <div className="p-6 bg-gradient-to-br from-cyan-50 to-white border border-cyan-100 rounded-xl">
          <DollarSign className="w-8 h-8 text-cyan-600 mb-3" />
          <h3 className="font-semibold text-slate-900 mb-2">
            80% Lower Price
          </h3>
          <p className="text-sm text-slate-600">
            $29.99/month flat rate. No scaling with ad spend. No surprise fees.
          </p>
        </div>
        <div className="p-6 bg-gradient-to-br from-cyan-50 to-white border border-cyan-100 rounded-xl">
          <Zap className="w-8 h-8 text-cyan-600 mb-3" />
          <h3 className="font-semibold text-slate-900 mb-2">
            5-Minute Setup
          </h3>
          <p className="text-sm text-slate-600">
            Connect your accounts and start seeing insights immediately. No complex onboarding.
          </p>
        </div>
        <div className="p-6 bg-gradient-to-br from-cyan-50 to-white border border-cyan-100 rounded-xl">
          <Users className="w-8 h-8 text-cyan-600 mb-3" />
          <h3 className="font-semibold text-slate-900 mb-2">
            AI That Explains
          </h3>
          <p className="text-sm text-slate-600">
            Ask questions in plain English. Get answers with data, not more dashboards.
          </p>
        </div>
      </div>

      {/* Quick Comparison Table */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-slate-900 mb-6">
          Quick Comparison
        </h2>
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
          <QuickComparisonTable competitors={competitors} />
        </div>
      </section>

      {/* All Comparisons */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-slate-900 mb-6">
          Detailed Comparisons
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {competitors.map((competitor) => (
            <CompetitorCard key={competitor.slug} competitor={competitor} />
          ))}
        </div>
      </section>

      {/* Alternative Pages Links */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-slate-900 mb-6">
          Looking for Alternatives?
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {competitors.map((competitor) => (
            <Link
              key={competitor.slug}
              href={`/alternatives/${competitor.slug}`}
              className="p-4 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors text-center"
            >
              <div className="text-sm text-slate-600">Best</div>
              <div className="font-medium text-slate-900">
                {competitor.name} Alternative
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* CTA */}
      <CTABanner
        title="Ready to Switch?"
        description="Join thousands of e-commerce brands who chose simpler, more affordable ad analytics."
        primaryCTA={{ text: "Start Free Trial", href: "/sign-up" }}
        secondaryCTA={{ text: "See Pricing", href: "/#pricing" }}
      />
    </>
  );
}
