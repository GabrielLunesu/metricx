/**
 * FAQ Accordion Component with Schema
 *
 * WHAT: Renders an FAQ section with collapsible answers and JSON-LD schema
 * WHY: FAQ schema can trigger rich snippets in search results, showing
 *      questions and answers directly in the SERP
 *
 * Related files:
 * - lib/seo/schemas.js - FAQPage schema generation
 *
 * @example
 * import { FAQ } from '@/components/seo/FAQ';
 *
 * <FAQ
 *   items={[
 *     { question: "What is ROAS?", answer: "ROAS stands for..." },
 *     { question: "What is a good ROAS?", answer: "A good ROAS depends..." }
 *   ]}
 * />
 */

"use client";

import { useState } from "react";
import { ChevronDown, Plus, Minus } from "lucide-react";
import { JsonLd } from "./JsonLd";
import { generateFAQSchema } from "@/lib/seo/schemas";

/**
 * FAQ accordion with schema markup.
 *
 * @param {Object} props - Component props
 * @param {Array<{question: string, answer: string} | {q: string, a: string}>} props.items - FAQ items
 * @param {string} [props.title] - Optional section title
 * @param {string} [props.className] - Additional CSS classes
 * @param {boolean} [props.showSchema=true] - Whether to include JSON-LD schema
 * @param {boolean} [props.allowMultiple=false] - Allow multiple items open
 * @param {"chevron" | "plusminus"} [props.iconStyle="chevron"] - Icon style
 * @returns {JSX.Element} FAQ section
 */
export function FAQ({
  items,
  title,
  className = "",
  showSchema = true,
  allowMultiple = false,
  iconStyle = "chevron",
}) {
  const [openItems, setOpenItems] = useState(new Set());

  if (!items || items.length === 0) return null;

  // Normalize items to consistent format
  const normalizedItems = items.map((item) => ({
    question: item.question || item.q,
    answer: item.answer || item.a,
  }));

  const toggleItem = (index) => {
    setOpenItems((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        if (!allowMultiple) {
          next.clear();
        }
        next.add(index);
      }
      return next;
    });
  };

  const Icon = iconStyle === "plusminus" ? PlusMinusIcon : ChevronIcon;

  return (
    <section className={`faq-section ${className}`}>
      {/* JSON-LD Structured Data */}
      {showSchema && <JsonLd schema={generateFAQSchema(normalizedItems)} />}

      {/* Section Title */}
      {title && (
        <h2 className="text-2xl font-bold text-gray-900 mb-6">{title}</h2>
      )}

      {/* FAQ List */}
      <div
        className="space-y-3"
        itemScope
        itemType="https://schema.org/FAQPage"
      >
        {normalizedItems.map((item, index) => {
          const isOpen = openItems.has(index);

          return (
            <div
              key={index}
              className="border border-gray-200 rounded-lg overflow-hidden"
              itemScope
              itemProp="mainEntity"
              itemType="https://schema.org/Question"
            >
              {/* Question Button */}
              <button
                onClick={() => toggleItem(index)}
                className="w-full px-5 py-4 flex items-center justify-between text-left bg-white hover:bg-gray-50 transition-colors"
                aria-expanded={isOpen}
                aria-controls={`faq-answer-${index}`}
              >
                <span
                  className="font-medium text-gray-900 pr-4"
                  itemProp="name"
                >
                  {item.question}
                </span>
                <Icon isOpen={isOpen} />
              </button>

              {/* Answer Panel */}
              <div
                id={`faq-answer-${index}`}
                className={`overflow-hidden transition-all duration-200 ${
                  isOpen ? "max-h-96" : "max-h-0"
                }`}
                itemScope
                itemProp="acceptedAnswer"
                itemType="https://schema.org/Answer"
              >
                <div
                  className="px-5 pb-4 text-gray-500 prose prose-sm max-w-none"
                  itemProp="text"
                >
                  {item.answer}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

/**
 * Chevron icon for FAQ toggle.
 */
function ChevronIcon({ isOpen }) {
  return (
    <ChevronDown
      className={`w-5 h-5 text-gray-400 transition-transform duration-200 flex-shrink-0 ${
        isOpen ? "rotate-180" : ""
      }`}
      aria-hidden="true"
    />
  );
}

/**
 * Plus/Minus icon for FAQ toggle.
 */
function PlusMinusIcon({ isOpen }) {
  return isOpen ? (
    <Minus className="w-5 h-5 text-gray-400 flex-shrink-0" aria-hidden="true" />
  ) : (
    <Plus className="w-5 h-5 text-gray-400 flex-shrink-0" aria-hidden="true" />
  );
}

/**
 * Simple FAQ list without accordion (all answers visible).
 *
 * @param {Object} props - Component props
 * @param {Array} props.items - FAQ items
 * @param {string} [props.title] - Section title
 * @param {boolean} [props.showSchema=true] - Include JSON-LD schema
 * @returns {JSX.Element} FAQ list
 */
export function FAQList({ items, title, showSchema = true }) {
  if (!items || items.length === 0) return null;

  const normalizedItems = items.map((item) => ({
    question: item.question || item.q,
    answer: item.answer || item.a,
  }));

  return (
    <section className="faq-list">
      {showSchema && <JsonLd schema={generateFAQSchema(normalizedItems)} />}

      {title && (
        <h2 className="text-2xl font-bold text-gray-900 mb-6">{title}</h2>
      )}

      <dl className="space-y-6">
        {normalizedItems.map((item, index) => (
          <div key={index}>
            <dt className="font-semibold text-gray-900 mb-2">
              {item.question}
            </dt>
            <dd className="text-gray-500">{item.answer}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

export default FAQ;
