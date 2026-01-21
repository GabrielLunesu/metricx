/**
 * Individual Competitor Comparison Page
 *
 * WHAT: Dynamic comparison page for each competitor
 * WHY: SEO page targeting "metricx vs [competitor]" keywords
 *
 * Related files:
 * - content/competitors/data.json - Competitor data
 * - lib/seo/content-loader.js - Data loading
 * - components/seo/ - SEO components
 */

import { notFound } from "next/navigation";
import Link from "next/link";
import { getCompetitors, getCompetitor } from "@/lib/seo/content-loader";
import { Breadcrumbs, FAQ, CTABanner } from "@/components/seo";
import { JsonLd } from "@/components/seo/JsonLd";
import {
  generateBreadcrumbSchema,
  generateFAQSchema,
  generateProductComparisonSchema,
} from "@/lib/seo/schemas";
import {
  Check,
  X,
  ArrowRight,
  DollarSign,
  Clock,
  Sparkles,
  Shield,
  Users,
  Zap,
} from "lucide-react";

/**
 * Generate static params for all competitors.
 */
export async function generateStaticParams() {
  const competitors = await getCompetitors();
  return competitors.map((c) => ({
    competitor: c.slug,
  }));
}

/**
 * Generate metadata for comparison page.
 */
export async function generateMetadata({ params }) {
  const { competitor: slug } = await params;
  const competitor = await getCompetitor(slug);

  if (!competitor) {
    return {
      title: "Comparison Not Found | metricx",
    };
  }

  const savings = competitor.comparisonPoints?.price?.savings || "";
  const savingsText = savings ? ` Save ${savings}.` : "";

  return {
    title: `metricx vs ${competitor.name} (2026) | Comparison & Savings`,
    description: `Compare metricx and ${competitor.name}. ${competitor.pricing} vs $29.99/month.${savingsText} See why e-commerce brands choose metricx for simpler ad analytics.`,
    keywords: [
      `metricx vs ${competitor.name.toLowerCase()}`,
      `${competitor.name.toLowerCase()} alternative`,
      `${competitor.name.toLowerCase()} comparison`,
      `${competitor.name.toLowerCase()} pricing`,
    ],
    openGraph: {
      title: `metricx vs ${competitor.name} | Detailed Comparison`,
      description: `See how metricx compares to ${competitor.name} for ad analytics.`,
      type: "article",
      url: `https://www.metricx.ai/vs/${competitor.slug}`,
    },
    twitter: {
      card: "summary_large_image",
      title: `metricx vs ${competitor.name}`,
      description: `Compare metricx and ${competitor.name} for e-commerce ad analytics.`,
    },
    alternates: {
      canonical: `https://www.metricx.ai/vs/${competitor.slug}`,
    },
  };
}

/**
 * Comparison point row component.
 */
function ComparisonRow({ label, them, us, winner, icon: Icon }) {
  return (
    <div className="grid grid-cols-3 gap-4 py-4 border-b border-slate-100 items-center">
      <div className="flex items-center gap-2">
        {Icon && <Icon className="w-4 h-4 text-slate-400" />}
        <span className="font-medium text-slate-900">{label}</span>
      </div>
      <div className={`text-center ${winner === "them" ? "font-semibold text-slate-900" : "text-slate-600"}`}>
        {them}
      </div>
      <div className={`text-center ${winner === "metricx" ? "font-semibold text-cyan-600" : "text-slate-600"}`}>
        {us}
        {winner === "metricx" && (
          <Check className="w-4 h-4 text-emerald-500 inline ml-1" />
        )}
      </div>
    </div>
  );
}

/**
 * Feature comparison table component.
 */
function FeatureComparisonTable({ competitor }) {
  const features = [
    { key: "metaAds", label: "Meta Ads Integration", icon: null },
    { key: "googleAds", label: "Google Ads Integration", icon: null },
    { key: "tiktokAds", label: "TikTok Ads Integration", icon: null },
    { key: "shopifyIntegration", label: "Shopify Integration", icon: null },
    { key: "aiInsights", label: "AI-Powered Insights", icon: Sparkles },
    { key: "attribution", label: "Attribution Modeling", icon: null },
    { key: "creativeAnalytics", label: "Creative Analytics", icon: null },
  ];

  const metricxFeatures = {
    metaAds: true,
    googleAds: true,
    tiktokAds: true,
    shopifyIntegration: true,
    aiInsights: true,
    attribution: true,
    creativeAnalytics: true,
  };

  return (
    <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
      <div className="grid grid-cols-3 gap-4 p-4 bg-slate-50 border-b border-slate-200">
        <div className="font-semibold text-slate-900">Feature</div>
        <div className="font-semibold text-slate-900 text-center">{competitor.name}</div>
        <div className="font-semibold text-cyan-600 text-center">metricx</div>
      </div>
      <div className="p-4">
        {features.map((feature) => {
          const theyHave = competitor.features?.[feature.key];
          const weHave = metricxFeatures[feature.key];
          return (
            <div
              key={feature.key}
              className="grid grid-cols-3 gap-4 py-3 border-b border-slate-100 last:border-0"
            >
              <div className="flex items-center gap-2 text-slate-700">
                {feature.icon && <feature.icon className="w-4 h-4 text-slate-400" />}
                {feature.label}
              </div>
              <div className="text-center">
                {theyHave ? (
                  <Check className="w-5 h-5 text-emerald-500 mx-auto" />
                ) : (
                  <X className="w-5 h-5 text-slate-300 mx-auto" />
                )}
              </div>
              <div className="text-center">
                {weHave ? (
                  <Check className="w-5 h-5 text-emerald-500 mx-auto" />
                ) : (
                  <X className="w-5 h-5 text-slate-300 mx-auto" />
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/**
 * Pros and cons component.
 */
function ProsCons({ pros, cons, name }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div className="bg-emerald-50 border border-emerald-100 rounded-xl p-6">
        <h3 className="font-semibold text-emerald-800 mb-4">
          {name} Strengths
        </h3>
        <ul className="space-y-2">
          {pros?.map((pro, i) => (
            <li key={i} className="flex items-start gap-2 text-emerald-700">
              <Check className="w-4 h-4 flex-shrink-0 mt-1" />
              <span>{pro}</span>
            </li>
          ))}
        </ul>
      </div>
      <div className="bg-red-50 border border-red-100 rounded-xl p-6">
        <h3 className="font-semibold text-red-800 mb-4">
          {name} Weaknesses
        </h3>
        <ul className="space-y-2">
          {cons?.map((con, i) => (
            <li key={i} className="flex items-start gap-2 text-red-700">
              <X className="w-4 h-4 flex-shrink-0 mt-1" />
              <span>{con}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

/**
 * Savings calculator component.
 */
function SavingsCalculator({ competitor }) {
  const theirPrice = competitor.pricing;
  const savings = competitor.comparisonPoints?.price?.savings;

  return (
    <div className="bg-gradient-to-r from-cyan-500 to-cyan-600 text-white rounded-xl p-8">
      <h3 className="text-2xl font-bold mb-4">Potential Savings</h3>
      <div className="grid grid-cols-2 gap-8">
        <div>
          <div className="text-cyan-100 mb-1">{competitor.name}</div>
          <div className="text-3xl font-bold">{theirPrice}</div>
        </div>
        <div>
          <div className="text-cyan-100 mb-1">metricx</div>
          <div className="text-3xl font-bold">$29.99/mo</div>
        </div>
      </div>
      {savings && (
        <div className="mt-6 pt-6 border-t border-cyan-400">
          <div className="text-cyan-100">You could save</div>
          <div className="text-4xl font-bold">{savings}</div>
          <div className="text-cyan-100">every month with metricx</div>
        </div>
      )}
    </div>
  );
}

/**
 * Individual Competitor Comparison Page Component
 */
export default async function CompetitorComparisonPage({ params }) {
  const { competitor: slug } = await params;
  const competitor = await getCompetitor(slug);

  if (!competitor) {
    notFound();
  }

  const breadcrumbItems = [
    { name: "Home", href: "/" },
    { name: "Comparisons", href: "/vs" },
    { name: `vs ${competitor.name}`, href: `/vs/${competitor.slug}` },
  ];

  // Build FAQ items
  const faqItems = competitor.faqs?.map((f) => ({
    question: f.q,
    answer: f.a,
  })) || [];

  // Add generic comparison FAQs
  faqItems.push(
    {
      question: `Is metricx better than ${competitor.name}?`,
      answer: `It depends on your needs. metricx is better for small to mid-sized e-commerce brands who want simple, affordable ad analytics with AI insights. ${competitor.name} may be better for ${competitor.targetAudience} who need ${competitor.pros?.[0]?.toLowerCase() || "advanced features"}.`,
    },
    {
      question: `How do I switch from ${competitor.name} to metricx?`,
      answer: `Switching is easy: 1) Sign up for metricx, 2) Connect your ad accounts (Meta, Google, TikTok), 3) Connect Shopify if applicable. Your data starts syncing immediately. Most brands run both tools briefly to compare data before fully switching.`,
    }
  );

  return (
    <>
      {/* Structured Data */}
      <JsonLd schema={generateBreadcrumbSchema(breadcrumbItems)} />
      <JsonLd schema={generateFAQSchema(faqItems)} />
      <JsonLd
        schema={generateProductComparisonSchema({
          products: [
            { name: "metricx", price: 29.99, rating: 4.9 },
            { name: competitor.name, price: null, rating: null },
          ],
        })}
      />

      {/* Breadcrumbs */}
      <Breadcrumbs items={breadcrumbItems} />

      {/* Hero */}
      <header className="mb-12">
        <div className="flex items-center gap-2 text-sm text-slate-500 mb-2">
          <Link href="/vs" className="hover:text-cyan-600">
            Comparisons
          </Link>
          <span>/</span>
          <span>{competitor.name}</span>
        </div>
        <h1 className="text-4xl font-bold text-slate-900 mb-4">
          metricx vs {competitor.name}
        </h1>
        <p className="text-lg text-slate-600 max-w-3xl">
          An honest comparison between metricx and {competitor.name}. See pricing,
          features, and which tool is right for your e-commerce business.
        </p>
      </header>

      {/* Key Comparison Points */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-slate-900 mb-6">
          At a Glance
        </h2>
        <div className="bg-white border border-slate-200 rounded-xl p-6">
          <div className="grid grid-cols-3 gap-4 pb-4 border-b border-slate-200 mb-4">
            <div className="font-semibold text-slate-900">Comparison</div>
            <div className="font-semibold text-slate-900 text-center">{competitor.name}</div>
            <div className="font-semibold text-cyan-600 text-center">metricx</div>
          </div>
          {Object.entries(competitor.comparisonPoints || {}).map(([key, data]) => (
            <ComparisonRow
              key={key}
              label={key.replace(/([A-Z])/g, " $1").replace(/^./, (s) => s.toUpperCase())}
              them={data.them}
              us={data.us}
              winner={data.winner}
              icon={
                key === "price" ? DollarSign :
                key === "setupTime" ? Clock :
                key === "aiCopilot" || key === "aiCapabilities" ? Sparkles :
                null
              }
            />
          ))}
        </div>
      </section>

      {/* Savings Calculator */}
      <section className="mb-12">
        <SavingsCalculator competitor={competitor} />
      </section>

      {/* Feature Comparison */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-slate-900 mb-6">
          Feature Comparison
        </h2>
        <FeatureComparisonTable competitor={competitor} />
      </section>

      {/* About Competitor */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-slate-900 mb-6">
          About {competitor.name}
        </h2>
        <p className="text-slate-600 mb-6">{competitor.description}</p>
        <ProsCons pros={competitor.pros} cons={competitor.cons} name={competitor.name} />
      </section>

      {/* Why metricx */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-slate-900 mb-6">
          Why Choose metricx
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="p-6 bg-cyan-50 border border-cyan-100 rounded-xl">
            <DollarSign className="w-8 h-8 text-cyan-600 mb-3" />
            <h3 className="font-semibold text-slate-900 mb-2">
              Flat-Rate Pricing
            </h3>
            <p className="text-slate-600">
              $29.99/month. No scaling with ad spend. Know exactly what you'll pay.
            </p>
          </div>
          <div className="p-6 bg-cyan-50 border border-cyan-100 rounded-xl">
            <Sparkles className="w-8 h-8 text-cyan-600 mb-3" />
            <h3 className="font-semibold text-slate-900 mb-2">
              AI Copilot
            </h3>
            <p className="text-slate-600">
              Ask questions in plain English. Get answers with data, not more dashboards.
            </p>
          </div>
          <div className="p-6 bg-cyan-50 border border-cyan-100 rounded-xl">
            <Zap className="w-8 h-8 text-cyan-600 mb-3" />
            <h3 className="font-semibold text-slate-900 mb-2">
              5-Minute Setup
            </h3>
            <p className="text-slate-600">
              Connect accounts and see data immediately. No complex implementation.
            </p>
          </div>
          <div className="p-6 bg-cyan-50 border border-cyan-100 rounded-xl">
            <Shield className="w-8 h-8 text-cyan-600 mb-3" />
            <h3 className="font-semibold text-slate-900 mb-2">
              Verified Revenue
            </h3>
            <p className="text-slate-600">
              Shopify integration verifies actual revenue, not just platform-reported.
            </p>
          </div>
        </div>
      </section>

      {/* FAQs */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-slate-900 mb-6">
          Frequently Asked Questions
        </h2>
        <FAQ items={faqItems} />
      </section>

      {/* Related Comparisons */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-slate-900 mb-6">
          Related Comparisons
        </h2>
        <div className="flex flex-wrap gap-4">
          <Link
            href={`/alternatives/${competitor.slug}`}
            className="inline-flex items-center gap-2 px-4 py-2 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
          >
            Best {competitor.name} Alternative
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            href="/vs"
            className="inline-flex items-center gap-2 px-4 py-2 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
          >
            All Comparisons
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* CTA */}
      <CTABanner
        title={`Ready to try metricx?`}
        description={`See why e-commerce brands switch from ${competitor.name} to metricx for simpler, more affordable ad analytics.`}
        primaryCTA={{ text: "Start Free Trial", href: "/sign-up" }}
        secondaryCTA={{ text: "See All Features", href: "/#features" }}
      />
    </>
  );
}
