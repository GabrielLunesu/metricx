/**
 * Individual Glossary Term Page
 *
 * WHAT: Dynamic page for each glossary term
 * WHY: Programmatic SEO page targeting "[term] definition" keywords
 *
 * Related files:
 * - content/glossary/terms.json - Term data
 * - lib/seo/content-loader.js - Data loading
 * - components/seo/ - SEO components
 */

import { notFound } from "next/navigation";
import Link from "next/link";
import { getGlossaryTerms, getGlossaryTerm, getGlossaryTermsByCategory } from "@/lib/seo/content-loader";
import { getRelatedGlossaryTerms } from "@/lib/seo/internal-links";
import { Breadcrumbs, FAQ, RelatedContent, CTABanner } from "@/components/seo";
import { JsonLd } from "@/components/seo/JsonLd";
import {
  generateBreadcrumbSchema,
  generateFAQSchema,
  generateDefinedTermSchema,
  generateArticleSchema,
} from "@/lib/seo/schemas";
import { Calculator, BookOpen, ArrowRight, Lightbulb, ExternalLink } from "lucide-react";

/**
 * Generate static params for all glossary terms.
 */
export async function generateStaticParams() {
  const terms = await getGlossaryTerms();
  return terms.map((term) => ({
    term: term.slug,
  }));
}

/**
 * Generate metadata for individual term page.
 */
export async function generateMetadata({ params }) {
  const { term: termSlug } = await params;
  const term = await getGlossaryTerm(termSlug);

  if (!term) {
    return {
      title: "Term Not Found | metricx Glossary",
    };
  }

  const title = term.fullName && term.fullName !== term.term
    ? `${term.term} (${term.fullName}) - Definition & Formula | metricx`
    : `${term.term} - Definition, Formula & Examples | metricx`;

  const description = `Learn what ${term.term} means in advertising. ${term.definition.slice(0, 120)}...`;

  return {
    title,
    description,
    keywords: [
      `${term.term.toLowerCase()} definition`,
      `what is ${term.term.toLowerCase()}`,
      `${term.term.toLowerCase()} formula`,
      `${term.term.toLowerCase()} meaning`,
      `${term.term.toLowerCase()} advertising`,
    ],
    openGraph: {
      title: `${term.term} Definition | metricx Glossary`,
      description,
      type: "article",
      url: `https://www.metricx.ai/glossary/${term.slug}`,
    },
    twitter: {
      card: "summary",
      title: `${term.term} Definition | metricx`,
      description,
    },
    alternates: {
      canonical: `https://www.metricx.ai/glossary/${term.slug}`,
    },
  };
}

/**
 * Term definition card component.
 */
function DefinitionCard({ term }) {
  return (
    <div className="bg-gradient-to-br from-cyan-50 to-white border border-cyan-100 rounded-xl p-6 mb-8">
      <div className="flex items-start gap-4">
        <div className="p-3 bg-cyan-100 rounded-lg">
          <BookOpen className="w-6 h-6 text-cyan-600" />
        </div>
        <div className="flex-1">
          <h2 className="text-lg font-semibold text-slate-900 mb-2">Definition</h2>
          <p className="text-slate-700 leading-relaxed">{term.definition}</p>
        </div>
      </div>
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
 * Related terms sidebar component.
 */
function RelatedTerms({ terms }) {
  if (!terms || terms.length === 0) return null;

  return (
    <div className="bg-slate-50 rounded-xl p-6">
      <h3 className="text-lg font-semibold text-slate-900 mb-4">Related Terms</h3>
      <div className="space-y-2">
        {terms.map((t) => (
          <Link
            key={t.slug}
            href={`/glossary/${t.slug}`}
            className="flex items-center justify-between p-3 bg-white rounded-lg border border-slate-200 hover:border-cyan-300 transition-colors group"
          >
            <div>
              <div className="font-medium text-slate-900 group-hover:text-cyan-700">
                {t.term}
              </div>
              {t.fullName && t.fullName !== t.term && (
                <div className="text-sm text-slate-500">{t.fullName}</div>
              )}
            </div>
            <ArrowRight className="w-4 h-4 text-slate-300 group-hover:text-cyan-500" />
          </Link>
        ))}
      </div>
    </div>
  );
}

/**
 * Calculator link component if relevant.
 */
function CalculatorLink({ term }) {
  const calculatorMap = {
    roas: { name: "ROAS Calculator", slug: "roas-calculator" },
    cpa: { name: "CPA Calculator", slug: "cpa-calculator" },
    cpm: { name: "CPM Calculator", slug: "cpm-calculator" },
    ctr: { name: "CTR Calculator", slug: "ctr-calculator" },
    cpc: { name: "CPC Calculator", slug: "cpc-calculator" },
  };

  const calculator = calculatorMap[term.slug];
  if (!calculator) return null;

  return (
    <Link
      href={`/tools/${calculator.slug}`}
      className="flex items-center gap-3 p-4 bg-cyan-50 border border-cyan-200 rounded-xl hover:bg-cyan-100 transition-colors group mb-8"
    >
      <div className="p-2 bg-cyan-100 rounded-lg group-hover:bg-cyan-200">
        <Calculator className="w-5 h-5 text-cyan-600" />
      </div>
      <div className="flex-1">
        <div className="font-medium text-slate-900">Try our {calculator.name}</div>
        <div className="text-sm text-slate-600">
          Calculate your {term.term} instantly with our free tool
        </div>
      </div>
      <ArrowRight className="w-5 h-5 text-cyan-500" />
    </Link>
  );
}

/**
 * Metricx feature callout.
 */
function MetricxFeature({ feature }) {
  if (!feature) return null;

  return (
    <div className="flex items-start gap-3 p-4 bg-gradient-to-r from-cyan-500 to-cyan-600 text-white rounded-xl mb-8">
      <Lightbulb className="w-5 h-5 flex-shrink-0 mt-0.5" />
      <div>
        <div className="font-medium mb-1">How metricx Helps</div>
        <div className="text-cyan-50 text-sm">{feature}</div>
      </div>
    </div>
  );
}

/**
 * Individual Glossary Term Page Component
 */
export default async function GlossaryTermPage({ params }) {
  const { term: termSlug } = await params;
  const term = await getGlossaryTerm(termSlug);

  if (!term) {
    notFound();
  }

  // Get related terms
  const relatedTerms = await getRelatedGlossaryTerms(term.slug, term.relatedTerms || []);

  // Get terms in same category
  const categoryTerms = await getGlossaryTermsByCategory(term.category);
  const siblingTerms = categoryTerms
    .filter((t) => t.slug !== term.slug)
    .slice(0, 4);

  const breadcrumbItems = [
    { name: "Home", href: "/" },
    { name: "Glossary", href: "/glossary" },
    { name: term.term, href: `/glossary/${term.slug}` },
  ];

  return (
    <>
      {/* Structured Data */}
      <JsonLd schema={generateBreadcrumbSchema(breadcrumbItems)} />
      <JsonLd schema={generateDefinedTermSchema(term)} />
      {term.faqs && term.faqs.length > 0 && (
        <JsonLd schema={generateFAQSchema(term.faqs.map((f) => ({ question: f.q, answer: f.a })))} />
      )}
      <JsonLd
        schema={generateArticleSchema({
          title: `${term.term} - Definition & Formula`,
          description: term.definition,
          url: `https://www.metricx.ai/glossary/${term.slug}`,
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
              <Link href="/glossary" className="hover:text-cyan-600">
                Glossary
              </Link>
              <span>/</span>
              <span className="capitalize">{term.category?.replace("-", " ")}</span>
            </div>
            <h1 className="text-4xl font-bold text-slate-900 mb-2">{term.term}</h1>
            {term.fullName && term.fullName !== term.term && (
              <p className="text-xl text-slate-600">{term.fullName}</p>
            )}
          </header>

          {/* Definition */}
          <DefinitionCard term={term} />

          {/* Calculator Link */}
          <CalculatorLink term={term} />

          {/* Formula */}
          {term.formula && (
            <FormulaCard formula={term.formula} example={term.example} />
          )}

          {/* metricx Feature */}
          <MetricxFeature feature={term.metricxFeature} />

          {/* FAQs */}
          {term.faqs && term.faqs.length > 0 && (
            <section className="mb-8">
              <h2 className="text-2xl font-bold text-slate-900 mb-4">
                Frequently Asked Questions
              </h2>
              <FAQ
                items={term.faqs.map((f) => ({
                  question: f.q,
                  answer: f.a,
                }))}
              />
            </section>
          )}

          {/* CTA */}
          <CTABanner
            title={`Track ${term.term} Automatically`}
            description={`Stop calculating ${term.term} manually. metricx tracks all your key metrics across Meta, Google, and TikTok in one dashboard.`}
            primaryCTA={{ text: "Start Free Trial", href: "/sign-up" }}
            secondaryCTA={{ text: "Learn More", href: "/#features" }}
            variant="inline"
          />
        </div>

        {/* Sidebar */}
        <aside className="space-y-6">
          {/* Related Terms */}
          {relatedTerms.length > 0 && <RelatedTerms terms={relatedTerms} />}

          {/* More in Category */}
          {siblingTerms.length > 0 && (
            <div className="bg-slate-50 rounded-xl p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-4">
                More {term.category?.replace("-", " ")} Terms
              </h3>
              <div className="space-y-2">
                {siblingTerms.map((t) => (
                  <Link
                    key={t.slug}
                    href={`/glossary/${t.slug}`}
                    className="flex items-center justify-between p-3 bg-white rounded-lg border border-slate-200 hover:border-cyan-300 transition-colors group"
                  >
                    <span className="font-medium text-slate-900 group-hover:text-cyan-700">
                      {t.term}
                    </span>
                    <ArrowRight className="w-4 h-4 text-slate-300 group-hover:text-cyan-500" />
                  </Link>
                ))}
              </div>
            </div>
          )}

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
                href="/blog"
                className="flex items-center gap-2 text-slate-600 hover:text-cyan-600"
              >
                <BookOpen className="w-4 h-4" />
                Blog & Guides
              </Link>
              <Link
                href="/vs"
                className="flex items-center gap-2 text-slate-600 hover:text-cyan-600"
              >
                <ExternalLink className="w-4 h-4" />
                Tool Comparisons
              </Link>
            </div>
          </div>
        </aside>
      </div>
    </>
  );
}
