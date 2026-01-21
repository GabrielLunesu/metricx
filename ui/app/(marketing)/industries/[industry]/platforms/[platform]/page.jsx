/**
 * Industry × Platform Combination Page
 *
 * WHAT: Long-tail SEO pages for "[Industry] [Platform] Ads" searches
 * WHY: Captures searches like "fashion ecommerce Meta Ads guide"
 *
 * Generates 864+ pages (108 industries × 8 platforms)
 *
 * Related files:
 * - content/industries/data.json - Industry data
 * - content/platforms/data.json - Platform data
 * - lib/seo/content-loader.js - Content loading utilities
 */

import { notFound } from "next/navigation";
import Link from "next/link";
import {
  getIndustries,
  getIndustry,
  getPlatforms,
  getPlatform,
} from "@/lib/seo/content-loader";
import { JsonLd } from "@/components/seo/JsonLd";
import { Breadcrumbs } from "@/components/seo/Breadcrumbs";
import { FAQ } from "@/components/seo/FAQ";
import { CTABanner } from "@/components/seo/CTABanner";
import {
  ArrowRight,
  CheckCircle,
  Laptop,
  Building2,
  TrendingUp,
  Target,
  Lightbulb,
} from "lucide-react";

/**
 * Generate all industry × platform combinations for static generation.
 */
export async function generateStaticParams() {
  const [industries, platforms] = await Promise.all([
    getIndustries(),
    getPlatforms(),
  ]);

  const params = [];
  for (const industry of industries) {
    for (const platform of platforms) {
      params.push({
        industry: industry.slug,
        platform: platform.slug,
      });
    }
  }

  return params;
}

/**
 * Generate unique metadata for each industry × platform combination.
 */
export async function generateMetadata({ params }) {
  const [industry, platform] = await Promise.all([
    getIndustry(params.industry),
    getPlatform(params.platform),
  ]);

  if (!industry || !platform) {
    return { title: "Not Found" };
  }

  const title = `${industry.name} ${platform.name} Guide | Advertising Best Practices | metricx`;
  const description = `Complete ${platform.name} advertising guide for ${industry.name.toLowerCase()} businesses. Strategies, benchmarks, and optimization tips from metricx.`;

  return {
    title,
    description,
    keywords: [
      `${industry.name.toLowerCase()} ${platform.name}`,
      `${platform.name} ads ${industry.name.toLowerCase()}`,
      `${industry.name.toLowerCase()} advertising ${platform.name}`,
      `${industry.name.toLowerCase()} ad strategy`,
    ],
    openGraph: {
      title,
      description,
      type: "article",
      url: `https://www.metricx.ai/industries/${params.industry}/platforms/${params.platform}`,
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
    },
    alternates: {
      canonical: `https://www.metricx.ai/industries/${params.industry}/platforms/${params.platform}`,
    },
  };
}

/**
 * Get platform-specific tips for an industry.
 */
function getPlatformTips(platform, industry) {
  const platformTips = {
    "meta-ads": [
      "Use Lookalike Audiences based on your best customers",
      "Test video ads - they typically outperform static images",
      "Leverage Instagram alongside Facebook for broader reach",
      "Use Advantage+ campaigns for automated optimization",
    ],
    "google-ads": [
      "Start with Search campaigns targeting high-intent keywords",
      "Use Performance Max for cross-channel optimization",
      "Implement negative keywords to reduce wasted spend",
      "Set up conversion tracking with Google Analytics 4",
    ],
    "tiktok-ads": [
      "Create native, authentic content that blends into the feed",
      "Use trending sounds and formats for better engagement",
      "Test Spark Ads to amplify organic content",
      "Target based on interests and behaviors, not just demographics",
    ],
  };

  const defaultTips = [
    "Start with clear campaign objectives",
    "Test multiple ad creatives to find winners",
    "Monitor performance daily and optimize weekly",
    "Focus on your best-performing audience segments",
  ];

  const tips = platformTips[platform.slug] || defaultTips;
  return tips.map((tip) => ({
    tip,
    context: `Proven strategy for ${industry.name.toLowerCase()} businesses.`,
  }));
}

/**
 * Get key metrics to track for this combination.
 */
function getKeyMetrics() {
  return [
    { name: "ROAS", slug: "roas", description: "Return on ad spend - your primary efficiency metric" },
    { name: "CPA", slug: "cpa", description: "Cost per acquisition - what you pay per customer" },
    { name: "CTR", slug: "ctr", description: "Click-through rate - measures ad engagement" },
    { name: "CPM", slug: "cpm", description: "Cost per 1,000 impressions - your reach efficiency" },
  ];
}

/**
 * Generate FAQs specific to this industry × platform combination.
 */
function generateCombinationFAQs(industry, platform) {
  return [
    {
      question: `Is ${platform.name} effective for ${industry.name.toLowerCase()} businesses?`,
      answer: `Yes, ${platform.name} can be highly effective for ${industry.name.toLowerCase()} businesses when used correctly. The key is targeting the right audience and creating compelling creative that resonates with ${industry.name.toLowerCase()} customers.`,
    },
    {
      question: `What's a good ROAS for ${industry.name.toLowerCase()} on ${platform.name}?`,
      answer: `${industry.name} businesses on ${platform.name} typically see ROAS of 3-5x for good performance. However, this varies based on your margins and business model. Use metricx to track your specific performance.`,
    },
    {
      question: `How much should ${industry.name.toLowerCase()} businesses spend on ${platform.name}?`,
      answer: `Start with a test budget of $500-1000 to gather data, then scale based on performance. ${industry.name.toLowerCase()} businesses often allocate 10-20% of revenue to advertising, split across platforms based on ROAS.`,
    },
    {
      question: `How does metricx help ${industry.name.toLowerCase()} businesses track ${platform.name}?`,
      answer: `metricx provides unified ${platform.name} analytics specifically for ${industry.name.toLowerCase()} businesses. See your performance alongside other ad platforms and your e-commerce data in one dashboard.`,
    },
  ];
}

export default async function IndustryPlatformPage({ params }) {
  const [industry, platform, allIndustries, allPlatforms] = await Promise.all([
    getIndustry(params.industry),
    getPlatform(params.platform),
    getIndustries(),
    getPlatforms(),
  ]);

  if (!industry || !platform) {
    notFound();
  }

  const tips = getPlatformTips(platform, industry);
  const keyMetrics = getKeyMetrics();
  const faqs = generateCombinationFAQs(industry, platform);

  // Get related pages for internal linking
  const relatedIndustries = allIndustries
    .filter((i) => i.slug !== industry.slug && i.category === industry.category)
    .slice(0, 4);
  const relatedPlatforms = allPlatforms
    .filter((p) => p.slug !== platform.slug)
    .slice(0, 4);

  const breadcrumbItems = [
    { name: "Home", href: "/" },
    { name: "Industries", href: "/industries" },
    { name: industry.name, href: `/industries/${industry.slug}` },
    { name: platform.name },
  ];

  // JSON-LD structured data
  const articleSchema = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: `${industry.name} ${platform.name} Advertising Guide`,
    description: `Complete guide to ${platform.name} advertising for ${industry.name.toLowerCase()} businesses.`,
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
              <span className="inline-flex items-center gap-2 px-3 py-1 bg-purple-50 text-purple-700 rounded-full text-sm font-medium">
                <Laptop className="w-4 h-4" />
                {platform.name}
              </span>
            </div>

            <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-6">
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-500 to-purple-500">
                {industry.name}
              </span>{" "}
              {platform.name} Guide
            </h1>

            <p className="text-xl text-gray-600 mb-8 leading-relaxed">
              Complete guide to {platform.name} advertising for{" "}
              {industry.name.toLowerCase()} businesses. Best practices, benchmarks, and
              optimization strategies.
            </p>

            <div className="flex flex-wrap gap-4">
              <Link
                href="/sign-up"
                className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-cyan-500 to-purple-500 text-white font-semibold rounded-full hover:opacity-90 transition-opacity"
              >
                Track {platform.name} Performance
                <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                href="/"
                className="inline-flex items-center gap-2 px-6 py-3 bg-white border border-gray-200 text-gray-700 font-semibold rounded-full hover:bg-gray-50 transition-colors"
              >
                See Product
              </Link>
            </div>
          </div>
        </section>

        {/* Main Content */}
        <article className="max-w-4xl mx-auto px-4 py-16">
          {/* Overview Section */}
          <section className="mb-16">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center gap-3">
              <Target className="w-6 h-6 text-cyan-500" />
              Why {platform.name} Works for {industry.name}
            </h2>
            <p className="text-gray-600 leading-relaxed mb-6">
              {platform.name} is one of the most effective advertising platforms for{" "}
              {industry.name.toLowerCase()} businesses. With precise targeting options and
              massive reach, {platform.name} helps {industry.name.toLowerCase()} brands
              connect with their ideal customers.
            </p>

            <div className="bg-gradient-to-r from-cyan-50 to-purple-50 rounded-xl p-6 border border-cyan-100">
              <p className="text-gray-700">
                <strong>The opportunity:</strong> {industry.name} businesses using{" "}
                {platform.name} effectively can achieve significant competitive advantage.
                Track your performance with metricx to optimize results.
              </p>
            </div>
          </section>

          {/* Key Metrics Section */}
          <section className="mb-16">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center gap-3">
              <TrendingUp className="w-6 h-6 text-purple-500" />
              Key Metrics to Track
            </h2>

            <div className="grid md:grid-cols-2 gap-4">
              {keyMetrics.map((metric, index) => (
                <Link
                  key={index}
                  href={`/industries/${industry.slug}/${metric.slug}`}
                  className="flex gap-4 p-4 bg-white rounded-xl border border-gray-200 hover:border-purple-200 transition-colors"
                >
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center">
                      <TrendingUp className="w-5 h-5 text-purple-600" />
                    </div>
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">{metric.name}</h3>
                    <p className="text-sm text-gray-500 mt-1">{metric.description}</p>
                  </div>
                </Link>
              ))}
            </div>
          </section>

          {/* Tips Section */}
          <section className="mb-16">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center gap-3">
              <Lightbulb className="w-6 h-6 text-yellow-500" />
              {platform.name} Best Practices for {industry.name}
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
            title={`Track ${platform.name} for Your ${industry.name} Business`}
            description={`Get unified analytics for your ${industry.name.toLowerCase()} ${platform.name} campaigns with AI-powered optimization.`}
            primaryCTA={{ text: "Start Free Trial", href: "/sign-up" }}
            secondaryCTA={{ text: "See Product", href: "/" }}
            variant="gradient"
          />

          {/* Related Content */}
          <section className="mt-16">
            <h2 className="text-xl font-bold text-gray-900 mb-6">Related Resources</h2>

            <div className="grid md:grid-cols-2 gap-6">
              {/* Same Industry, Different Platforms */}
              <div>
                <h3 className="font-semibold text-gray-700 mb-3">
                  More Platforms for {industry.name}
                </h3>
                <div className="space-y-2">
                  {relatedPlatforms.map((p) => (
                    <Link
                      key={p.slug}
                      href={`/industries/${industry.slug}/platforms/${p.slug}`}
                      className="block p-3 bg-gray-50 rounded-lg hover:bg-purple-50 transition-colors"
                    >
                      <span className="font-medium text-gray-900">{industry.name}</span>
                      <span className="text-gray-500"> {p.name} Guide</span>
                    </Link>
                  ))}
                </div>
              </div>

              {/* Same Platform, Different Industries */}
              <div>
                <h3 className="font-semibold text-gray-700 mb-3">
                  {platform.name} for Other Industries
                </h3>
                <div className="space-y-2">
                  {relatedIndustries.map((i) => (
                    <Link
                      key={i.slug}
                      href={`/industries/${i.slug}/platforms/${platform.slug}`}
                      className="block p-3 bg-gray-50 rounded-lg hover:bg-cyan-50 transition-colors"
                    >
                      <span className="font-medium text-gray-900">{i.name}</span>
                      <span className="text-gray-500"> {platform.name} Guide</span>
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
