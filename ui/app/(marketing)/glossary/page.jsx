/**
 * Glossary Hub Page
 *
 * WHAT: A-Z index of all advertising and marketing terms
 * WHY: Hub page for SEO programmatic glossary, provides navigation to all term pages
 *
 * Related files:
 * - content/glossary/terms.json - Term data
 * - lib/seo/content-loader.js - Data loading
 * - components/seo/ - SEO components
 */

import Link from "next/link";
import { getGlossaryTerms, getGlossaryTermsByLetter } from "@/lib/seo/content-loader";
import { Breadcrumbs, CTABanner } from "@/components/seo";
import { JsonLd } from "@/components/seo/JsonLd";
import { generateBreadcrumbSchema, generateWebPageSchema } from "@/lib/seo/schemas";
import { Book, Search, ArrowRight } from "lucide-react";

/**
 * Generate metadata for the glossary hub page.
 */
export async function generateMetadata() {
  const terms = await getGlossaryTerms();

  return {
    title: "Ad Analytics Glossary | 500+ Marketing Terms Defined | metricx",
    description: `Comprehensive glossary of ${terms.length}+ advertising and marketing analytics terms. Learn definitions, formulas, and examples for ROAS, CPA, CTR, and more.`,
    keywords: [
      "ad analytics glossary",
      "marketing terms",
      "advertising definitions",
      "roas definition",
      "cpa meaning",
      "digital marketing glossary",
    ],
    openGraph: {
      title: "Ad Analytics Glossary | metricx",
      description: `Master ${terms.length}+ advertising terms with clear definitions and examples.`,
      type: "website",
      url: "https://www.metricx.ai/glossary",
    },
    twitter: {
      card: "summary_large_image",
      title: "Ad Analytics Glossary | metricx",
      description: `Master ${terms.length}+ advertising terms with clear definitions and examples.`,
    },
    alternates: {
      canonical: "https://www.metricx.ai/glossary",
    },
  };
}

/**
 * Group terms by first letter for A-Z navigation.
 */
function groupTermsByLetter(terms) {
  const grouped = {};
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");

  // Initialize all letters
  alphabet.forEach((letter) => {
    grouped[letter] = [];
  });

  // Group terms
  terms.forEach((term) => {
    const firstLetter = term.term.charAt(0).toUpperCase();
    if (grouped[firstLetter]) {
      grouped[firstLetter].push(term);
    }
  });

  return grouped;
}

/**
 * Glossary Hub Page Component
 */
export default async function GlossaryPage() {
  const terms = await getGlossaryTerms();
  const groupedTerms = groupTermsByLetter(terms);
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");

  // Get popular/featured terms
  const popularTerms = terms.filter((t) =>
    ["roas", "cpa", "ctr", "cpm", "cpc", "ltv", "cac", "aov"].includes(t.slug)
  );

  const breadcrumbItems = [
    { name: "Home", href: "/" },
    { name: "Glossary", href: "/glossary" },
  ];

  return (
    <>
      {/* Structured Data */}
      <JsonLd schema={generateBreadcrumbSchema(breadcrumbItems)} />
      <JsonLd
        schema={generateWebPageSchema({
          title: "Ad Analytics Glossary",
          description: `Comprehensive glossary of ${terms.length}+ advertising terms`,
          url: "https://www.metricx.ai/glossary",
        })}
      />

      {/* Breadcrumbs */}
      <Breadcrumbs items={breadcrumbItems} />

      {/* Hero Section */}
      <div className="mb-12">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-cyan-100 rounded-lg">
            <Book className="w-6 h-6 text-cyan-600" />
          </div>
          <span className="text-sm font-medium text-cyan-600">
            {terms.length}+ Terms
          </span>
        </div>
        <h1 className="text-4xl font-bold text-slate-900 mb-4">
          Ad Analytics Glossary
        </h1>
        <p className="text-lg text-slate-600 max-w-3xl">
          Master the language of digital advertising. Our comprehensive glossary covers
          every metric, term, and concept you need to understand your ad performance
          and make data-driven decisions.
        </p>
      </div>

      {/* A-Z Navigation */}
      <nav className="mb-12 sticky top-20 bg-white/95 backdrop-blur-sm py-4 -mx-4 px-4 border-b border-slate-200 z-10">
        <div className="flex flex-wrap gap-2 justify-center">
          {alphabet.map((letter) => {
            const hasTerms = groupedTerms[letter]?.length > 0;
            return (
              <a
                key={letter}
                href={hasTerms ? `#letter-${letter}` : undefined}
                className={`w-8 h-8 flex items-center justify-center rounded text-sm font-medium transition-colors ${
                  hasTerms
                    ? "bg-slate-100 text-slate-900 hover:bg-cyan-100 hover:text-cyan-700"
                    : "bg-slate-50 text-slate-300 cursor-default"
                }`}
              >
                {letter}
              </a>
            );
          })}
        </div>
      </nav>

      {/* Popular Terms */}
      <section className="mb-12">
        <h2 className="text-xl font-semibold text-slate-900 mb-4">
          Popular Terms
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {popularTerms.map((term) => (
            <Link
              key={term.slug}
              href={`/glossary/${term.slug}`}
              className="p-4 bg-gradient-to-br from-cyan-50 to-white border border-cyan-100 rounded-lg hover:border-cyan-300 transition-colors group"
            >
              <div className="font-semibold text-slate-900 group-hover:text-cyan-700">
                {term.term}
              </div>
              <div className="text-sm text-slate-500 truncate">
                {term.fullName}
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* All Terms by Letter */}
      <section className="space-y-12">
        {alphabet.map((letter) => {
          const letterTerms = groupedTerms[letter];
          if (letterTerms.length === 0) return null;

          return (
            <div key={letter} id={`letter-${letter}`} className="scroll-mt-32">
              <h2 className="text-2xl font-bold text-slate-900 mb-4 pb-2 border-b border-slate-200">
                {letter}
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {letterTerms.map((term) => (
                  <Link
                    key={term.slug}
                    href={`/glossary/${term.slug}`}
                    className="group p-4 bg-white border border-slate-200 rounded-lg hover:border-cyan-300 hover:shadow-sm transition-all"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="font-semibold text-slate-900 group-hover:text-cyan-700">
                          {term.term}
                        </h3>
                        {term.fullName && term.fullName !== term.term && (
                          <div className="text-sm text-slate-500">
                            {term.fullName}
                          </div>
                        )}
                        <p className="text-sm text-slate-600 mt-1 line-clamp-2">
                          {term.definition}
                        </p>
                      </div>
                      <ArrowRight className="w-4 h-4 text-slate-300 group-hover:text-cyan-500 flex-shrink-0 mt-1" />
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          );
        })}
      </section>

      {/* CTA Section */}
      <div className="mt-16">
        <CTABanner
          title="Track These Metrics Automatically"
          description="Stop calculating manually. metricx tracks ROAS, CPA, and all key metrics across Meta, Google, and TikTok in one dashboard."
          primaryCTA={{ text: "Start Free Trial", href: "/sign-up" }}
          secondaryCTA={{ text: "See Features", href: "/#features" }}
        />
      </div>
    </>
  );
}
