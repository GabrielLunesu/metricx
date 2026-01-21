/**
 * Use Case × Industry Combination Page
 *
 * WHAT: Long-tail SEO pages for "[Use Case] for [Industry]" searches
 * WHY: Captures high-intent searches like "track ROAS for fashion ecommerce"
 *
 * Generates 10,260+ pages (95 use cases × 108 industries)
 *
 * Related files:
 * - content/use-cases/data.json - Use case data
 * - content/industries/data.json - Industry data
 * - lib/seo/content-loader.js - Content loading utilities
 */

import { notFound } from "next/navigation";
import Link from "next/link";
import {
  getUseCases,
  getUseCase,
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
  Target,
  Lightbulb,
  Building2,
  Zap,
  TrendingUp,
} from "lucide-react";

/**
 * Enable on-demand generation for pages not pre-rendered at build time.
 * This allows ISR to generate pages when first requested.
 */
export const dynamicParams = true;

/**
 * Generate top use case × industry combinations for static generation.
 * Only pre-renders ~50 highest-value pages to stay under Vercel size limits.
 * Remaining 10,000+ pages are generated on-demand via ISR.
 */
export async function generateStaticParams() {
  const [useCases, industries] = await Promise.all([
    getUseCases(),
    getIndustries(),
  ]);

  // Pre-render only top 5 use cases × top 10 industries = 50 pages
  // Rest will be generated on-demand (ISR)
  const topUseCases = useCases.slice(0, 5);
  const topIndustries = industries.slice(0, 10);

  const params = [];
  for (const useCase of topUseCases) {
    for (const industry of topIndustries) {
      params.push({
        "use-case": useCase.slug,
        industry: industry.slug,
      });
    }
  }

  return params;
}

/**
 * Generate unique metadata for each use case × industry combination.
 */
export async function generateMetadata({ params }) {
  const [useCase, industry] = await Promise.all([
    getUseCase(params["use-case"]),
    getIndustry(params.industry),
  ]);

  if (!useCase || !industry) {
    return { title: "Not Found" };
  }

  const title = `${useCase.title} for ${industry.name} | metricx`;
  const description = `Learn how ${industry.name.toLowerCase()} businesses can ${useCase.title.toLowerCase()}. Step-by-step guide and best practices from metricx.`;

  return {
    title,
    description,
    keywords: [
      `${useCase.title.toLowerCase()} ${industry.name.toLowerCase()}`,
      `${industry.name.toLowerCase()} ${useCase.category || "analytics"}`,
      `${industry.name.toLowerCase()} ad tracking`,
      `${useCase.title.toLowerCase()} guide`,
    ],
    openGraph: {
      title,
      description,
      type: "article",
      url: `https://www.metricx.ai/use-cases/${params["use-case"]}/${params.industry}`,
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
    },
    alternates: {
      canonical: `https://www.metricx.ai/use-cases/${params["use-case"]}/${params.industry}`,
    },
  };
}

/**
 * Generate industry-specific benefits for a use case.
 */
function getIndustryBenefits(useCase, industry) {
  const baseBenefits = useCase.benefits || [
    "Save time with automated tracking",
    "Get actionable insights",
    "Improve ad performance",
    "Make data-driven decisions",
  ];

  return baseBenefits.slice(0, 4).map((benefit) => ({
    benefit,
    context: `Especially valuable for ${industry.name.toLowerCase()} businesses.`,
  }));
}

/**
 * Generate industry-specific implementation steps.
 */
function getImplementationSteps(useCase, industry) {
  const baseSteps = useCase.steps || [
    "Connect your ad accounts",
    "Set up tracking parameters",
    "Configure your dashboard",
    "Start analyzing data",
  ];

  return baseSteps.slice(0, 5).map((step, index) => ({
    step,
    detail: `Customize this step for your ${industry.name.toLowerCase()} business needs.`,
    position: index + 1,
  }));
}

/**
 * Generate FAQs specific to this use case × industry combination.
 */
function generateCombinationFAQs(useCase, industry) {
  return [
    {
      question: `How can ${industry.name.toLowerCase()} businesses ${useCase.title.toLowerCase()}?`,
      answer: `${industry.name} businesses can ${useCase.title.toLowerCase()} by using metricx's unified analytics platform. Connect your ad accounts (Meta, Google, TikTok), and metricx automatically tracks performance across all channels in one dashboard.`,
    },
    {
      question: `Why is ${useCase.title.toLowerCase()} important for ${industry.name.toLowerCase()}?`,
      answer: `For ${industry.name.toLowerCase()} businesses, ${useCase.title.toLowerCase()} helps optimize ad spend, identify top-performing campaigns, and improve overall marketing ROI. This is especially important in the competitive ${industry.name.toLowerCase()} market.`,
    },
    {
      question: `What tools does metricx offer for ${industry.name.toLowerCase()} ${useCase.category || "analytics"}?`,
      answer: `metricx provides ${industry.name.toLowerCase()} businesses with: unified multi-platform tracking, AI-powered insights, real-time dashboards, and Shopify integration for complete attribution. Our platform is designed to make ${useCase.title.toLowerCase()} simple and actionable.`,
    },
    {
      question: `How quickly can I start ${useCase.title.toLowerCase()} with metricx?`,
      answer: `Most ${industry.name.toLowerCase()} businesses can get started with metricx in under 5 minutes. Simply connect your ad accounts, and you'll immediately see your performance data in our unified dashboard. No complex setup required.`,
    },
  ];
}

export default async function UseCaseIndustryPage({ params }) {
  const [useCase, industry, allUseCases, allIndustries] = await Promise.all([
    getUseCase(params["use-case"]),
    getIndustry(params.industry),
    getUseCases(),
    getIndustries(),
  ]);

  if (!useCase || !industry) {
    notFound();
  }

  const benefits = getIndustryBenefits(useCase, industry);
  const steps = getImplementationSteps(useCase, industry);
  const faqs = generateCombinationFAQs(useCase, industry);

  // Get related pages for internal linking
  const relatedUseCases = allUseCases
    .filter((u) => u.slug !== useCase.slug && u.category === useCase.category)
    .slice(0, 4);
  const relatedIndustries = allIndustries
    .filter((i) => i.slug !== industry.slug && i.category === industry.category)
    .slice(0, 4);

  const breadcrumbItems = [
    { name: "Home", href: "/" },
    { name: "Use Cases", href: "/use-cases" },
    { name: useCase.title, href: `/use-cases/${useCase.slug}` },
    { name: industry.name },
  ];

  // JSON-LD structured data
  const howToSchema = {
    "@context": "https://schema.org",
    "@type": "HowTo",
    name: `How to ${useCase.title} for ${industry.name}`,
    description: `Step-by-step guide for ${industry.name.toLowerCase()} businesses to ${useCase.title.toLowerCase()}.`,
    step: steps.map((item) => ({
      "@type": "HowToStep",
      position: item.position,
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
              <span className="inline-flex items-center gap-2 px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-sm font-medium">
                <Zap className="w-4 h-4" />
                {useCase.category || "Analytics"}
              </span>
              <span className="text-gray-400">×</span>
              <span className="inline-flex items-center gap-2 px-3 py-1 bg-cyan-50 text-cyan-700 rounded-full text-sm font-medium">
                <Building2 className="w-4 h-4" />
                {industry.name}
              </span>
            </div>

            <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-6">
              {useCase.title} for{" "}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-cyan-500">
                {industry.name}
              </span>
            </h1>

            <p className="text-xl text-gray-600 mb-8 leading-relaxed">
              Learn how {industry.name.toLowerCase()} businesses can{" "}
              {useCase.title.toLowerCase()} with metricx. Step-by-step guide, best
              practices, and expert tips.
            </p>

            <div className="flex flex-wrap gap-4">
              <Link
                href="/sign-up"
                className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-cyan-500 text-white font-semibold rounded-full hover:opacity-90 transition-opacity"
              >
                Get Started Free
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
              <Target className="w-6 h-6 text-blue-500" />
              Why {industry.name} Businesses Need This
            </h2>
            <p className="text-gray-600 leading-relaxed mb-6">
              {useCase.description ||
                `${useCase.title} is essential for ${industry.name.toLowerCase()} businesses looking to optimize their advertising performance. With accurate tracking and AI-powered insights, you can make data-driven decisions that improve ROI.`}
            </p>

            <div className="bg-gradient-to-r from-blue-50 to-cyan-50 rounded-xl p-6 border border-blue-100">
              <p className="text-gray-700">
                <strong>The challenge:</strong> {industry.name} businesses often struggle
                with fragmented data across multiple ad platforms. metricx solves this by
                providing a unified view of all your advertising performance.
              </p>
            </div>
          </section>

          {/* Benefits Section */}
          <section className="mb-16">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center gap-3">
              <TrendingUp className="w-6 h-6 text-cyan-500" />
              Key Benefits for {industry.name}
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
                    <p className="text-sm text-gray-500 mt-1">{item.context}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* How-To Steps */}
          <section className="mb-16">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center gap-3">
              <Lightbulb className="w-6 h-6 text-yellow-500" />
              How to Get Started
            </h2>

            <div className="space-y-4">
              {steps.map((item, index) => (
                <div
                  key={index}
                  className="flex gap-4 p-4 bg-white rounded-xl border border-gray-200 hover:border-blue-200 transition-colors"
                >
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                      <span className="text-blue-600 font-bold text-sm">
                        {item.position}
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
            title={`Start ${useCase.title} for Your ${industry.name} Business`}
            description={`Join thousands of ${industry.name.toLowerCase()} businesses using metricx to optimize their ad performance.`}
            primaryCTA={{ text: "Start Free Trial", href: "/sign-up" }}
            secondaryCTA={{ text: "See Product", href: "/" }}
            variant="gradient"
          />

          {/* Related Content */}
          <section className="mt-16">
            <h2 className="text-xl font-bold text-gray-900 mb-6">Related Resources</h2>

            <div className="grid md:grid-cols-2 gap-6">
              {/* Other Use Cases for This Industry */}
              <div>
                <h3 className="font-semibold text-gray-700 mb-3">
                  More for {industry.name}
                </h3>
                <div className="space-y-2">
                  {relatedUseCases.map((u) => (
                    <Link
                      key={u.slug}
                      href={`/use-cases/${u.slug}/${industry.slug}`}
                      className="block p-3 bg-gray-50 rounded-lg hover:bg-blue-50 transition-colors"
                    >
                      <span className="font-medium text-gray-900">{u.title}</span>
                      <span className="text-gray-500"> for {industry.name}</span>
                    </Link>
                  ))}
                </div>
              </div>

              {/* Same Use Case for Other Industries */}
              <div>
                <h3 className="font-semibold text-gray-700 mb-3">
                  {useCase.title} for Other Industries
                </h3>
                <div className="space-y-2">
                  {relatedIndustries.map((i) => (
                    <Link
                      key={i.slug}
                      href={`/use-cases/${useCase.slug}/${i.slug}`}
                      className="block p-3 bg-gray-50 rounded-lg hover:bg-cyan-50 transition-colors"
                    >
                      <span className="font-medium text-gray-900">{useCase.title}</span>
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
