/**
 * Platform × Metric Combination Page
 *
 * WHAT: Long-tail SEO pages for "[Platform] [Metric]" searches
 * WHY: Captures high-intent searches like "Meta Ads ROAS tracking"
 *
 * Generates 160+ pages (8 platforms × 20 metrics)
 *
 * Related files:
 * - content/platforms/data.json - Platform data
 * - content/metrics/data.json - Metric definitions
 * - lib/seo/content-loader.js - Content loading utilities
 */

import { notFound } from "next/navigation";
import Link from "next/link";
import {
  getPlatforms,
  getPlatform,
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
  Laptop,
  AlertTriangle,
  Eye,
  Settings,
} from "lucide-react";

/**
 * Generate all platform × metric combinations for static generation.
 */
export async function generateStaticParams() {
  const [platforms, metrics] = await Promise.all([
    getPlatforms(),
    getMetrics(),
  ]);

  const params = [];
  for (const platform of platforms) {
    for (const metric of metrics) {
      params.push({
        platform: platform.slug,
        metric: metric.slug,
      });
    }
  }

  return params;
}

/**
 * Generate unique metadata for each platform × metric combination.
 */
export async function generateMetadata({ params }) {
  const [platform, metric] = await Promise.all([
    getPlatform(params.platform),
    getMetric(params.metric),
  ]);

  if (!platform || !metric) {
    return { title: "Not Found" };
  }

  const title = `${platform.name} ${metric.abbreviation || metric.name} Guide | How to Track & Optimize | metricx`;
  const description = `Learn how to track and optimize ${metric.name} (${metric.abbreviation}) in ${platform.name}. Step-by-step guide, benchmarks, and optimization tips.`;

  return {
    title,
    description,
    keywords: [
      `${platform.name} ${metric.abbreviation}`,
      `${metric.abbreviation} ${platform.name}`,
      `track ${metric.abbreviation} ${platform.name}`,
      `${platform.name} ${metric.name}`,
      `how to see ${metric.abbreviation} in ${platform.name}`,
    ],
    openGraph: {
      title,
      description,
      type: "article",
      url: `https://www.metricx.ai/platforms/${params.platform}/${params.metric}`,
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
    },
    alternates: {
      canonical: `https://www.metricx.ai/platforms/${params.platform}/${params.metric}`,
    },
  };
}

/**
 * Get platform-specific tracking steps for a metric.
 */
function getPlatformTrackingSteps(metric, platform) {
  const platformSteps = {
    "meta-ads": [
      {
        step: "Open Meta Ads Manager",
        detail: "Go to business.facebook.com and select your ad account.",
      },
      {
        step: "Navigate to Campaigns View",
        detail: "Click on Campaigns in the left navigation to see your active campaigns.",
      },
      {
        step: "Customize Your Columns",
        detail: `Click 'Columns' dropdown and select 'Customize Columns'. Search for '${metric.name}' or related metrics.`,
      },
      {
        step: `Add ${metric.abbreviation || metric.name} to View`,
        detail: `Check the box next to ${metric.abbreviation || metric.name} and click 'Apply'. The metric will now appear in your dashboard.`,
      },
      {
        step: "Save Column Preset",
        detail: "Save this column configuration as a preset for quick access next time.",
      },
    ],
    "google-ads": [
      {
        step: "Sign in to Google Ads",
        detail: "Go to ads.google.com and access your account.",
      },
      {
        step: "Go to Campaigns Section",
        detail: "Select 'Campaigns' from the left menu to view your campaigns.",
      },
      {
        step: "Modify Columns",
        detail: `Click the columns icon and select 'Modify columns'. Search for '${metric.name}'.`,
      },
      {
        step: `Add ${metric.abbreviation || metric.name} Column`,
        detail: `Find and add ${metric.abbreviation || metric.name} to your column set. Click 'Apply'.`,
      },
      {
        step: "Set as Default View",
        detail: "Save this column set for easy access to your key metrics.",
      },
    ],
    "tiktok-ads": [
      {
        step: "Access TikTok Ads Manager",
        detail: "Go to ads.tiktok.com and log into your business account.",
      },
      {
        step: "Open Campaign Dashboard",
        detail: "Navigate to 'Campaign' in the main menu.",
      },
      {
        step: "Customize Table View",
        detail: `Click the column settings icon and look for '${metric.name}' options.`,
      },
      {
        step: `Enable ${metric.abbreviation || metric.name} Display`,
        detail: `Toggle on ${metric.abbreviation || metric.name} to add it to your dashboard view.`,
      },
      {
        step: "Save Configuration",
        detail: "Your column preferences will be saved for future sessions.",
      },
    ],
    shopify: [
      {
        step: "Open Shopify Admin",
        detail: "Go to your Shopify admin dashboard at yourstore.myshopify.com/admin.",
      },
      {
        step: "Navigate to Analytics",
        detail: "Click on 'Analytics' in the left sidebar.",
      },
      {
        step: "View Reports Section",
        detail: `Look for marketing or sales reports that include ${metric.abbreviation || metric.name} data.`,
      },
      {
        step: "Check Marketing Channel Performance",
        detail: "Review the Marketing section to see channel-specific metrics.",
      },
      {
        step: "Export for Analysis",
        detail: "Export data to analyze trends and compare with ad platform data.",
      },
    ],
  };

  const defaultSteps = [
    {
      step: "Access Your Dashboard",
      detail: `Log into ${platform.name} and navigate to your main dashboard.`,
    },
    {
      step: "Find Reporting Section",
      detail: "Look for Analytics, Reports, or Performance in the navigation.",
    },
    {
      step: "Customize Metrics View",
      detail: `Find the column or metric customization options and add ${metric.abbreviation || metric.name}.`,
    },
    {
      step: "Apply and Save",
      detail: "Save your configuration for quick access in the future.",
    },
  ];

  return platformSteps[platform.slug] || defaultSteps;
}

/**
 * Get platform-specific optimization tips.
 */
function getPlatformOptimizationTips(metric, platform) {
  const baseTips = metric.improvementTips || [];

  const platformContext = {
    "meta-ads": "Meta's algorithm rewards engaging content with lower costs.",
    "google-ads": "Quality Score directly impacts your costs - focus on relevance.",
    "tiktok-ads": "Native, authentic content performs best on TikTok.",
    shopify: "Optimize your store's conversion funnel alongside ad campaigns.",
  };

  const context = platformContext[platform.slug] || "Platform-specific optimization can significantly improve results.";

  return baseTips.slice(0, 4).map((tip) => ({
    tip,
    context,
  }));
}

/**
 * Get important considerations for this platform.
 */
function getPlatformConsiderations(metric, platform) {
  const considerations = [
    {
      title: "Attribution Model Differences",
      description: `${platform.name} uses its own attribution model that may differ from other platforms or Shopify data. A single conversion might be claimed by multiple platforms.`,
      type: "warning",
    },
    {
      title: "Data Reporting Delays",
      description: `${platform.name} ${metric.abbreviation || metric.name} data may take 24-72 hours to fully populate. Recent data is often incomplete.`,
      type: "info",
    },
    {
      title: "iOS 14+ Privacy Impact",
      description: "Apple's privacy changes have affected tracking accuracy. Consider server-side tracking (Conversions API) for better data.",
      type: "warning",
    },
  ];

  return considerations;
}

/**
 * Generate FAQs specific to this platform × metric combination.
 */
function generatePlatformFAQs(metric, platform) {
  return [
    {
      question: `How do I find ${metric.abbreviation || metric.name} in ${platform.name}?`,
      answer: `In ${platform.name}, ${metric.abbreviation || metric.name} can be found by customizing your column view in the campaign dashboard. Navigate to your campaigns, click on column settings, and add ${metric.abbreviation || metric.name} to your view. You may need to search for the exact metric name.`,
    },
    {
      question: `What's a good ${metric.abbreviation || metric.name} for ${platform.name} ads?`,
      answer: `Good ${metric.abbreviation || metric.name} for ${platform.name} varies by industry and campaign objective. Generally, ${metric.benchmarks?.good?.value || "above-average"} is considered solid performance. However, your specific targets should be based on your margins and business model.`,
    },
    {
      question: `Why does my ${platform.name} ${metric.abbreviation || metric.name} differ from other platforms?`,
      answer: `Different platforms use different attribution models and windows. ${platform.name} may credit conversions that other platforms attribute differently. For accurate cross-platform comparison, use a unified analytics tool like metricx.`,
    },
    {
      question: `How can I improve ${metric.abbreviation || metric.name} in ${platform.name}?`,
      answer: `To improve ${metric.abbreviation || metric.name} in ${platform.name}: optimize your targeting to reach high-intent audiences, test multiple ad creatives, improve landing page experience, and use ${platform.name}'s automated bidding strategies where appropriate.`,
    },
  ];
}

export default async function PlatformMetricPage({ params }) {
  const [platform, metric, allPlatforms, allMetrics] = await Promise.all([
    getPlatform(params.platform),
    getMetric(params.metric),
    getPlatforms(),
    getMetrics(),
  ]);

  if (!platform || !metric) {
    notFound();
  }

  const trackingSteps = getPlatformTrackingSteps(metric, platform);
  const tips = getPlatformOptimizationTips(metric, platform);
  const considerations = getPlatformConsiderations(metric, platform);
  const faqs = generatePlatformFAQs(metric, platform);

  // Get related pages for internal linking
  const relatedPlatforms = allPlatforms
    .filter((p) => p.slug !== platform.slug)
    .slice(0, 4);
  const relatedMetrics = allMetrics
    .filter((m) => m.slug !== metric.slug)
    .slice(0, 4);

  const breadcrumbItems = [
    { name: "Home", href: "/" },
    { name: "Platforms", href: "/platforms" },
    { name: platform.name, href: `/platforms/${platform.slug}` },
    { name: metric.abbreviation || metric.name },
  ];

  // JSON-LD structured data
  const howToSchema = {
    "@context": "https://schema.org",
    "@type": "HowTo",
    name: `How to Track ${metric.abbreviation || metric.name} in ${platform.name}`,
    description: `Step-by-step guide to finding and tracking ${metric.name} in ${platform.name}.`,
    step: trackingSteps.map((item, index) => ({
      "@type": "HowToStep",
      position: index + 1,
      name: item.step,
      text: item.detail,
    })),
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
      <JsonLd schema={howToSchema} />
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
              <span className="inline-flex items-center gap-2 px-3 py-1 bg-purple-50 text-purple-700 rounded-full text-sm font-medium">
                <Laptop className="w-4 h-4" />
                {platform.name}
              </span>
              <span className="text-gray-400">×</span>
              <span className="inline-flex items-center gap-2 px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-sm font-medium">
                <BarChart3 className="w-4 h-4" />
                {metric.abbreviation || metric.name}
              </span>
            </div>

            <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-6">
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-500 to-blue-600">
                {platform.name}
              </span>{" "}
              {metric.abbreviation || metric.name} Guide
            </h1>

            <p className="text-xl text-gray-600 mb-8 leading-relaxed">
              Complete guide to tracking and optimizing {metric.name} ({metric.abbreviation})
              in {platform.name}. Step-by-step instructions, benchmarks, and pro tips.
            </p>

            <div className="flex flex-wrap gap-4">
              <Link
                href="/sign-up"
                className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-500 to-blue-600 text-white font-semibold rounded-full hover:opacity-90 transition-opacity"
              >
                Track {platform.name} {metric.abbreviation || metric.name}
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

          {/* How to Track */}
          <section className="mb-16">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center gap-3">
              <Settings className="w-6 h-6 text-purple-500" />
              How to Find {metric.abbreviation || metric.name} in {platform.name}
            </h2>

            <div className="space-y-4">
              {trackingSteps.map((item, index) => (
                <div
                  key={index}
                  className="flex gap-4 p-4 bg-white rounded-xl border border-gray-200 hover:border-purple-200 transition-colors"
                >
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center">
                      <span className="text-purple-600 font-bold text-sm">{index + 1}</span>
                    </div>
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">{item.step}</h3>
                    <p className="text-sm text-gray-500 mt-1">{item.detail}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Benchmarks */}
          {metric.benchmarks && (
            <section className="mb-16">
              <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center gap-3">
                <BarChart3 className="w-6 h-6 text-blue-500" />
                {metric.abbreviation || metric.name} Benchmarks
              </h2>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                {Object.entries(metric.benchmarks).map(
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
            </section>
          )}

          {/* Optimization Tips */}
          <section className="mb-16">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center gap-3">
              <Lightbulb className="w-6 h-6 text-yellow-500" />
              How to Improve {metric.abbreviation || metric.name} in {platform.name}
            </h2>

            <div className="space-y-4">
              {tips.map((item, index) => (
                <div
                  key={index}
                  className="flex gap-4 p-4 bg-white rounded-xl border border-gray-200 hover:border-blue-200 transition-colors"
                >
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                      <CheckCircle className="w-5 h-5 text-blue-600" />
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

          {/* Important Considerations */}
          <section className="mb-16">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center gap-3">
              <AlertTriangle className="w-6 h-6 text-yellow-500" />
              Important Considerations
            </h2>

            <div className="space-y-4">
              {considerations.map((item, index) => (
                <div
                  key={index}
                  className={`flex gap-4 p-4 rounded-xl border ${
                    item.type === "warning"
                      ? "bg-yellow-50 border-yellow-200"
                      : "bg-blue-50 border-blue-200"
                  }`}
                >
                  <div className="flex-shrink-0">
                    {item.type === "warning" ? (
                      <AlertTriangle className="w-6 h-6 text-yellow-600" />
                    ) : (
                      <Eye className="w-6 h-6 text-blue-600" />
                    )}
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">{item.title}</h3>
                    <p className="text-sm text-gray-600 mt-1">{item.description}</p>
                  </div>
                </div>
              ))}
            </div>

            <div className="bg-gradient-to-r from-purple-50 to-blue-50 rounded-xl p-6 border border-purple-100 mt-6">
              <p className="text-gray-700">
                <strong>Pro tip:</strong> Use metricx to see {platform.name}{" "}
                {metric.abbreviation || metric.name} alongside your other ad platforms in one
                unified dashboard, with AI-powered optimization recommendations.
              </p>
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
            title={`Track ${platform.name} ${metric.abbreviation || metric.name} Across All Channels`}
            description={`Get unified ${metric.abbreviation || metric.name} tracking for ${platform.name}, Meta, Google, and TikTok in one dashboard.`}
            primaryCTA={{ text: "Start Free Trial", href: "/sign-up" }}
            secondaryCTA={{ text: "See Product", href: "/" }}
            variant="gradient"
          />

          {/* Related Content */}
          <section className="mt-16">
            <h2 className="text-xl font-bold text-gray-900 mb-6">Related Resources</h2>

            <div className="grid md:grid-cols-2 gap-6">
              {/* Other Metrics for This Platform */}
              <div>
                <h3 className="font-semibold text-gray-700 mb-3">
                  More {platform.name} Guides
                </h3>
                <div className="space-y-2">
                  {relatedMetrics.map((m) => (
                    <Link
                      key={m.slug}
                      href={`/platforms/${platform.slug}/${m.slug}`}
                      className="block p-3 bg-gray-50 rounded-lg hover:bg-purple-50 transition-colors"
                    >
                      <span className="font-medium text-gray-900">{platform.name}</span>
                      <span className="text-gray-500"> {m.abbreviation || m.name} Guide</span>
                    </Link>
                  ))}
                </div>
              </div>

              {/* Same Metric for Other Platforms */}
              <div>
                <h3 className="font-semibold text-gray-700 mb-3">
                  {metric.abbreviation || metric.name} on Other Platforms
                </h3>
                <div className="space-y-2">
                  {relatedPlatforms.map((p) => (
                    <Link
                      key={p.slug}
                      href={`/platforms/${p.slug}/${metric.slug}`}
                      className="block p-3 bg-gray-50 rounded-lg hover:bg-blue-50 transition-colors"
                    >
                      <span className="font-medium text-gray-900">{p.name}</span>
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
