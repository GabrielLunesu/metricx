/**
 * Individual Platform Page
 *
 * WHAT: Deep dive page for each advertising platform
 * WHY: SEO page targeting "[platform] guide/tutorial" keywords
 *
 * Related files:
 * - content/platforms/data.json - Platform data
 * - lib/seo/content-loader.js - Data loading
 */

import { notFound } from "next/navigation";
import Link from "next/link";
import { getPlatforms, getPlatform } from "@/lib/seo/content-loader";
import { Breadcrumbs, FAQ, CTABanner } from "@/components/seo";
import { JsonLd } from "@/components/seo/JsonLd";
import { generateBreadcrumbSchema, generateFAQSchema, generateArticleSchema } from "@/lib/seo/schemas";
import {
  ArrowRight,
  CheckCircle2,
  XCircle,
  Target,
  LayoutGrid,
  Settings,
  Lightbulb,
  BookOpen,
} from "lucide-react";

/**
 * Generate static params for all platforms.
 */
export async function generateStaticParams() {
  const platforms = await getPlatforms();
  return platforms.map((p) => ({
    platform: p.slug,
  }));
}

/**
 * Generate metadata for platform page.
 */
export async function generateMetadata({ params }) {
  const { platform: slug } = await params;
  const platform = await getPlatform(slug);

  if (!platform) {
    return {
      title: "Platform Not Found | metricx",
    };
  }

  return {
    title: `${platform.name} Guide | Setup, Targeting & Best Practices | metricx`,
    description: `Complete ${platform.name} advertising guide. Learn setup, ad types, targeting options, and optimization strategies. ${platform.description.slice(0, 100)}`,
    keywords: [
      `${platform.name.toLowerCase()} guide`,
      `${platform.name.toLowerCase()} tutorial`,
      `${platform.name.toLowerCase()} advertising`,
      `${platform.name.toLowerCase()} setup`,
      `${platform.name.toLowerCase()} best practices`,
    ],
    openGraph: {
      title: `${platform.name} Guide | metricx`,
      description: platform.description,
      type: "article",
      url: `https://www.metricx.ai/platforms/${platform.slug}`,
    },
    alternates: {
      canonical: `https://www.metricx.ai/platforms/${platform.slug}`,
    },
  };
}

/**
 * Platform icon component.
 */
function PlatformIcon({ name, className = "" }) {
  const colors = {
    meta: "bg-blue-500",
    google: "bg-red-500",
    tiktok: "bg-slate-900",
    pinterest: "bg-red-600",
    snapchat: "bg-yellow-400",
    linkedin: "bg-blue-700",
    microsoft: "bg-blue-600",
    amazon: "bg-orange-500",
  };

  return (
    <div className={`w-16 h-16 rounded-xl ${colors[name.toLowerCase()] || "bg-slate-500"} flex items-center justify-center text-white font-bold text-2xl ${className}`}>
      {name.charAt(0).toUpperCase()}
    </div>
  );
}

/**
 * Ad types grid component.
 */
function AdTypesGrid({ adTypes }) {
  if (!adTypes || adTypes.length === 0) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {adTypes.map((adType, index) => (
        <div key={index} className="p-4 bg-slate-50 rounded-lg">
          <h4 className="font-semibold text-slate-900 mb-1">{adType.name}</h4>
          <p className="text-sm text-slate-600">{adType.description}</p>
        </div>
      ))}
    </div>
  );
}

/**
 * Placements list component.
 */
function PlacementsList({ placements }) {
  if (!placements || placements.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2">
      {placements.map((placement, index) => (
        <span
          key={index}
          className="px-3 py-1 bg-white border border-slate-200 rounded-full text-sm text-slate-700"
        >
          {placement}
        </span>
      ))}
    </div>
  );
}

/**
 * Pros and cons component.
 */
function ProsAndCons({ pros, cons }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* Pros */}
      <div className="bg-emerald-50 rounded-xl p-6">
        <h3 className="font-semibold text-emerald-800 mb-4 flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5" />
          Pros
        </h3>
        <ul className="space-y-2">
          {pros?.map((pro, index) => (
            <li key={index} className="flex items-start gap-2 text-emerald-700">
              <span className="text-emerald-500 mt-1">+</span>
              <span>{pro}</span>
            </li>
          ))}
        </ul>
      </div>
      {/* Cons */}
      <div className="bg-red-50 rounded-xl p-6">
        <h3 className="font-semibold text-red-800 mb-4 flex items-center gap-2">
          <XCircle className="w-5 h-5" />
          Cons
        </h3>
        <ul className="space-y-2">
          {cons?.map((con, index) => (
            <li key={index} className="flex items-start gap-2 text-red-700">
              <span className="text-red-500 mt-1">−</span>
              <span>{con}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

/**
 * Setup steps component.
 */
function SetupSteps({ steps }) {
  if (!steps || steps.length === 0) return null;

  return (
    <div className="space-y-4">
      {steps.map((step, index) => (
        <div key={index} className="flex gap-4">
          <div className="w-8 h-8 flex items-center justify-center bg-cyan-100 text-cyan-700 font-semibold rounded-full flex-shrink-0">
            {index + 1}
          </div>
          <div className="flex-1 pt-1">
            <p className="text-slate-700">{step}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Best practices component.
 */
function BestPractices({ practices }) {
  if (!practices || practices.length === 0) return null;

  return (
    <div className="bg-cyan-50 border border-cyan-100 rounded-xl p-6">
      <div className="flex items-center gap-2 mb-4">
        <Lightbulb className="w-5 h-5 text-cyan-600" />
        <h3 className="font-semibold text-slate-900">Best Practices</h3>
      </div>
      <ul className="space-y-2">
        {practices.map((practice, index) => (
          <li key={index} className="flex items-start gap-2 text-slate-700">
            <span className="text-cyan-500 mt-1">•</span>
            <span>{practice}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * Related platforms component.
 */
function RelatedPlatforms({ currentSlug, platforms }) {
  const related = platforms.filter((p) => p.slug !== currentSlug).slice(0, 4);

  return (
    <div className="bg-slate-50 rounded-xl p-6">
      <h3 className="text-lg font-semibold text-slate-900 mb-4">Other Platforms</h3>
      <div className="space-y-2">
        {related.map((p) => (
          <Link
            key={p.slug}
            href={`/platforms/${p.slug}`}
            className="flex items-center justify-between p-3 bg-white rounded-lg border border-slate-200 hover:border-cyan-300 transition-colors group"
          >
            <span className="font-medium text-slate-900 group-hover:text-cyan-700">
              {p.name}
            </span>
            <ArrowRight className="w-4 h-4 text-slate-300 group-hover:text-cyan-500" />
          </Link>
        ))}
      </div>
    </div>
  );
}

/**
 * Individual Platform Page Component
 */
export default async function PlatformPage({ params }) {
  const { platform: slug } = await params;
  const platform = await getPlatform(slug);
  const allPlatforms = await getPlatforms();

  if (!platform) {
    notFound();
  }

  const breadcrumbItems = [
    { name: "Home", href: "/" },
    { name: "Platforms", href: "/platforms" },
    { name: platform.name, href: `/platforms/${platform.slug}` },
  ];

  // Build FAQ items
  const faqItems = platform.faqs?.map((f) => ({
    question: f.question,
    answer: f.answer,
  })) || [];

  return (
    <>
      {/* Structured Data */}
      <JsonLd schema={generateBreadcrumbSchema(breadcrumbItems)} />
      {faqItems.length > 0 && <JsonLd schema={generateFAQSchema(faqItems)} />}
      <JsonLd
        schema={generateArticleSchema({
          title: `${platform.name} Advertising Guide`,
          description: platform.description,
          url: `https://www.metricx.ai/platforms/${platform.slug}`,
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
            <div className="flex items-start gap-4 mb-4">
              <PlatformIcon name={platform.icon || platform.slug} />
              <div>
                <h1 className="text-4xl font-bold text-slate-900">{platform.name}</h1>
                {platform.aliases && platform.aliases.length > 0 && (
                  <p className="text-slate-500">
                    Also known as: {platform.aliases.join(", ")}
                  </p>
                )}
              </div>
            </div>
            <p className="text-lg text-slate-600">{platform.description}</p>
            <p className="text-sm text-slate-500 mt-2">
              <strong>Best for:</strong> {platform.targetAudience}
            </p>
          </header>

          {/* Key Metrics */}
          {platform.keyMetrics && (
            <section className="mb-8">
              <div className="flex flex-wrap gap-2">
                {platform.keyMetrics.map((metric) => (
                  <Link
                    key={metric}
                    href={`/glossary/${metric}`}
                    className="px-3 py-1 bg-cyan-50 text-cyan-700 text-sm rounded-full hover:bg-cyan-100"
                  >
                    {metric.toUpperCase()}
                  </Link>
                ))}
              </div>
            </section>
          )}

          {/* Ad Types */}
          <section className="mb-8">
            <div className="flex items-center gap-2 mb-4">
              <LayoutGrid className="w-5 h-5 text-slate-600" />
              <h2 className="text-2xl font-bold text-slate-900">Ad Types</h2>
            </div>
            <AdTypesGrid adTypes={platform.adTypes} />
          </section>

          {/* Placements */}
          {platform.placements && (
            <section className="mb-8">
              <div className="flex items-center gap-2 mb-4">
                <Target className="w-5 h-5 text-slate-600" />
                <h2 className="text-2xl font-bold text-slate-900">Placements</h2>
              </div>
              <PlacementsList placements={platform.placements} />
            </section>
          )}

          {/* Targeting Capabilities */}
          {platform.targetingCapabilities && (
            <section className="mb-8">
              <h2 className="text-2xl font-bold text-slate-900 mb-4">
                Targeting Capabilities
              </h2>
              <ul className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {platform.targetingCapabilities.map((cap, index) => (
                  <li key={index} className="flex items-center gap-2 text-slate-700">
                    <CheckCircle2 className="w-4 h-4 text-cyan-500 flex-shrink-0" />
                    <span>{cap}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* Pros and Cons */}
          <section className="mb-8">
            <h2 className="text-2xl font-bold text-slate-900 mb-4">Pros & Cons</h2>
            <ProsAndCons pros={platform.pros} cons={platform.cons} />
          </section>

          {/* Setup Steps */}
          {platform.setupSteps && (
            <section className="mb-8">
              <div className="flex items-center gap-2 mb-4">
                <Settings className="w-5 h-5 text-slate-600" />
                <h2 className="text-2xl font-bold text-slate-900">Getting Started</h2>
              </div>
              <SetupSteps steps={platform.setupSteps} />
            </section>
          )}

          {/* Best Practices */}
          <section className="mb-8">
            <BestPractices practices={platform.bestPractices} />
          </section>

          {/* metricx Feature */}
          {platform.metricxFeature && (
            <div className="flex items-start gap-3 p-4 bg-gradient-to-r from-cyan-500 to-cyan-600 text-white rounded-xl mb-8">
              <Lightbulb className="w-5 h-5 flex-shrink-0 mt-0.5" />
              <div>
                <div className="font-medium mb-1">How metricx Helps</div>
                <div className="text-cyan-50 text-sm">{platform.metricxFeature}</div>
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
            title={`Track ${platform.name} Performance`}
            description={`metricx integrates with ${platform.name} to give you real-time performance insights and AI-powered recommendations.`}
            primaryCTA={{ text: "Start Free Trial", href: "/sign-up" }}
            secondaryCTA={{ text: "Learn More", href: "/#features" }}
            variant="inline"
          />
        </div>

        {/* Sidebar */}
        <aside className="space-y-6">
          {/* Related Platforms */}
          <RelatedPlatforms currentSlug={platform.slug} platforms={allPlatforms} />

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
                <BookOpen className="w-4 h-4" />
                Free Calculators
              </Link>
              <Link
                href="/glossary"
                className="flex items-center gap-2 text-slate-600 hover:text-cyan-600"
              >
                <BookOpen className="w-4 h-4" />
                Glossary
              </Link>
              <Link
                href="/vs"
                className="flex items-center gap-2 text-slate-600 hover:text-cyan-600"
              >
                <BookOpen className="w-4 h-4" />
                Tool Comparisons
              </Link>
            </div>
          </div>
        </aside>
      </div>
    </>
  );
}
