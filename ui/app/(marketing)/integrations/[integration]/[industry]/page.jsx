/**
 * Integration × Industry Combination Page
 *
 * WHAT: Long-tail SEO pages for "[Integration] for [Industry]" searches
 * WHY: Captures searches like "Shopify analytics for fashion ecommerce"
 *
 * Generates 1,296+ pages (12 integrations × 108 industries)
 *
 * Related files:
 * - content/integrations/data.json - Integration data
 * - content/industries/data.json - Industry data
 * - lib/seo/content-loader.js - Content loading utilities
 */

import { notFound } from "next/navigation";
import Link from "next/link";
import {
  getIntegrations,
  getIntegration,
  getIndustries,
  getIndustry,
} from "@/lib/seo/content-loader";
import { JsonLd } from "@/components/seo/JsonLd";
import { Breadcrumbs } from "@/components/seo/Breadcrumbs";
import { FAQ } from "@/components/seo/FAQ";
import { CTABanner } from "@/components/seo/CTABanner";
import {
  ArrowRight,
  CheckCircle,
  Plug,
  Building2,
  TrendingUp,
  Zap,
  Settings,
} from "lucide-react";

/**
 * Enable on-demand generation for pages not pre-rendered at build time.
 * This allows ISR to generate pages when first requested.
 */
export const dynamicParams = true;

/**
 * Generate top integration × industry combinations for static generation.
 * Only pre-renders ~50 highest-value pages to stay under Vercel size limits.
 * Remaining 1,200+ pages are generated on-demand via ISR.
 */
export async function generateStaticParams() {
  const [integrations, industries] = await Promise.all([
    getIntegrations(),
    getIndustries(),
  ]);

  // Pre-render top 5 integrations × top 10 industries = 50 pages
  // Rest will be generated on-demand (ISR)
  const topIntegrations = integrations.slice(0, 5);
  const topIndustries = industries.slice(0, 10);

  const params = [];
  for (const integration of topIntegrations) {
    for (const industry of topIndustries) {
      params.push({
        integration: integration.slug,
        industry: industry.slug,
      });
    }
  }

  return params;
}

/**
 * Generate unique metadata for each integration × industry combination.
 */
export async function generateMetadata({ params }) {
  const [integration, industry] = await Promise.all([
    getIntegration(params.integration),
    getIndustry(params.industry),
  ]);

  if (!integration || !industry) {
    return { title: "Not Found" };
  }

  const title = `${integration.name} Analytics for ${industry.name} | metricx`;
  const description = `Connect ${integration.name} to metricx for ${industry.name.toLowerCase()} analytics. Track ad performance, ROAS, and revenue with unified ${integration.name} data.`;

  return {
    title,
    description,
    keywords: [
      `${integration.name} ${industry.name.toLowerCase()}`,
      `${integration.name} analytics ${industry.name.toLowerCase()}`,
      `${industry.name.toLowerCase()} ${integration.name} tracking`,
      `${integration.name} ROAS tracking`,
    ],
    openGraph: {
      title,
      description,
      type: "article",
      url: `https://www.metricx.ai/integrations/${params.integration}/${params.industry}`,
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
    },
    alternates: {
      canonical: `https://www.metricx.ai/integrations/${params.integration}/${params.industry}`,
    },
  };
}

/**
 * Get integration benefits for a specific industry.
 */
function getIntegrationBenefits(integration, industry) {
  const baseBenefits = integration.benefits || [
    "Unified data view",
    "Automated sync",
    "Real-time updates",
    "Better attribution",
  ];

  return baseBenefits.slice(0, 4).map((benefit) => ({
    benefit,
    detail: `Essential for ${industry.name.toLowerCase()} businesses using ${integration.name}.`,
  }));
}

/**
 * Get setup steps for this integration.
 */
function getSetupSteps(integration, industry) {
  return [
    {
      step: `Connect your ${integration.name} account`,
      detail: `Log into metricx and authenticate with your ${integration.name} credentials.`,
    },
    {
      step: "Grant necessary permissions",
      detail: `Allow metricx to read your ${integration.name} ${industry.name.toLowerCase()} data.`,
    },
    {
      step: "Configure data sync settings",
      detail: "Choose which metrics and data points to track automatically.",
    },
    {
      step: "Start tracking performance",
      detail: `View your ${industry.name.toLowerCase()} analytics in the unified metricx dashboard.`,
    },
  ];
}

/**
 * Generate FAQs specific to this integration × industry combination.
 */
function generateCombinationFAQs(integration, industry) {
  return [
    {
      question: `How does metricx integrate with ${integration.name} for ${industry.name.toLowerCase()}?`,
      answer: `metricx connects directly to your ${integration.name} account to pull ${industry.name.toLowerCase()} sales, revenue, and customer data. This data is combined with your ad platform metrics to show accurate ROAS and attribution.`,
    },
    {
      question: `What ${integration.name} data can I track for my ${industry.name.toLowerCase()} business?`,
      answer: `metricx syncs orders, revenue, customer data, and product performance from ${integration.name}. For ${industry.name.toLowerCase()} businesses, this means accurate attribution of which ads drive ${integration.name} sales.`,
    },
    {
      question: `Is the ${integration.name} integration secure for ${industry.name.toLowerCase()} data?`,
      answer: `Yes, metricx uses OAuth 2.0 for secure ${integration.name} authentication. Your ${industry.name.toLowerCase()} business data is encrypted in transit and at rest, and we never store your ${integration.name} credentials.`,
    },
    {
      question: `How quickly does ${integration.name} data sync with metricx?`,
      answer: `${integration.name} data typically syncs within 15-30 minutes. For ${industry.name.toLowerCase()} businesses with high order volume, our real-time sync ensures your analytics are always up to date.`,
    },
  ];
}

export default async function IntegrationIndustryPage({ params }) {
  const [integration, industry, allIntegrations, allIndustries] =
    await Promise.all([
      getIntegration(params.integration),
      getIndustry(params.industry),
      getIntegrations(),
      getIndustries(),
    ]);

  if (!integration || !industry) {
    notFound();
  }

  const benefits = getIntegrationBenefits(integration, industry);
  const steps = getSetupSteps(integration, industry);
  const faqs = generateCombinationFAQs(integration, industry);

  // Get related pages for internal linking
  const relatedIntegrations = allIntegrations
    .filter((i) => i.slug !== integration.slug)
    .slice(0, 4);
  const relatedIndustries = allIndustries
    .filter((i) => i.slug !== industry.slug && i.category === industry.category)
    .slice(0, 4);

  const breadcrumbItems = [
    { name: "Home", href: "/" },
    { name: "Integrations", href: "/integrations" },
    { name: integration.name, href: `/integrations/${integration.slug}` },
    { name: industry.name },
  ];

  // JSON-LD structured data
  const articleSchema = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: `${integration.name} Analytics for ${industry.name}`,
    description: `How to use ${integration.name} with metricx for ${industry.name.toLowerCase()} analytics.`,
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
              <span className="inline-flex items-center gap-2 px-3 py-1 bg-purple-50 text-purple-700 rounded-full text-sm font-medium">
                <Plug className="w-4 h-4" />
                {integration.name}
              </span>
              <span className="text-gray-400">×</span>
              <span className="inline-flex items-center gap-2 px-3 py-1 bg-cyan-50 text-cyan-700 rounded-full text-sm font-medium">
                <Building2 className="w-4 h-4" />
                {industry.name}
              </span>
            </div>

            <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-6">
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-500 to-cyan-500">
                {integration.name}
              </span>{" "}
              Analytics for {industry.name}
            </h1>

            <p className="text-xl text-gray-600 mb-8 leading-relaxed">
              Connect {integration.name} to metricx for complete{" "}
              {industry.name.toLowerCase()} analytics. Track ROAS, verify revenue, and
              get AI-powered insights.
            </p>

            <div className="flex flex-wrap gap-4">
              <Link
                href="/sign-up"
                className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-500 to-cyan-500 text-white font-semibold rounded-full hover:opacity-90 transition-opacity"
              >
                Connect {integration.name}
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
          {/* Why Connect Section */}
          <section className="mb-16">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center gap-3">
              <Zap className="w-6 h-6 text-purple-500" />
              Why Connect {integration.name} for {industry.name}?
            </h2>
            <p className="text-gray-600 leading-relaxed mb-6">
              {integration.description ||
                `${integration.name} integration enables accurate revenue attribution for your ${industry.name.toLowerCase()} business. By connecting ${integration.name} to metricx, you can see exactly which ads drive sales and optimize your marketing spend.`}
            </p>

            <div className="bg-gradient-to-r from-purple-50 to-cyan-50 rounded-xl p-6 border border-purple-100">
              <p className="text-gray-700">
                <strong>The advantage:</strong> Stop relying on platform-reported data.
                With {integration.name} connected, metricx shows you verified revenue and
                true ROAS for your {industry.name.toLowerCase()} business.
              </p>
            </div>
          </section>

          {/* Benefits Section */}
          <section className="mb-16">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center gap-3">
              <TrendingUp className="w-6 h-6 text-cyan-500" />
              Key Benefits
            </h2>

            <div className="grid md:grid-cols-2 gap-4">
              {benefits.map((item, index) => (
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
                    <h3 className="font-semibold text-gray-900">{item.benefit}</h3>
                    <p className="text-sm text-gray-500 mt-1">{item.detail}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Setup Steps */}
          <section className="mb-16">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center gap-3">
              <Settings className="w-6 h-6 text-purple-500" />
              How to Set Up
            </h2>

            <div className="space-y-4">
              {steps.map((item, index) => (
                <div
                  key={index}
                  className="flex gap-4 p-4 bg-white rounded-xl border border-gray-200 hover:border-purple-200 transition-colors"
                >
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center">
                      <span className="text-purple-600 font-bold text-sm">
                        {index + 1}
                      </span>
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

          {/* FAQs */}
          <section className="mb-16">
            <h2 className="text-2xl font-bold text-gray-900 mb-6">
              Frequently Asked Questions
            </h2>
            <FAQ items={faqs} />
          </section>

          {/* CTA Banner */}
          <CTABanner
            title={`Connect ${integration.name} for Your ${industry.name} Business`}
            description={`Get accurate analytics and verified ROAS for your ${industry.name.toLowerCase()} ${integration.name} store.`}
            primaryCTA={{ text: "Start Free Trial", href: "/sign-up" }}
            secondaryCTA={{ text: "See Product", href: "/" }}
            variant="gradient"
          />

          {/* Related Content */}
          <section className="mt-16">
            <h2 className="text-xl font-bold text-gray-900 mb-6">Related Resources</h2>

            <div className="grid md:grid-cols-2 gap-6">
              {/* Other Integrations for This Industry */}
              <div>
                <h3 className="font-semibold text-gray-700 mb-3">
                  More Integrations for {industry.name}
                </h3>
                <div className="space-y-2">
                  {relatedIntegrations.map((i) => (
                    <Link
                      key={i.slug}
                      href={`/integrations/${i.slug}/${industry.slug}`}
                      className="block p-3 bg-gray-50 rounded-lg hover:bg-purple-50 transition-colors"
                    >
                      <span className="font-medium text-gray-900">{i.name}</span>
                      <span className="text-gray-500"> for {industry.name}</span>
                    </Link>
                  ))}
                </div>
              </div>

              {/* Same Integration for Other Industries */}
              <div>
                <h3 className="font-semibold text-gray-700 mb-3">
                  {integration.name} for Other Industries
                </h3>
                <div className="space-y-2">
                  {relatedIndustries.map((i) => (
                    <Link
                      key={i.slug}
                      href={`/integrations/${integration.slug}/${i.slug}`}
                      className="block p-3 bg-gray-50 rounded-lg hover:bg-cyan-50 transition-colors"
                    >
                      <span className="font-medium text-gray-900">
                        {integration.name}
                      </span>
                      <span className="text-gray-500"> for {i.name}</span>
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
