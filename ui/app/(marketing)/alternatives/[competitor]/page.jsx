/**
 * Individual Alternative Page
 *
 * WHAT: Dynamic page targeting "[competitor] alternative" keywords
 * WHY: SEO page for "alternative to X" search intent
 *
 * Related files:
 * - content/competitors/data.json - Competitor data
 * - /vs/[competitor]/page.jsx - Comparison page
 */

import { notFound } from "next/navigation";
import Link from "next/link";
import { getCompetitors, getCompetitor } from "@/lib/seo/content-loader";
import { Breadcrumbs, FAQ, CTABanner } from "@/components/seo";
import { JsonLd } from "@/components/seo/JsonLd";
import {
  generateBreadcrumbSchema,
  generateFAQSchema,
  generateWebPageSchema,
} from "@/lib/seo/schemas";
import {
  Check,
  X,
  ArrowRight,
  DollarSign,
  Clock,
  Sparkles,
  Shield,
  Zap,
  Star,
} from "lucide-react";

/**
 * Generate static params for all alternatives.
 */
export async function generateStaticParams() {
  const competitors = await getCompetitors();
  return competitors.map((c) => ({
    competitor: c.slug,
  }));
}

/**
 * Generate metadata for alternative page.
 */
export async function generateMetadata({ params }) {
  const { competitor: slug } = await params;
  const competitor = await getCompetitor(slug);

  if (!competitor) {
    return {
      title: "Alternative Not Found | metricx",
    };
  }

  const savings = competitor.comparisonPoints?.price?.savings || "";

  return {
    title: `Best ${competitor.name} Alternative (2026) | metricx - Save ${savings || "70%+"}`,
    description: `Looking for a ${competitor.name} alternative? metricx offers the same features at $29.99/month vs ${competitor.pricing}. Simpler setup, AI-powered insights, Shopify verified.`,
    keywords: [
      `${competitor.name.toLowerCase()} alternative`,
      `${competitor.name.toLowerCase()} alternatives`,
      `best ${competitor.name.toLowerCase()} alternative`,
      `cheaper ${competitor.name.toLowerCase()}`,
      `${competitor.name.toLowerCase()} competitor`,
    ],
    openGraph: {
      title: `Best ${competitor.name} Alternative | metricx`,
      description: `Save ${savings || "70%+"} switching from ${competitor.name} to metricx.`,
      type: "article",
      url: `https://www.metricx.ai/alternatives/${competitor.slug}`,
    },
    twitter: {
      card: "summary_large_image",
      title: `Best ${competitor.name} Alternative | metricx`,
      description: `Simpler, more affordable ad analytics than ${competitor.name}.`,
    },
    alternates: {
      canonical: `https://www.metricx.ai/alternatives/${competitor.slug}`,
    },
  };
}

/**
 * Reasons to switch component.
 */
function ReasonsToSwitch({ competitor }) {
  const reasons = [
    {
      icon: DollarSign,
      title: "Save " + (competitor.comparisonPoints?.price?.savings || "70%+"),
      description: `${competitor.pricing} vs $29.99/month. No scaling with ad spend.`,
    },
    {
      icon: Zap,
      title: "Faster Setup",
      description: "5-minute setup vs " + (competitor.comparisonPoints?.setupTime?.them || "30+ minutes") + ". Connect and go.",
    },
    {
      icon: Sparkles,
      title: "AI-Powered",
      description: "Ask questions in plain English. Get answers with data.",
    },
    {
      icon: Shield,
      title: "Shopify Verified",
      description: "Real revenue data, not just platform-reported numbers.",
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {reasons.map((reason, i) => (
        <div
          key={i}
          className="p-6 bg-gradient-to-br from-cyan-50 to-white border border-cyan-100 rounded-xl"
        >
          <reason.icon className="w-8 h-8 text-cyan-600 mb-3" />
          <h3 className="font-semibold text-slate-900 mb-2">{reason.title}</h3>
          <p className="text-slate-600">{reason.description}</p>
        </div>
      ))}
    </div>
  );
}

/**
 * Migration steps component.
 */
function MigrationSteps() {
  const steps = [
    {
      number: 1,
      title: "Sign up for metricx",
      description: "Start your free trial - no credit card required.",
    },
    {
      number: 2,
      title: "Connect your ad accounts",
      description: "Meta, Google, and TikTok connect in one click via OAuth.",
    },
    {
      number: 3,
      title: "Connect Shopify (optional)",
      description: "Get verified revenue data for accurate attribution.",
    },
    {
      number: 4,
      title: "Start seeing insights",
      description: "Your data syncs immediately. Ask the AI any question.",
    },
  ];

  return (
    <div className="space-y-4">
      {steps.map((step) => (
        <div
          key={step.number}
          className="flex items-start gap-4 p-4 bg-white border border-slate-200 rounded-lg"
        >
          <div className="w-8 h-8 flex items-center justify-center bg-cyan-100 text-cyan-700 font-semibold rounded-full flex-shrink-0">
            {step.number}
          </div>
          <div>
            <h4 className="font-medium text-slate-900">{step.title}</h4>
            <p className="text-sm text-slate-600">{step.description}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Pain points component.
 */
function PainPoints({ competitor }) {
  return (
    <div className="bg-slate-50 rounded-xl p-6">
      <h3 className="font-semibold text-slate-900 mb-4">
        Common {competitor.name} Frustrations
      </h3>
      <ul className="space-y-3">
        {competitor.cons?.map((con, i) => (
          <li key={i} className="flex items-start gap-2 text-slate-600">
            <X className="w-5 h-5 text-red-400 flex-shrink-0" />
            <span>{con}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * How metricx solves component.
 */
function HowMetricxSolves({ competitor }) {
  const solutions = [
    "Flat $29.99/month - no surprises",
    "5-minute setup - no implementation needed",
    "AI answers questions - no dashboard hunting",
    "Shopify-verified revenue - not inflated platform data",
    "All platforms in one view - Meta, Google, TikTok",
  ];

  return (
    <div className="bg-cyan-50 border border-cyan-100 rounded-xl p-6">
      <h3 className="font-semibold text-slate-900 mb-4">
        How metricx Solves These
      </h3>
      <ul className="space-y-3">
        {solutions.map((solution, i) => (
          <li key={i} className="flex items-start gap-2 text-slate-700">
            <Check className="w-5 h-5 text-emerald-500 flex-shrink-0" />
            <span>{solution}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * Individual Alternative Page Component
 */
export default async function AlternativePage({ params }) {
  const { competitor: slug } = await params;
  const competitor = await getCompetitor(slug);

  if (!competitor) {
    notFound();
  }

  const breadcrumbItems = [
    { name: "Home", href: "/" },
    { name: "Alternatives", href: "/alternatives" },
    { name: `${competitor.name} Alternative`, href: `/alternatives/${competitor.slug}` },
  ];

  // Build FAQ items
  const faqItems = [
    {
      question: `What is the best ${competitor.name} alternative?`,
      answer: `metricx is the best ${competitor.name} alternative for most e-commerce brands. It offers similar core features (multi-platform analytics, Shopify integration, AI insights) at ${competitor.comparisonPoints?.price?.savings || "70%+"} lower cost with faster setup.`,
    },
    {
      question: `How does metricx compare to ${competitor.name}?`,
      answer: `metricx costs $29.99/month vs ${competitor.pricing}. Setup takes 5 minutes vs ${competitor.comparisonPoints?.setupTime?.them || "30+ minutes"}. Both track Meta, Google, and TikTok ads, but metricx focuses on simplicity and AI-powered insights vs ${competitor.name}'s more complex dashboards.`,
    },
    {
      question: `Can I migrate from ${competitor.name} to metricx?`,
      answer: `Yes, migration is seamless. Sign up for metricx, connect your ad accounts (they're independent of ${competitor.name}), and you'll have data immediately. Most brands run both briefly to compare before fully switching.`,
    },
    {
      question: `Is metricx missing any ${competitor.name} features?`,
      answer: `metricx focuses on core analytics that 90% of e-commerce brands need. If you require ${competitor.pros?.[0]?.toLowerCase() || "advanced enterprise features"}, ${competitor.name} might be better. For most SMBs, metricx provides everything needed at a fraction of the cost.`,
    },
  ];

  return (
    <>
      {/* Structured Data */}
      <JsonLd schema={generateBreadcrumbSchema(breadcrumbItems)} />
      <JsonLd schema={generateFAQSchema(faqItems)} />
      <JsonLd
        schema={generateWebPageSchema({
          title: `Best ${competitor.name} Alternative`,
          description: `metricx is the best alternative to ${competitor.name} for e-commerce ad analytics`,
          url: `https://www.metricx.ai/alternatives/${competitor.slug}`,
        })}
      />

      {/* Breadcrumbs */}
      <Breadcrumbs items={breadcrumbItems} />

      {/* Hero */}
      <header className="mb-12">
        <div className="flex items-center gap-2 text-sm text-slate-500 mb-2">
          <Link href="/alternatives" className="hover:text-cyan-600">
            Alternatives
          </Link>
          <span>/</span>
          <span>{competitor.name}</span>
        </div>
        <h1 className="text-4xl font-bold text-slate-900 mb-4">
          Best {competitor.name} Alternative
        </h1>
        <p className="text-lg text-slate-600 max-w-3xl">
          Looking for a {competitor.name} alternative? metricx offers simpler,
          more affordable ad analytics for e-commerce brands who don't need
          enterprise complexity.
        </p>

        {/* Quick Stats */}
        <div className="flex flex-wrap gap-6 mt-8">
          <div className="flex items-center gap-2">
            <DollarSign className="w-5 h-5 text-emerald-500" />
            <span className="text-slate-900">
              Save <strong>{competitor.comparisonPoints?.price?.savings || "70%+"}</strong>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Clock className="w-5 h-5 text-cyan-500" />
            <span className="text-slate-900">
              <strong>5-minute</strong> setup
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Star className="w-5 h-5 text-amber-500" />
            <span className="text-slate-900">
              <strong>4.9/5</strong> rating
            </span>
          </div>
        </div>
      </header>

      {/* Reasons to Switch */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-slate-900 mb-6">
          Why Switch from {competitor.name}
        </h2>
        <ReasonsToSwitch competitor={competitor} />
      </section>

      {/* Pain Points + Solutions */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-slate-900 mb-6">
          {competitor.name} Pain Points & How metricx Helps
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <PainPoints competitor={competitor} />
          <HowMetricxSolves competitor={competitor} />
        </div>
      </section>

      {/* Migration Steps */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-slate-900 mb-6">
          How to Switch to metricx
        </h2>
        <MigrationSteps />
      </section>

      {/* FAQs */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-slate-900 mb-6">
          Frequently Asked Questions
        </h2>
        <FAQ items={faqItems} />
      </section>

      {/* Related Links */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-slate-900 mb-6">
          Learn More
        </h2>
        <div className="flex flex-wrap gap-4">
          <Link
            href={`/vs/${competitor.slug}`}
            className="inline-flex items-center gap-2 px-4 py-2 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
          >
            Detailed Comparison
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            href="/vs"
            className="inline-flex items-center gap-2 px-4 py-2 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
          >
            All Comparisons
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            href="/#features"
            className="inline-flex items-center gap-2 px-4 py-2 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
          >
            metricx Features
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* CTA */}
      <CTABanner
        title={`Ready to Switch from ${competitor.name}?`}
        description={`Start your free trial and see why e-commerce brands choose metricx.`}
        primaryCTA={{ text: "Start Free Trial", href: "/sign-up" }}
        secondaryCTA={{ text: "See Pricing", href: "/#pricing" }}
      />
    </>
  );
}
