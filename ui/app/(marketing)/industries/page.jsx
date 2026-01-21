/**
 * Industries Hub Page
 *
 * WHAT: Hub page for all industry-specific ad analytics guides
 * WHY: SEO hub for industry-related keyword targeting
 *
 * Related files:
 * - content/industries/data.json - Industry data
 * - lib/seo/content-loader.js - Data loading
 */

import Link from "next/link";
import { getIndustries } from "@/lib/seo/content-loader";
import { Breadcrumbs, CTABanner } from "@/components/seo";
import { JsonLd } from "@/components/seo/JsonLd";
import { generateBreadcrumbSchema, generateWebPageSchema } from "@/lib/seo/schemas";
import { Building2, ArrowRight, TrendingUp, DollarSign } from "lucide-react";

/**
 * Generate metadata for the industries hub page.
 */
export async function generateMetadata() {
  const industries = await getIndustries();

  return {
    title: "Ad Analytics by Industry | E-commerce, SaaS, Fashion & More | metricx",
    description: `Industry-specific ad analytics guides for ${industries.length}+ verticals. Learn benchmarks, strategies, and best practices for fashion, beauty, health, home, and more.`,
    keywords: [
      "ecommerce analytics by industry",
      "fashion ads analytics",
      "beauty brand advertising",
      "dtic advertising guide",
      "industry ad benchmarks",
    ],
    openGraph: {
      title: "Ad Analytics by Industry | metricx",
      description: "Industry-specific guides with benchmarks and strategies.",
      type: "website",
      url: "https://www.metricx.ai/industries",
    },
    alternates: {
      canonical: "https://www.metricx.ai/industries",
    },
  };
}

/**
 * Industry card component.
 */
function IndustryCard({ industry }) {
  return (
    <Link
      href={`/industries/${industry.slug}`}
      className="group block bg-white border border-slate-200 rounded-xl p-6 hover:border-cyan-300 hover:shadow-lg transition-all"
    >
      <div className="flex items-start justify-between mb-4">
        <div className="p-2 bg-slate-100 rounded-lg group-hover:bg-cyan-100 transition-colors">
          <Building2 className="w-5 h-5 text-slate-600 group-hover:text-cyan-600" />
        </div>
        <ArrowRight className="w-5 h-5 text-slate-300 group-hover:text-cyan-500" />
      </div>
      <h3 className="text-xl font-semibold text-slate-900 group-hover:text-cyan-700 mb-2">
        {industry.name}
      </h3>
      <p className="text-slate-600 text-sm mb-4 line-clamp-2">{industry.description}</p>
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-1 text-emerald-600">
          <TrendingUp className="w-4 h-4" />
          <span>Target ROAS: {industry.targetROAS}</span>
        </div>
        <div className="flex items-center gap-1 text-slate-500">
          <DollarSign className="w-4 h-4" />
          <span>AOV: {industry.averageAOV}</span>
        </div>
      </div>
    </Link>
  );
}

/**
 * Industry benchmarks table component.
 */
function IndustryBenchmarksTable({ industries }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200">
            <th className="text-left py-3 px-4 font-semibold text-slate-900">Industry</th>
            <th className="text-left py-3 px-4 font-semibold text-slate-900">Target ROAS</th>
            <th className="text-left py-3 px-4 font-semibold text-slate-900">Avg AOV</th>
            <th className="text-left py-3 px-4 font-semibold text-slate-900">Best Platforms</th>
          </tr>
        </thead>
        <tbody>
          {industries.map((industry) => (
            <tr key={industry.slug} className="border-b border-slate-100 hover:bg-slate-50">
              <td className="py-3 px-4">
                <Link href={`/industries/${industry.slug}`} className="font-medium text-slate-900 hover:text-cyan-600">
                  {industry.name}
                </Link>
              </td>
              <td className="py-3 px-4 text-emerald-600 font-medium">{industry.targetROAS}</td>
              <td className="py-3 px-4 text-slate-600">{industry.averageAOV}</td>
              <td className="py-3 px-4">
                <div className="flex flex-wrap gap-1">
                  {industry.bestPlatforms?.slice(0, 3).map((platform) => (
                    <span key={platform} className="px-2 py-0.5 bg-slate-100 text-slate-600 text-xs rounded-full">
                      {platform}
                    </span>
                  ))}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/**
 * Industries Hub Page Component
 */
export default async function IndustriesHubPage() {
  const industries = await getIndustries();

  const breadcrumbItems = [
    { name: "Home", href: "/" },
    { name: "Industries", href: "/industries" },
  ];

  return (
    <>
      {/* Structured Data */}
      <JsonLd schema={generateBreadcrumbSchema(breadcrumbItems)} />
      <JsonLd
        schema={generateWebPageSchema({
          title: "Ad Analytics by Industry",
          description: "Industry-specific ad analytics guides",
          url: "https://www.metricx.ai/industries",
        })}
      />

      {/* Breadcrumbs */}
      <Breadcrumbs items={breadcrumbItems} />

      {/* Hero Section */}
      <div className="mb-12">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-cyan-100 rounded-lg">
            <Building2 className="w-6 h-6 text-cyan-600" />
          </div>
          <span className="text-sm font-medium text-cyan-600">
            {industries.length} Industries
          </span>
        </div>
        <h1 className="text-4xl font-bold text-slate-900 mb-4">
          Ad Analytics by Industry
        </h1>
        <p className="text-lg text-slate-600 max-w-3xl">
          Every industry has unique challenges and benchmarks. Find strategies,
          KPIs, and best practices tailored to your specific vertical.
        </p>
      </div>

      {/* Quick Benchmarks */}
      <section className="mb-12 bg-white rounded-xl border border-slate-200 p-6">
        <h2 className="text-2xl font-bold text-slate-900 mb-4">
          Industry Benchmarks
        </h2>
        <IndustryBenchmarksTable industries={industries} />
      </section>

      {/* Industry Cards */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-slate-900 mb-6">
          Browse by Industry
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {industries.map((industry) => (
            <IndustryCard key={industry.slug} industry={industry} />
          ))}
        </div>
      </section>

      {/* CTA */}
      <CTABanner
        title="Get Industry-Specific Insights"
        description="metricx provides AI-powered recommendations tailored to your industry's unique challenges and benchmarks."
        primaryCTA={{ text: "Start Free Trial", href: "/sign-up" }}
        secondaryCTA={{ text: "See Features", href: "/#features" }}
      />
    </>
  );
}
