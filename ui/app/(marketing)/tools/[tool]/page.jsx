/**
 * Individual Calculator Tool Page
 *
 * WHAT: Dynamic page for each calculator tool
 * WHY: SEO pages targeting "[metric] calculator" keywords
 *
 * Related files:
 * - components/tools/ - Calculator components
 * - content/tools/calculators.json - Calculator configurations
 */

import { notFound } from "next/navigation";
import Link from "next/link";
import { Breadcrumbs, FAQ, CTABanner } from "@/components/seo";
import { JsonLd } from "@/components/seo/JsonLd";
import { generateBreadcrumbSchema, generateHowToSchema } from "@/lib/seo/schemas";
import {
  ROASCalculator,
  roasCalculatorData,
  CPACalculator,
  cpaCalculatorData,
  CPMCalculator,
  cpmCalculatorData,
  CTRCalculator,
  ctrCalculatorData,
  AdSpendPlanner,
  adSpendPlannerData,
  BreakEvenCalculator,
  breakEvenCalculatorData,
  CalculatorLayout,
  allCalculators,
} from "@/components/tools";
import { ArrowRight, Calculator } from "lucide-react";

/**
 * Calculator configuration mapping.
 */
const calculatorConfig = {
  "roas-calculator": {
    Component: ROASCalculator,
    data: roasCalculatorData,
  },
  "cpa-calculator": {
    Component: CPACalculator,
    data: cpaCalculatorData,
  },
  "cpm-calculator": {
    Component: CPMCalculator,
    data: cpmCalculatorData,
  },
  "ctr-calculator": {
    Component: CTRCalculator,
    data: ctrCalculatorData,
  },
  "ad-spend-calculator": {
    Component: AdSpendPlanner,
    data: adSpendPlannerData,
  },
  "break-even-roas-calculator": {
    Component: BreakEvenCalculator,
    data: breakEvenCalculatorData,
  },
};

/**
 * Generate static params for all calculators.
 */
export function generateStaticParams() {
  return allCalculators.map((calc) => ({
    tool: calc.slug,
  }));
}

/**
 * Generate metadata for calculator page.
 */
export async function generateMetadata({ params }) {
  const { tool } = await params;
  const config = calculatorConfig[tool];

  if (!config || !config.data) {
    return {
      title: "Calculator Not Found | metricx",
    };
  }

  const { data } = config;
  const title = data.title || "Calculator";
  const titleBase = title.replace(" Calculator", "");

  return {
    title: `Free ${title} | Calculate ${titleBase} Instantly | metricx`,
    description: data.description,
    keywords: [
      title.toLowerCase(),
      `${title.toLowerCase()} free`,
      `calculate ${titleBase.toLowerCase()}`,
      `${titleBase.toLowerCase()} formula`,
    ],
    openGraph: {
      title: `Free ${title} | metricx`,
      description: data.description,
      type: "website",
      url: `https://www.metricx.ai/tools/${data.slug}`,
    },
    twitter: {
      card: "summary",
      title: `Free ${title} | metricx`,
      description: data.description,
    },
    alternates: {
      canonical: `https://www.metricx.ai/tools/${data.slug}`,
    },
  };
}

/**
 * Related tools component.
 */
function RelatedTools({ currentSlug, relatedTools }) {
  const tools = relatedTools || allCalculators.filter((t) => t.slug !== currentSlug).slice(0, 3);

  return (
    <div className="bg-slate-50 rounded-xl p-6">
      <h3 className="text-lg font-semibold text-slate-900 mb-4">Related Tools</h3>
      <div className="space-y-3">
        {tools.map((tool) => (
          <Link
            key={tool.slug}
            href={`/tools/${tool.slug}`}
            className="flex items-center justify-between p-3 bg-white rounded-lg border border-slate-200 hover:border-cyan-300 transition-colors group"
          >
            <div>
              <div className="font-medium text-slate-900 group-hover:text-cyan-700">
                {tool.name}
              </div>
              <div className="text-sm text-slate-500">{tool.description}</div>
            </div>
            <ArrowRight className="w-4 h-4 text-slate-300 group-hover:text-cyan-500" />
          </Link>
        ))}
      </div>
    </div>
  );
}

/**
 * Individual Calculator Tool Page Component
 */
export default async function CalculatorToolPage({ params }) {
  const { tool } = await params;
  const config = calculatorConfig[tool];

  if (!config || !config.data) {
    notFound();
  }

  const { Component, data } = config;
  const title = data.title || "Calculator";
  const titleBase = title.replace(" Calculator", "");

  const breadcrumbItems = [
    { name: "Home", href: "/" },
    { name: "Tools", href: "/tools" },
    { name: title, href: `/tools/${data.slug}` },
  ];

  // Get related tools (either from data or defaults)
  // Handle both slug strings and objects with slug property
  const relatedTools = data.relatedTools?.map((item) => {
    const slug = typeof item === "string" ? item : item.slug;
    return allCalculators.find((c) => c.slug === slug);
  }).filter(Boolean) || allCalculators.filter((c) => c.slug !== tool).slice(0, 3);

  return (
    <>
      {/* Structured Data */}
      <JsonLd schema={generateBreadcrumbSchema(breadcrumbItems)} />
      {data.howToSteps && (
        <JsonLd
          schema={generateHowToSchema({
            name: `How to Use the ${title}`,
            description: data.description,
            steps: data.howToSteps,
          })}
        />
      )}

      {/* Breadcrumbs */}
      <Breadcrumbs items={breadcrumbItems} />

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Calculator Column */}
        <div className="lg:col-span-2">
          {/* Header */}
          <header className="mb-8">
            <div className="flex items-center gap-2 text-sm text-slate-500 mb-2">
              <Link href="/tools" className="hover:text-cyan-600">
                Tools
              </Link>
              <span>/</span>
              <span>Calculator</span>
            </div>
            <h1 className="text-4xl font-bold text-slate-900 mb-4">
              {title}
            </h1>
            <p className="text-lg text-slate-600">{data.description}</p>
          </header>

          {/* Calculator */}
          <div className="bg-white border border-slate-200 rounded-xl p-6 mb-8">
            <Component />
          </div>

          {/* How to Use */}
          {data.howToSteps && data.howToSteps.length > 0 && (
            <section className="mb-8">
              <h2 className="text-2xl font-bold text-slate-900 mb-4">
                How to Use This Calculator
              </h2>
              <div className="space-y-4">
                {data.howToSteps.map((step, index) => (
                  <div key={index} className="flex gap-4">
                    <div className="w-8 h-8 flex items-center justify-center bg-cyan-100 text-cyan-700 font-semibold rounded-full flex-shrink-0">
                      {index + 1}
                    </div>
                    <div>
                      <h3 className="font-medium text-slate-900">{step.name}</h3>
                      <p className="text-slate-600">{step.text}</p>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* FAQs */}
          {data.faqs && data.faqs.length > 0 && (
            <section className="mb-8">
              <h2 className="text-2xl font-bold text-slate-900 mb-4">
                Frequently Asked Questions
              </h2>
              <FAQ items={data.faqs} />
            </section>
          )}

          {/* CTA */}
          <CTABanner
            title="Track Automatically with metricx"
            description={`Stop calculating manually. metricx tracks ${titleBase} and all key metrics across Meta, Google, and TikTok in real-time.`}
            primaryCTA={{ text: "Start Free Trial", href: "/sign-up" }}
            secondaryCTA={{ text: "See Features", href: "/#features" }}
            variant="inline"
          />
        </div>

        {/* Sidebar */}
        <aside className="space-y-6">
          {/* Related Tools */}
          <RelatedTools currentSlug={tool} relatedTools={relatedTools} />

          {/* Glossary Link */}
          <div className="bg-slate-50 rounded-xl p-6">
            <h3 className="text-lg font-semibold text-slate-900 mb-4">
              Learn More
            </h3>
            <div className="space-y-3">
              <Link
                href="/glossary"
                className="flex items-center gap-2 text-slate-600 hover:text-cyan-600"
              >
                <Calculator className="w-4 h-4" />
                Ad Analytics Glossary
              </Link>
              <Link
                href="/metrics"
                className="flex items-center gap-2 text-slate-600 hover:text-cyan-600"
              >
                <Calculator className="w-4 h-4" />
                Metrics Deep Dives
              </Link>
            </div>
          </div>

          {/* All Tools Link */}
          <Link
            href="/tools"
            className="flex items-center justify-center gap-2 p-4 bg-cyan-50 text-cyan-700 rounded-xl hover:bg-cyan-100 transition-colors font-medium"
          >
            View All Calculators
            <ArrowRight className="w-4 h-4" />
          </Link>
        </aside>
      </div>
    </>
  );
}
