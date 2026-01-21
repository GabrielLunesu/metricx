/**
 * Tools Hub Page
 *
 * WHAT: Hub page for all interactive calculator tools
 * WHY: SEO hub for "[metric] calculator" keywords and link-bait content
 *
 * Related files:
 * - content/tools/calculators.json - Calculator configurations
 * - components/tools/ - Calculator components
 */

import Link from "next/link";
import { Breadcrumbs, CTABanner } from "@/components/seo";
import { JsonLd } from "@/components/seo/JsonLd";
import { generateBreadcrumbSchema, generateWebPageSchema } from "@/lib/seo/schemas";
import { allCalculators } from "@/components/tools";
import { Calculator, ArrowRight, TrendingUp, DollarSign, Percent, MousePointerClick, Wallet, Scale } from "lucide-react";

/**
 * Generate metadata for the tools hub page.
 */
export function generateMetadata() {
  return {
    title: "Free Ad Analytics Calculators | ROAS, CPA, CPM, CTR | metricx",
    description: "Free advertising calculators for e-commerce marketers. Calculate ROAS, CPA, CPM, CTR, break-even ROAS, and plan your ad budget instantly.",
    keywords: [
      "roas calculator",
      "cpa calculator",
      "cpm calculator",
      "ctr calculator",
      "ad spend calculator",
      "break even roas calculator",
      "advertising calculator",
    ],
    openGraph: {
      title: "Free Ad Analytics Calculators | metricx",
      description: "Calculate ROAS, CPA, CPM, CTR, and more with our free marketing calculators.",
      type: "website",
      url: "https://www.metricx.ai/tools",
    },
    twitter: {
      card: "summary_large_image",
      title: "Free Ad Analytics Calculators | metricx",
      description: "Calculate your key ad metrics instantly.",
    },
    alternates: {
      canonical: "https://www.metricx.ai/tools",
    },
  };
}

/**
 * Get icon for calculator type.
 */
function getCalculatorIcon(slug) {
  const icons = {
    "roas-calculator": TrendingUp,
    "cpa-calculator": DollarSign,
    "cpm-calculator": Percent,
    "ctr-calculator": MousePointerClick,
    "ad-spend-calculator": Wallet,
    "break-even-roas-calculator": Scale,
  };
  return icons[slug] || Calculator;
}

/**
 * Calculator card component.
 */
function CalculatorCard({ calculator }) {
  const Icon = getCalculatorIcon(calculator.slug);

  return (
    <Link
      href={`/tools/${calculator.slug}`}
      className="group block bg-white border border-slate-200 rounded-xl p-6 hover:border-cyan-300 hover:shadow-lg transition-all"
    >
      <div className="flex items-start justify-between mb-4">
        <div className="p-3 bg-cyan-50 rounded-lg group-hover:bg-cyan-100 transition-colors">
          <Icon className="w-6 h-6 text-cyan-600" />
        </div>
        <ArrowRight className="w-5 h-5 text-slate-300 group-hover:text-cyan-500 transition-colors" />
      </div>
      <h3 className="text-xl font-semibold text-slate-900 group-hover:text-cyan-700 mb-2">
        {calculator.name}
      </h3>
      <p className="text-slate-600">{calculator.description}</p>
    </Link>
  );
}

/**
 * Tools Hub Page Component
 */
export default function ToolsHubPage() {
  const breadcrumbItems = [
    { name: "Home", href: "/" },
    { name: "Tools", href: "/tools" },
  ];

  return (
    <>
      {/* Structured Data */}
      <JsonLd schema={generateBreadcrumbSchema(breadcrumbItems)} />
      <JsonLd
        schema={generateWebPageSchema({
          title: "Free Ad Analytics Calculators",
          description: "Calculate ROAS, CPA, CPM, CTR and more",
          url: "https://www.metricx.ai/tools",
        })}
      />

      {/* Breadcrumbs */}
      <Breadcrumbs items={breadcrumbItems} />

      {/* Hero Section */}
      <div className="mb-12">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-cyan-100 rounded-lg">
            <Calculator className="w-6 h-6 text-cyan-600" />
          </div>
          <span className="text-sm font-medium text-cyan-600">
            Free Tools
          </span>
        </div>
        <h1 className="text-4xl font-bold text-slate-900 mb-4">
          Ad Analytics Calculators
        </h1>
        <p className="text-lg text-slate-600 max-w-3xl">
          Free calculators to help you understand and optimize your advertising performance.
          Calculate ROAS, CPA, CPM, CTR, and plan your ad budget instantly.
        </p>
      </div>

      {/* Calculators Grid */}
      <section className="mb-12">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {allCalculators.map((calculator) => (
            <CalculatorCard key={calculator.slug} calculator={calculator} />
          ))}
        </div>
      </section>

      {/* Why Use Our Calculators */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-slate-900 mb-6">
          Why Use Our Calculators
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-6 bg-slate-50 rounded-xl">
            <h3 className="font-semibold text-slate-900 mb-2">Instant Results</h3>
            <p className="text-slate-600">
              Real-time calculations as you type. No waiting, no page reloads.
            </p>
          </div>
          <div className="p-6 bg-slate-50 rounded-xl">
            <h3 className="font-semibold text-slate-900 mb-2">Industry Benchmarks</h3>
            <p className="text-slate-600">
              See how your metrics compare to industry averages and best performers.
            </p>
          </div>
          <div className="p-6 bg-slate-50 rounded-xl">
            <h3 className="font-semibold text-slate-900 mb-2">Learn & Improve</h3>
            <p className="text-slate-600">
              Each calculator includes explanations, formulas, and optimization tips.
            </p>
          </div>
        </div>
      </section>

      {/* Related Resources */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-slate-900 mb-6">
          Related Resources
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Link
            href="/glossary"
            className="flex items-center justify-between p-4 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <div>
              <div className="font-medium text-slate-900">Ad Analytics Glossary</div>
              <div className="text-sm text-slate-600">Learn what all these metrics mean</div>
            </div>
            <ArrowRight className="w-5 h-5 text-slate-400" />
          </Link>
          <Link
            href="/metrics"
            className="flex items-center justify-between p-4 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <div>
              <div className="font-medium text-slate-900">Metrics Deep Dives</div>
              <div className="text-sm text-slate-600">In-depth guides for each metric</div>
            </div>
            <ArrowRight className="w-5 h-5 text-slate-400" />
          </Link>
        </div>
      </section>

      {/* CTA */}
      <CTABanner
        title="Track All Metrics Automatically"
        description="Stop calculating manually. metricx tracks ROAS, CPA, and all key metrics across Meta, Google, and TikTok in real-time."
        primaryCTA={{ text: "Start Free Trial", href: "/sign-up" }}
        secondaryCTA={{ text: "See Features", href: "/#features" }}
      />
    </>
  );
}
