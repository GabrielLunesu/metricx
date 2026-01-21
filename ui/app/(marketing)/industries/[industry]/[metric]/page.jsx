/**
 * Industry × Metric Combination Page
 *
 * WHAT: Long-tail SEO pages for "[Industry] [Metric]" searches
 * WHY: Captures high-intent searches like "fashion ecommerce ROAS benchmarks"
 *
 * Generates 2,160+ pages (108 industries × 20 metrics)
 *
 * Related files:
 * - content/industries/data.json - Industry data
 * - content/metrics/data.json - Metric definitions
 * - lib/seo/content-loader.js - Content loading utilities
 */

import { notFound } from "next/navigation";
import Link from "next/link";
import {
  getIndustries,
  getIndustry,
  getMetrics,
  getMetric,
} from "@/lib/seo/content-loader";
import { JsonLd } from "@/components/seo/JsonLd";
import { Breadcrumbs } from "@/components/seo/Breadcrumbs";
import { FAQ } from "@/components/seo/FAQ";
import { CTABanner } from "@/components/seo/CTABanner";
import {
  Calculator,
  TrendingUp,
  Target,
  Lightbulb,
  ArrowRight,
  CheckCircle,
  BarChart3,
  Building2,
} from "lucide-react";

/**
 * Generate all industry × metric combinations for static generation.
 */
export async function generateStaticParams() {
  const [industries, metrics] = await Promise.all([
    getIndustries(),
    getMetrics(),
  ]);

  const params = [];
  for (const industry of industries) {
    for (const metric of metrics) {
      params.push({
        industry: industry.slug,
        metric: metric.slug,
      });
    }
  }

  return params;
}

/**
 * Generate unique metadata for each industry × metric combination.
 */
export async function generateMetadata({ params }) {
  const [industry, metric] = await Promise.all([
    getIndustry(params.industry),
    getMetric(params.metric),
  ]);

  if (!industry || !metric) {
    return { title: "Not Found" };
  }

  const title = `${industry.name} ${metric.abbreviation || metric.name} Guide | Benchmarks & Tips | metricx`;
  const description = `Complete guide to ${metric.name} (${metric.abbreviation}) for ${industry.name.toLowerCase()} businesses. Industry-specific benchmarks, optimization tips, and strategies.`;

  return {
    title,
    description,
    keywords: [
      `${industry.name.toLowerCase()} ${metric.abbreviation}`,
      `${metric.abbreviation} ${industry.name.toLowerCase()}`,
      `${industry.name.toLowerCase()} ${metric.abbreviation} benchmarks`,
      `good ${metric.abbreviation} for ${industry.name.toLowerCase()}`,
      `${industry.name.toLowerCase()} ad metrics`,
    ],
    openGraph: {
      title,
      description,
      type: "article",
      url: `https://www.metricx.ai/industries/${params.industry}/${params.metric}`,
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
    },
    alternates: {
      canonical: `https://www.metricx.ai/industries/${params.industry}/${params.metric}`,
    },
  };
}

/**
 * Generate industry-specific benchmarks based on industry characteristics.
 */
function getIndustryBenchmarks(metric, industry) {
  // Industry category multipliers for benchmark adjustments
  const categoryMultipliers = {
    ecommerce: { roas: 1.0, cpa: 1.0, ctr: 0.95, cpm: 1.1 },
    saas: { roas: 0.8, cpa: 1.3, ctr: 0.9, cpm: 0.9 },
    services: { roas: 1.1, cpa: 0.9, ctr: 1.1, cpm: 0.85 },
    "b2b": { roas: 0.7, cpa: 1.5, ctr: 0.8, cpm: 1.2 },
    healthcare: { roas: 0.9, cpa: 1.2, ctr: 0.85, cpm: 1.3 },
    finance: { roas: 0.85, cpa: 1.4, ctr: 0.75, cpm: 1.5 },
    default: { roas: 1.0, cpa: 1.0, ctr: 1.0, cpm: 1.0 },
  };

  const category = (industry.category || "default").toLowerCase();
  const multipliers = categoryMultipliers[category] || categoryMultipliers.default;
  const metricKey = metric.slug.toLowerCase().replace(/-/g, "");
  const multiplier = multipliers[metricKey] || 1.0;

  if (metric.benchmarks) {
    const description = multiplier > 1
      ? `${industry.name} typically sees ${Math.round((multiplier - 1) * 100)}% higher ${metric.abbreviation} than average.`
      : multiplier < 1
        ? `${industry.name} typically sees ${Math.round((1 - multiplier) * 100)}% lower ${metric.abbreviation} than average.`
        : `${industry.name} generally aligns with standard ${metric.abbreviation} benchmarks.`;

    return {
      benchmarks: metric.benchmarks,
      multiplier,
      industryNote: description,
    };
  }

  return null;
}

/**
 * Generate industry-specific optimization tips.
 */
function getIndustrySpecificTips(metric, industry) {
  const baseTips = metric.improvementTips || [];

  const contextualizedTips = baseTips.slice(0, 3).map((tip, index) => ({
    tip,
    context: `Critical for ${industry.name.toLowerCase()} success.`,
    priority: index + 1,
  }));

  const industryTips = [
    {
      tip: `Study ${industry.name.toLowerCase()} competitor ad strategies`,
      context: "Analyze what's working for successful brands in your space.",
      priority: 4,
    },
    {
      tip: `Target ${industry.name.toLowerCase()}-specific audiences`,
      context: `Use interest and behavior targeting relevant to ${industry.name.toLowerCase()} customers.`,
      priority: 5,
    },
    {
      tip: `Leverage ${industry.name.toLowerCase()} seasonal trends`,
      context: "Time your campaigns around key buying periods in your industry.",
      priority: 6,
    },
  ];

  return [...contextualizedTips, ...industryTips];
}

/**
 * Generate FAQs specific to this industry × metric combination.
 */
function generateCombinationFAQs(metric, industry) {
  return [
    {
      question: `What is a good ${metric.abbreviation || metric.name} for ${industry.name.toLowerCase()}?`,
      answer: `For ${industry.name.toLowerCase()} businesses, a good ${metric.abbreviation || metric.name} is typically ${metric.benchmarks?.good?.value || "above the industry average"}. However, this varies based on your specific business model, margins, and competitive landscape. Track your own performance over time with metricx to establish personalized benchmarks.`,
    },
    {
      question: `How do I improve ${metric.abbreviation || metric.name} for my ${industry.name.toLowerCase()} ads?`,
      answer: `To improve ${metric.abbreviation || metric.name} in ${industry.name.toLowerCase()}: 1) Refine audience targeting to reach high-intent ${industry.name.toLowerCase()} customers, 2) Test ad creatives that resonate with your market, 3) Optimize landing pages for conversions, 4) Analyze competitor strategies. metricx provides AI-powered recommendations specific to your campaigns.`,
    },
    {
      question: `What ${metric.abbreviation || metric.name} should ${industry.name.toLowerCase()} businesses target?`,
      answer: `${industry.name} businesses should aim for ${metric.abbreviation || metric.name} of ${metric.benchmarks?.good?.value || "above average"} or better. New businesses might see lower initial performance while optimizing. Established brands often achieve ${metric.benchmarks?.excellent?.value || "excellent"} performance with refined campaigns.`,
    },
    {
      question: `How does metricx help ${industry.name.toLowerCase()} businesses track ${metric.abbreviation || metric.name}?`,
      answer: `metricx provides real-time ${metric.abbreviation || metric.name} tracking for ${industry.name.toLowerCase()} businesses across Meta, Google, and TikTok ads. Our AI Copilot analyzes your specific performance and provides actionable recommendations to improve your metrics.`,
    },
  ];
}

export default async function IndustryMetricPage({ params }) {
  const [industry, metric, allIndustries, allMetrics] = await Promise.all([
    getIndustry(params.industry),
    getMetric(params.metric),
    getIndustries(),
    getMetrics(),
  ]);

  if (!industry || !metric) {
    notFound();
  }

  const benchmarkData = getIndustryBenchmarks(metric, industry);
  const tips = getIndustrySpecificTips(metric, industry);
  const faqs = generateCombinationFAQs(metric, industry);

  // Get related pages for internal linking
  const relatedIndustries = allIndustries
    .filter((i) => i.slug !== industry.slug && i.category === industry.category)
    .slice(0, 4);
  const relatedMetrics = allMetrics
    .filter((m) => m.slug !== metric.slug)
    .slice(0, 4);

  const breadcrumbItems = [
    { name: "Home", href: "/" },
    { name: "Industries", href: "/industries" },
    { name: industry.name, href: `/industries/${industry.slug}` },
    { name: metric.abbreviation || metric.name },
  ];

  // JSON-LD structured data
  const articleSchema = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: `${industry.name} ${metric.abbreviation || metric.name} Guide`,
    description: `Complete guide to ${metric.name} for ${industry.name.toLowerCase()} businesses.`,
    author: {
      "@type": "Organization",
      name: "metricx",
      url: "https://www.metricx.ai",
    },
    publisher: {
      "@type": "Organization",
      name: "metricx",
      url: "https://www.metricx.ai",
    },
    mainEntityOfPage: {
      "@type": "WebPage",
      "@id": `https://www.metricx.ai/industries/${params.industry}/${params.metric}`,
    },
  };

  const faqSchema = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: faqs.map((faq) => ({
      "@type": "Question",
      name: faq.question,
      acceptedAnswer: {
        "@type": "Answer",
        text: faq.answer,
      },
    })),
  };

  return (
    <>
      <JsonLd schema={articleSchema} />
      <JsonLd schema={faqSchema} />

      <div className="min-h-screen bg-white">
        {/* Breadcrumbs */}
        <div className="border-b border-gray-100">
          <div className="max-w-4xl mx-auto px-4 py-4">
            <Breadcrumbs items={breadcrumbItems} />
          </div>
        </div>

        {/* Hero Section */}
        <section className="bg-gradient-to-b from-gray-50 to-white border-b border-gray-100">
          <div className="max-w-4xl mx-auto px-4 py-16">
            <div className="flex items-center gap-3 mb-4">
              <span className="inline-flex items-center gap-2 px-3 py-1 bg-cyan-50 text-cyan-700 rounded-full text-sm font-medium">
                <Building2 className="w-4 h-4" />
                {industry.name}
              </span>
              <span className="text-gray-400">×</span>
              <span className="inline-flex items-center gap-2 px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-sm font-medium">
                <BarChart3 className="w-4 h-4" />
                {metric.abbreviation || metric.name}
              </span>
            </div>

            <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-6">
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-500 to-blue-600">
                {industry.name}
              </span>{" "}
              {metric.abbreviation || metric.name} Guide
            </h1>

            <p className="text-xl text-gray-600 mb-8 leading-relaxed">
              Everything you need to know about {metric.name} ({metric.abbreviation}) for{" "}
              {industry.name.toLowerCase()} businesses. Benchmarks, optimization strategies,
              and expert insights.
            </p>

            <div className="flex flex-wrap gap-4">
              <Link
                href="/sign-up"
                className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-semibold rounded-full hover:opacity-90 transition-opacity"
              >
                Track Your {metric.abbreviation || metric.name}
                <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                href={`/tools/${metric.slug}-calculator`}
                className="inline-flex items-center gap-2 px-6 py-3 bg-white border border-gray-200 text-gray-700 font-semibold rounded-full hover:bg-gray-50 transition-colors"
              >
                <Calculator className="w-4 h-4" />
                {metric.abbreviation || metric.name} Calculator
              </Link>
            </div>
          </div>
        </section>

        {/* Main Content */}
        <article className="max-w-4xl mx-auto px-4 py-16">
          {/* What is Section */}
          <section className="mb-16">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center gap-3">
              <Target className="w-6 h-6 text-blue-500" />
              What is {metric.abbreviation || metric.name}?
            </h2>
            <p className="text-gray-600 leading-relaxed mb-6">{metric.description}</p>

            {metric.formula && (
              <div className="bg-gray-50 rounded-xl p-6 border border-gray-200">
                <h3 className="font-semibold text-gray-900 mb-2">Formula</h3>
                <code className="text-lg font-mono text-blue-600">{metric.formula}</code>
                {metric.formulaExample && (
                  <p className="text-sm text-gray-500 mt-2">{metric.formulaExample}</p>
                )}
              </div>
            )}
          </section>

          {/* Industry-Specific Benchmarks */}
          <section className="mb-16">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center gap-3">
              <TrendingUp className="w-6 h-6 text-cyan-500" />
              {metric.abbreviation || metric.name} Benchmarks for {industry.name}
            </h2>

            {benchmarkData && (
              <>
                <p className="text-gray-600 mb-6">{benchmarkData.industryNote}</p>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                  {Object.entries(benchmarkData.benchmarks).map(
                    ([level, data]) =>
                      data?.value && (
                        <div
                          key={level}
                          className={`p-4 rounded-xl border ${
                            level === "excellent"
                              ? "bg-green-50 border-green-200"
                              : level === "good"
                                ? "bg-blue-50 border-blue-200"
                                : level === "average"
                                  ? "bg-yellow-50 border-yellow-200"
                                  : "bg-red-50 border-red-200"
                          }`}
                        >
                          <div className="text-sm font-medium text-gray-600 capitalize mb-1">
                            {level}
                          </div>
                          <div className="text-xl font-bold text-gray-900">{data.value}</div>
                          {data.description && (
                            <div className="text-xs text-gray-500 mt-1">{data.description}</div>
                          )}
                        </div>
                      )
                  )}
                </div>
              </>
            )}

            <div className="bg-gradient-to-r from-cyan-50 to-blue-50 rounded-xl p-6 border border-cyan-100">
              <p className="text-gray-700">
                <strong>Track your benchmarks:</strong> Use metricx to see how your{" "}
                {industry.name.toLowerCase()} business compares to these benchmarks in real-time.
                Our AI identifies opportunities to improve.
              </p>
            </div>
          </section>

          {/* Optimization Tips */}
          <section className="mb-16">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center gap-3">
              <Lightbulb className="w-6 h-6 text-yellow-500" />
              How to Improve {metric.abbreviation || metric.name} for {industry.name}
            </h2>

            <div className="space-y-4">
              {tips.map((item, index) => (
                <div
                  key={index}
                  className="flex gap-4 p-4 bg-white rounded-xl border border-gray-200 hover:border-cyan-200 transition-colors"
                >
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-cyan-100 rounded-full flex items-center justify-center">
                      <CheckCircle className="w-5 h-5 text-cyan-600" />
                    </div>
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">{item.tip}</h3>
                    <p className="text-sm text-gray-500 mt-1">{item.context}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* FAQs */}
          <section className="mb-16">
            <h2 className="text-2xl font-bold text-gray-900 mb-6">
              Frequently Asked Questions
            </h2>
            <FAQ items={faqs} />
          </section>

          {/* CTA Banner */}
          <CTABanner
            title={`Track ${metric.abbreviation || metric.name} for Your ${industry.name} Business`}
            description={`Get real-time ${metric.abbreviation || metric.name} tracking with AI-powered optimization for ${industry.name.toLowerCase()} brands.`}
            primaryCTA={{ text: "Start Free Trial", href: "/sign-up" }}
            secondaryCTA={{ text: "See Product", href: "/" }}
            variant="gradient"
          />

          {/* Related Content */}
          <section className="mt-16">
            <h2 className="text-xl font-bold text-gray-900 mb-6">Related Resources</h2>

            <div className="grid md:grid-cols-2 gap-6">
              {/* Other Metrics for This Industry */}
              <div>
                <h3 className="font-semibold text-gray-700 mb-3">
                  More {industry.name} Guides
                </h3>
                <div className="space-y-2">
                  {relatedMetrics.map((m) => (
                    <Link
                      key={m.slug}
                      href={`/industries/${industry.slug}/${m.slug}`}
                      className="block p-3 bg-gray-50 rounded-lg hover:bg-cyan-50 transition-colors"
                    >
                      <span className="font-medium text-gray-900">{industry.name}</span>
                      <span className="text-gray-500"> {m.abbreviation || m.name} Guide</span>
                    </Link>
                  ))}
                </div>
              </div>

              {/* Same Metric for Other Industries */}
              <div>
                <h3 className="font-semibold text-gray-700 mb-3">
                  {metric.abbreviation || metric.name} for Other Industries
                </h3>
                <div className="space-y-2">
                  {relatedIndustries.map((i) => (
                    <Link
                      key={i.slug}
                      href={`/industries/${i.slug}/${metric.slug}`}
                      className="block p-3 bg-gray-50 rounded-lg hover:bg-blue-50 transition-colors"
                    >
                      <span className="font-medium text-gray-900">{i.name}</span>
                      <span className="text-gray-500">
                        {" "}
                        {metric.abbreviation || metric.name} Guide
                      </span>
                    </Link>
                  ))}
                </div>
              </div>
            </div>
          </section>
        </article>
      </div>
    </>
  );
}
