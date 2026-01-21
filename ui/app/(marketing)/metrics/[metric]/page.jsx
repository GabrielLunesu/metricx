/**
 * Individual Metric Page
 *
 * WHAT: Deep dive page for each advertising metric
 * WHY: SEO page targeting "[metric] guide/explained" keywords
 *
 * Related files:
 * - content/metrics/data.json - Metric data
 * - lib/seo/content-loader.js - Data loading
 */

import { notFound } from "next/navigation";
import Link from "next/link";
import { getMetrics, getMetric } from "@/lib/seo/content-loader";
import { Breadcrumbs, FAQ, CTABanner } from "@/components/seo";
import { JsonLd } from "@/components/seo/JsonLd";
import { generateBreadcrumbSchema, generateFAQSchema, generateArticleSchema } from "@/lib/seo/schemas";
import { Calculator, BookOpen, ArrowRight, Lightbulb, TrendingUp, TrendingDown, Minus } from "lucide-react";

/**
 * Generate static params for all metrics.
 */
export async function generateStaticParams() {
  const metrics = await getMetrics();
  return metrics.map((m) => ({
    metric: m.slug,
  }));
}

/**
 * Generate metadata for metric page.
 */
export async function generateMetadata({ params }) {
  const { metric: slug } = await params;
  const metric = await getMetric(slug);

  if (!metric) {
    return {
      title: "Metric Not Found | metricx",
    };
  }

  return {
    title: `${metric.abbreviation || metric.name} Explained | Formula, Benchmarks & Tips | metricx`,
    description: `Learn everything about ${metric.name} (${metric.abbreviation}). Formula: ${metric.formula}. See benchmarks and optimization tips.`,
    keywords: [
      `${metric.name.toLowerCase()} explained`,
      `${metric.abbreviation?.toLowerCase()} formula`,
      `what is ${metric.abbreviation?.toLowerCase() || metric.name.toLowerCase()}`,
      `${metric.abbreviation?.toLowerCase()} benchmarks`,
    ],
    openGraph: {
      title: `${metric.abbreviation || metric.name} Explained | metricx`,
      description: metric.description,
      type: "article",
      url: `https://www.metricx.ai/metrics/${metric.slug}`,
    },
    alternates: {
      canonical: `https://www.metricx.ai/metrics/${metric.slug}`,
    },
  };
}

/**
 * Benchmark display component.
 */
function Benchmarks({ benchmarks }) {
  if (!benchmarks) return null;

  const getBenchmarkIcon = (key) => {
    if (key === "poor" || key === "negative") return TrendingDown;
    if (key === "excellent" || key === "good") return TrendingUp;
    return Minus;
  };

  const getBenchmarkColor = (key) => {
    const colors = {
      poor: "text-red-600 bg-red-50",
      negative: "text-red-600 bg-red-50",
      average: "text-amber-600 bg-amber-50",
      break_even: "text-amber-600 bg-amber-50",
      good: "text-emerald-600 bg-emerald-50",
      excellent: "text-emerald-700 bg-emerald-50",
    };
    return colors[key] || "text-slate-600 bg-slate-50";
  };

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {Object.entries(benchmarks).map(([key, data]) => {
        if (typeof data !== "object" || !data.value) return null;
        const Icon = getBenchmarkIcon(key);
        const colorClass = getBenchmarkColor(key);

        return (
          <div key={key} className={`p-4 rounded-xl ${colorClass}`}>
            <div className="flex items-center gap-2 mb-1">
              <Icon className="w-4 h-4" />
              <span className="font-semibold capitalize">{key.replace("_", " ")}</span>
            </div>
            <div className="text-2xl font-bold">{data.value}</div>
            <div className="text-sm opacity-75">{data.description}</div>
          </div>
        );
      })}
    </div>
  );
}

/**
 * Formula card component.
 */
function FormulaCard({ formula, example }) {
  return (
    <div className="bg-slate-900 text-white rounded-xl p-6 mb-8">
      <div className="flex items-center gap-2 mb-4">
        <Calculator className="w-5 h-5 text-cyan-400" />
        <h2 className="text-lg font-semibold">Formula</h2>
      </div>
      <div className="font-mono text-xl text-cyan-300 mb-4 p-4 bg-slate-800 rounded-lg">
        {formula}
      </div>
      {example && (
        <div className="text-slate-300">
          <span className="text-slate-400">Example: </span>
          {example}
        </div>
      )}
    </div>
  );
}

/**
 * Improvement tips component.
 */
function ImprovementTips({ tips }) {
  if (!tips || tips.length === 0) return null;

  return (
    <div className="bg-cyan-50 border border-cyan-100 rounded-xl p-6 mb-8">
      <div className="flex items-center gap-2 mb-4">
        <Lightbulb className="w-5 h-5 text-cyan-600" />
        <h3 className="font-semibold text-slate-900">How to Improve</h3>
      </div>
      <ul className="space-y-2">
        {tips.map((tip, i) => (
          <li key={i} className="flex items-start gap-2 text-slate-700">
            <span className="text-cyan-500 mt-1">•</span>
            <span>{tip}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * Related metrics component.
 */
function RelatedMetrics({ slugs, metrics }) {
  const related = slugs?.map((s) => metrics.find((m) => m.slug === s)).filter(Boolean) || [];
  if (related.length === 0) return null;

  return (
    <div className="bg-slate-50 rounded-xl p-6">
      <h3 className="text-lg font-semibold text-slate-900 mb-4">Related Metrics</h3>
      <div className="space-y-2">
        {related.map((m) => (
          <Link
            key={m.slug}
            href={`/metrics/${m.slug}`}
            className="flex items-center justify-between p-3 bg-white rounded-lg border border-slate-200 hover:border-cyan-300 transition-colors group"
          >
            <div>
              <div className="font-medium text-slate-900 group-hover:text-cyan-700">
                {m.abbreviation || m.name}
              </div>
              <div className="text-sm text-slate-500">{m.name}</div>
            </div>
            <ArrowRight className="w-4 h-4 text-slate-300 group-hover:text-cyan-500" />
          </Link>
        ))}
      </div>
    </div>
  );
}

/**
 * Individual Metric Page Component
 */
export default async function MetricPage({ params }) {
  const { metric: slug } = await params;
  const metric = await getMetric(slug);
  const allMetrics = await getMetrics();

  if (!metric) {
    notFound();
  }

  const breadcrumbItems = [
    { name: "Home", href: "/" },
    { name: "Metrics", href: "/metrics" },
    { name: metric.abbreviation || metric.name, href: `/metrics/${metric.slug}` },
  ];

  // Build FAQ items
  const faqItems = metric.faqs?.map((f) => ({
    question: f.question,
    answer: f.answer,
  })) || [];

  // Calculator link if available
  const calculatorSlug = {
    roas: "roas-calculator",
    cpa: "cpa-calculator",
    cpm: "cpm-calculator",
    ctr: "ctr-calculator",
  }[metric.slug];

  return (
    <>
      {/* Structured Data */}
      <JsonLd schema={generateBreadcrumbSchema(breadcrumbItems)} />
      {faqItems.length > 0 && <JsonLd schema={generateFAQSchema(faqItems)} />}
      <JsonLd
        schema={generateArticleSchema({
          title: `${metric.abbreviation || metric.name} Explained`,
          description: metric.description,
          url: `https://www.metricx.ai/metrics/${metric.slug}`,
          datePublished: "2024-01-01",
          dateModified: new Date().toISOString().split("T")[0],
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
              <Link href="/metrics" className="hover:text-cyan-600">
                Metrics
              </Link>
              <span>/</span>
              <span className="capitalize">{metric.category}</span>
            </div>
            <h1 className="text-4xl font-bold text-slate-900 mb-2">
              {metric.abbreviation || metric.name}
            </h1>
            {metric.abbreviation && (
              <p className="text-xl text-slate-600">{metric.name}</p>
            )}
          </header>

          {/* Description */}
          <div className="prose prose-slate max-w-none mb-8">
            <p className="text-lg">{metric.description}</p>
          </div>

          {/* Calculator Link */}
          {calculatorSlug && (
            <Link
              href={`/tools/${calculatorSlug}`}
              className="flex items-center gap-3 p-4 bg-cyan-50 border border-cyan-200 rounded-xl hover:bg-cyan-100 transition-colors group mb-8"
            >
              <div className="p-2 bg-cyan-100 rounded-lg group-hover:bg-cyan-200">
                <Calculator className="w-5 h-5 text-cyan-600" />
              </div>
              <div className="flex-1">
                <div className="font-medium text-slate-900">
                  Calculate Your {metric.abbreviation || metric.name}
                </div>
                <div className="text-sm text-slate-600">
                  Use our free calculator to get instant results
                </div>
              </div>
              <ArrowRight className="w-5 h-5 text-cyan-500" />
            </Link>
          )}

          {/* Formula */}
          {metric.formula && (
            <FormulaCard formula={metric.formula} example={metric.formulaExample} />
          )}

          {/* Benchmarks */}
          {metric.benchmarks && (
            <section className="mb-8">
              <h2 className="text-2xl font-bold text-slate-900 mb-4">Benchmarks</h2>
              <Benchmarks benchmarks={metric.benchmarks} />
            </section>
          )}

          {/* Improvement Tips */}
          <ImprovementTips tips={metric.improvementTips} />

          {/* metricx Feature */}
          {metric.metricxFeature && (
            <div className="flex items-start gap-3 p-4 bg-gradient-to-r from-cyan-500 to-cyan-600 text-white rounded-xl mb-8">
              <Lightbulb className="w-5 h-5 flex-shrink-0 mt-0.5" />
              <div>
                <div className="font-medium mb-1">How metricx Helps</div>
                <div className="text-cyan-50 text-sm">{metric.metricxFeature}</div>
              </div>
            </div>
          )}

          {/* FAQs */}
          {faqItems.length > 0 && (
            <section className="mb-8">
              <h2 className="text-2xl font-bold text-slate-900 mb-4">
                Frequently Asked Questions
              </h2>
              <FAQ items={faqItems} />
            </section>
          )}

          {/* CTA */}
          <CTABanner
            title={`Track ${metric.abbreviation || metric.name} Automatically`}
            description={`metricx tracks ${metric.abbreviation || metric.name} and all key metrics across Meta, Google, and TikTok in one dashboard.`}
            primaryCTA={{ text: "Start Free Trial", href: "/sign-up" }}
            secondaryCTA={{ text: "Learn More", href: "/#features" }}
            variant="inline"
          />
        </div>

        {/* Sidebar */}
        <aside className="space-y-6">
          {/* Related Metrics */}
          <RelatedMetrics slugs={metric.relatedMetrics} metrics={allMetrics} />

          {/* Quick Links */}
          <div className="bg-slate-50 rounded-xl p-6">
            <h3 className="text-lg font-semibold text-slate-900 mb-4">
              Quick Links
            </h3>
            <div className="space-y-2">
              <Link
                href="/tools"
                className="flex items-center gap-2 text-slate-600 hover:text-cyan-600"
              >
                <Calculator className="w-4 h-4" />
                Free Calculators
              </Link>
              <Link
                href="/glossary"
                className="flex items-center gap-2 text-slate-600 hover:text-cyan-600"
              >
                <BookOpen className="w-4 h-4" />
                Glossary
              </Link>
            </div>
          </div>
        </aside>
      </div>
    </>
  );
}
