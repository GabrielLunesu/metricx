/**
 * Alternatives Hub Page
 *
 * WHAT: Hub page linking to all "[competitor] alternative" pages
 * WHY: SEO hub for alternative keyword targeting
 *
 * Related files:
 * - content/competitors/data.json - Competitor data
 * - /vs/[competitor]/page.jsx - Comparison pages
 */

import Link from "next/link";
import { getCompetitors } from "@/lib/seo/content-loader";
import { Breadcrumbs, CTABanner } from "@/components/seo";
import { JsonLd } from "@/components/seo/JsonLd";
import { generateBreadcrumbSchema, generateWebPageSchema } from "@/lib/seo/schemas";
import { ArrowRight, RefreshCw, DollarSign, Zap, Sparkles } from "lucide-react";

/**
 * Generate metadata for alternatives hub.
 */
export async function generateMetadata() {
  const competitors = await getCompetitors();

  return {
    title: "Best Ad Analytics Tool Alternatives | Triple Whale, Northbeam, Madgicx",
    description: `Looking for alternatives to ${competitors.slice(0, 3).map((c) => c.name).join(", ")}? metricx offers simpler, more affordable ad analytics for e-commerce brands.`,
    keywords: competitors.flatMap((c) => [
      `${c.name.toLowerCase()} alternative`,
      `${c.name.toLowerCase()} alternatives`,
      `best ${c.name.toLowerCase()} alternative`,
    ]),
    openGraph: {
      title: "Best Ad Analytics Tool Alternatives | metricx",
      description: "Find the best alternatives to popular ad analytics tools.",
      type: "website",
      url: "https://www.metricx.ai/alternatives",
    },
    alternates: {
      canonical: "https://www.metricx.ai/alternatives",
    },
  };
}

/**
 * Alternatives Hub Page Component
 */
export default async function AlternativesHubPage() {
  const competitors = await getCompetitors();

  const breadcrumbItems = [
    { name: "Home", href: "/" },
    { name: "Alternatives", href: "/alternatives" },
  ];

  return (
    <>
      {/* Structured Data */}
      <JsonLd schema={generateBreadcrumbSchema(breadcrumbItems)} />
      <JsonLd
        schema={generateWebPageSchema({
          title: "Ad Analytics Tool Alternatives",
          description: "Find alternatives to popular ad analytics tools",
          url: "https://www.metricx.ai/alternatives",
        })}
      />

      {/* Breadcrumbs */}
      <Breadcrumbs items={breadcrumbItems} />

      {/* Hero */}
      <div className="mb-12">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-cyan-100 rounded-lg">
            <RefreshCw className="w-6 h-6 text-cyan-600" />
          </div>
          <span className="text-sm font-medium text-cyan-600">
            Tool Alternatives
          </span>
        </div>
        <h1 className="text-4xl font-bold text-slate-900 mb-4">
          Ad Analytics Tool Alternatives
        </h1>
        <p className="text-lg text-slate-600 max-w-3xl">
          Looking to switch from your current ad analytics tool? See why thousands
          of e-commerce brands choose metricx as their simpler, more affordable alternative.
        </p>
      </div>

      {/* Why Switch */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
        <div className="p-6 bg-gradient-to-br from-cyan-50 to-white border border-cyan-100 rounded-xl">
          <DollarSign className="w-8 h-8 text-cyan-600 mb-3" />
          <h3 className="font-semibold text-slate-900 mb-2">
            Save 70-95%
          </h3>
          <p className="text-sm text-slate-600">
            Flat $29.99/month pricing vs $100-$1000+/month for competitors.
          </p>
        </div>
        <div className="p-6 bg-gradient-to-br from-cyan-50 to-white border border-cyan-100 rounded-xl">
          <Zap className="w-8 h-8 text-cyan-600 mb-3" />
          <h3 className="font-semibold text-slate-900 mb-2">
            Switch in Minutes
          </h3>
          <p className="text-sm text-slate-600">
            No complex migration. Connect your accounts and start seeing data.
          </p>
        </div>
        <div className="p-6 bg-gradient-to-br from-cyan-50 to-white border border-cyan-100 rounded-xl">
          <Sparkles className="w-8 h-8 text-cyan-600 mb-3" />
          <h3 className="font-semibold text-slate-900 mb-2">
            AI-First Analytics
          </h3>
          <p className="text-sm text-slate-600">
            Ask questions in plain English instead of clicking through dashboards.
          </p>
        </div>
      </div>

      {/* Alternatives List */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-slate-900 mb-6">
          Find Your Alternative
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {competitors.map((competitor) => (
            <Link
              key={competitor.slug}
              href={`/alternatives/${competitor.slug}`}
              className="group flex items-center justify-between p-6 bg-white border border-slate-200 rounded-xl hover:border-cyan-300 hover:shadow-lg transition-all"
            >
              <div>
                <h3 className="text-xl font-semibold text-slate-900 group-hover:text-cyan-700">
                  Best {competitor.name} Alternative
                </h3>
                <p className="text-sm text-slate-500 mt-1">
                  {competitor.pricing} → $29.99/month
                </p>
                {competitor.comparisonPoints?.price?.savings && (
                  <span className="inline-flex items-center gap-1 mt-2 px-3 py-1 bg-emerald-100 text-emerald-700 text-sm font-medium rounded-full">
                    Save {competitor.comparisonPoints.price.savings}
                  </span>
                )}
              </div>
              <ArrowRight className="w-5 h-5 text-slate-300 group-hover:text-cyan-500 transition-colors" />
            </Link>
          ))}
        </div>
      </section>

      {/* CTA */}
      <CTABanner
        title="Ready to Switch?"
        description="Start your free trial and see why brands choose metricx over expensive alternatives."
        primaryCTA={{ text: "Start Free Trial", href: "/sign-up" }}
        secondaryCTA={{ text: "Compare All Tools", href: "/vs" }}
      />
    </>
  );
}
