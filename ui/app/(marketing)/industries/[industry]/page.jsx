/**
 * Individual Industry Page
 *
 * WHAT: Deep dive page for each industry vertical
 * WHY: SEO page targeting "[industry] advertising" keywords
 *
 * Related files:
 * - content/industries/data.json - Industry data
 * - lib/seo/content-loader.js - Data loading
 */

import { notFound } from "next/navigation";
import Link from "next/link";
import { getIndustries, getIndustry } from "@/lib/seo/content-loader";
import { Breadcrumbs, FAQ, CTABanner } from "@/components/seo";
import { JsonLd } from "@/components/seo/JsonLd";
import { generateBreadcrumbSchema, generateFAQSchema, generateArticleSchema } from "@/lib/seo/schemas";
import {
  ArrowRight,
  TrendingUp,
  DollarSign,
  Target,
  AlertTriangle,
  CheckCircle2,
  Lightbulb,
  BarChart3,
  BookOpen,
} from "lucide-react";

/**
 * Generate static params for all industries.
 */
export async function generateStaticParams() {
  const industries = await getIndustries();
  return industries.map((i) => ({
    industry: i.slug,
  }));
}

/**
 * Generate metadata for industry page.
 */
export async function generateMetadata({ params }) {
  const { industry: slug } = await params;
  const industry = await getIndustry(slug);

  if (!industry) {
    return {
      title: "Industry Not Found | metricx",
    };
  }

  return {
    title: `${industry.name} Ad Analytics | Benchmarks & Strategies | metricx`,
    description: `${industry.name} advertising guide with benchmarks (${industry.targetROAS} ROAS target), platform recommendations, and optimization strategies.`,
    keywords: [
      `${industry.name.toLowerCase()} advertising`,
      `${industry.name.toLowerCase()} ad benchmarks`,
      `${industry.name.toLowerCase()} ecommerce analytics`,
      `${industry.name.toLowerCase()} roas`,
      `${industry.name.toLowerCase()} marketing`,
    ],
    openGraph: {
      title: `${industry.name} Ad Analytics | metricx`,
      description: industry.description,
      type: "article",
      url: `https://www.metricx.ai/industries/${industry.slug}`,
    },
    alternates: {
      canonical: `https://www.metricx.ai/industries/${industry.slug}`,
    },
  };
}

/**
 * KPI benchmarks component.
 */
function KPIBenchmarks({ benchmarks, targetROAS, averageAOV }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div className="p-4 bg-emerald-50 rounded-xl">
        <div className="flex items-center gap-2 mb-1 text-emerald-600">
          <TrendingUp className="w-4 h-4" />
          <span className="font-semibold">Target ROAS</span>
        </div>
        <div className="text-2xl font-bold text-emerald-700">{targetROAS}</div>
      </div>
      <div className="p-4 bg-blue-50 rounded-xl">
        <div className="flex items-center gap-2 mb-1 text-blue-600">
          <DollarSign className="w-4 h-4" />
          <span className="font-semibold">Avg AOV</span>
        </div>
        <div className="text-2xl font-bold text-blue-700">{averageAOV}</div>
      </div>
      {benchmarks?.cpa && (
        <div className="p-4 bg-amber-50 rounded-xl">
          <div className="flex items-center gap-2 mb-1 text-amber-600">
            <Target className="w-4 h-4" />
            <span className="font-semibold">Avg CPA</span>
          </div>
          <div className="text-2xl font-bold text-amber-700">{benchmarks.cpa}</div>
        </div>
      )}
      {benchmarks?.ctr && (
        <div className="p-4 bg-purple-50 rounded-xl">
          <div className="flex items-center gap-2 mb-1 text-purple-600">
            <BarChart3 className="w-4 h-4" />
            <span className="font-semibold">Avg CTR</span>
          </div>
          <div className="text-2xl font-bold text-purple-700">{benchmarks.ctr}</div>
        </div>
      )}
    </div>
  );
}

/**
 * Challenges section component.
 */
function Challenges({ challenges }) {
  if (!challenges || challenges.length === 0) return null;

  return (
    <div className="bg-amber-50 border border-amber-100 rounded-xl p-6">
      <div className="flex items-center gap-2 mb-4">
        <AlertTriangle className="w-5 h-5 text-amber-600" />
        <h3 className="font-semibold text-slate-900">Industry Challenges</h3>
      </div>
      <ul className="space-y-2">
        {challenges.map((challenge, index) => (
          <li key={index} className="flex items-start gap-2 text-slate-700">
            <span className="text-amber-500 mt-1">•</span>
            <span>{challenge}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * Strategies section component.
 */
function Strategies({ strategies }) {
  if (!strategies || strategies.length === 0) return null;

  return (
    <div className="bg-emerald-50 border border-emerald-100 rounded-xl p-6">
      <div className="flex items-center gap-2 mb-4">
        <CheckCircle2 className="w-5 h-5 text-emerald-600" />
        <h3 className="font-semibold text-slate-900">Recommended Strategies</h3>
      </div>
      <ul className="space-y-2">
        {strategies.map((strategy, index) => (
          <li key={index} className="flex items-start gap-2 text-slate-700">
            <span className="text-emerald-500 mt-1">✓</span>
            <span>{strategy}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * Best platforms component.
 */
function BestPlatforms({ platforms }) {
  if (!platforms || platforms.length === 0) return null;

  const platformNames = {
    meta: "Meta Ads",
    "meta-ads": "Meta Ads",
    google: "Google Ads",
    "google-ads": "Google Ads",
    "google-shopping": "Google Shopping",
    "google-search": "Google Search",
    tiktok: "TikTok Ads",
    "tiktok-ads": "TikTok Ads",
    pinterest: "Pinterest Ads",
    "pinterest-ads": "Pinterest Ads",
    snapchat: "Snapchat Ads",
    "snapchat-ads": "Snapchat Ads",
    linkedin: "LinkedIn Ads",
    "linkedin-ads": "LinkedIn Ads",
    youtube: "YouTube Ads",
    podcast: "Podcast Ads",
    amazon: "Amazon Ads",
    microsoft: "Microsoft Ads",
  };

  return (
    <div className="flex flex-wrap gap-2">
      {platforms.map((platform) => (
        <Link
          key={platform}
          href={`/platforms/${platform.includes("ads") ? platform : `${platform}-ads`}`}
          className="px-3 py-2 bg-white border border-slate-200 rounded-lg text-slate-700 hover:border-cyan-300 hover:text-cyan-700 transition-colors"
        >
          {platformNames[platform] || platform}
        </Link>
      ))}
    </div>
  );
}

/**
 * Related industries component.
 */
function RelatedIndustries({ slugs, industries }) {
  const related = slugs?.map((s) => industries.find((i) => i.slug === s)).filter(Boolean) || [];
  if (related.length === 0) return null;

  return (
    <div className="bg-slate-50 rounded-xl p-6">
      <h3 className="text-lg font-semibold text-slate-900 mb-4">Related Industries</h3>
      <div className="space-y-2">
        {related.map((i) => (
          <Link
            key={i.slug}
            href={`/industries/${i.slug}`}
            className="flex items-center justify-between p-3 bg-white rounded-lg border border-slate-200 hover:border-cyan-300 transition-colors group"
          >
            <span className="font-medium text-slate-900 group-hover:text-cyan-700">
              {i.name}
            </span>
            <ArrowRight className="w-4 h-4 text-slate-300 group-hover:text-cyan-500" />
          </Link>
        ))}
      </div>
    </div>
  );
}

/**
 * Individual Industry Page Component
 */
export default async function IndustryPage({ params }) {
  const { industry: slug } = await params;
  const industry = await getIndustry(slug);
  const allIndustries = await getIndustries();

  if (!industry) {
    notFound();
  }

  const breadcrumbItems = [
    { name: "Home", href: "/" },
    { name: "Industries", href: "/industries" },
    { name: industry.name, href: `/industries/${industry.slug}` },
  ];

  // Build FAQ items
  const faqItems = industry.faqs?.map((f) => ({
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
          title: `${industry.name} Ad Analytics Guide`,
          description: industry.description,
          url: `https://www.metricx.ai/industries/${industry.slug}`,
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
              <Link href="/industries" className="hover:text-cyan-600">
                Industries
              </Link>
            </div>
            <h1 className="text-4xl font-bold text-slate-900 mb-4">
              {industry.name} Ad Analytics
            </h1>
            <p className="text-lg text-slate-600">{industry.description}</p>
          </header>

          {/* KPI Benchmarks */}
          <section className="mb-8">
            <h2 className="text-2xl font-bold text-slate-900 mb-4">
              Industry Benchmarks
            </h2>
            <KPIBenchmarks
              benchmarks={industry.kpiBenchmarks}
              targetROAS={industry.targetROAS}
              averageAOV={industry.averageAOV}
            />
          </section>

          {/* Key Metrics */}
          {industry.keyMetrics && (
            <section className="mb-8">
              <h2 className="text-2xl font-bold text-slate-900 mb-4">
                Key Metrics to Track
              </h2>
              <div className="flex flex-wrap gap-2">
                {industry.keyMetrics.map((metric) => (
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

          {/* Best Platforms */}
          {industry.bestPlatforms && (
            <section className="mb-8">
              <h2 className="text-2xl font-bold text-slate-900 mb-4">
                Best Advertising Platforms
              </h2>
              <BestPlatforms platforms={industry.bestPlatforms} />
            </section>
          )}

          {/* Challenges */}
          <section className="mb-8">
            <Challenges challenges={industry.challenges} />
          </section>

          {/* Strategies */}
          <section className="mb-8">
            <Strategies strategies={industry.strategies} />
          </section>

          {/* Case Study Snippet */}
          {industry.caseStudySnippet && (
            <div className="flex items-start gap-3 p-4 bg-gradient-to-r from-cyan-500 to-cyan-600 text-white rounded-xl mb-8">
              <Lightbulb className="w-5 h-5 flex-shrink-0 mt-0.5" />
              <div>
                <div className="font-medium mb-1">metricx Insight</div>
                <div className="text-cyan-50 text-sm">{industry.caseStudySnippet}</div>
              </div>
            </div>
          )}

          {/* metricx Feature */}
          {industry.metricxFeature && (
            <div className="flex items-start gap-3 p-4 bg-slate-100 rounded-xl mb-8">
              <Lightbulb className="w-5 h-5 flex-shrink-0 mt-0.5 text-cyan-600" />
              <div>
                <div className="font-medium text-slate-900 mb-1">How metricx Helps</div>
                <div className="text-slate-600 text-sm">{industry.metricxFeature}</div>
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
            title={`Optimize Your ${industry.name} Ads`}
            description={`metricx helps ${industry.name.toLowerCase()} brands achieve better ROAS with AI-powered insights and accurate attribution.`}
            primaryCTA={{ text: "Start Free Trial", href: "/sign-up" }}
            secondaryCTA={{ text: "Learn More", href: "/#features" }}
            variant="inline"
          />
        </div>

        {/* Sidebar */}
        <aside className="space-y-6">
          {/* Related Industries */}
          <RelatedIndustries slugs={industry.relatedIndustries} industries={allIndustries} />

          {/* Quick Links */}
          <div className="bg-slate-50 rounded-xl p-6">
            <h3 className="text-lg font-semibold text-slate-900 mb-4">
              Quick Links
            </h3>
            <div className="space-y-2">
              <Link
                href="/tools/roas-calculator"
                className="flex items-center gap-2 text-slate-600 hover:text-cyan-600"
              >
                <BarChart3 className="w-4 h-4" />
                ROAS Calculator
              </Link>
              <Link
                href="/tools/cpa-calculator"
                className="flex items-center gap-2 text-slate-600 hover:text-cyan-600"
              >
                <Target className="w-4 h-4" />
                CPA Calculator
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

          {/* All Industries Link */}
          <Link
            href="/industries"
            className="flex items-center justify-center gap-2 p-4 bg-cyan-50 text-cyan-700 rounded-xl hover:bg-cyan-100 transition-colors font-medium"
          >
            View All Industries
            <ArrowRight className="w-4 h-4" />
          </Link>
        </aside>
      </div>
    </>
  );
}
