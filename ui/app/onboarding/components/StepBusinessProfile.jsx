/**
 * Step 3: Business Profile
 * ========================
 *
 * WHAT: Collects niche, target markets, and brand voice.
 * WHY: Provides context for AI personalization in Copilot.
 *
 * FIELDS:
 *   - Niche: Open text with autocomplete suggestions
 *   - Target Markets: Multi-select with countries, continents, Worldwide
 *   - Brand Voice: Single select
 */

'use client';

import { useState, useRef, useEffect } from 'react';
import { Briefcase, ArrowRight, ArrowLeft, X, Check, ChevronDown } from 'lucide-react';

// Niche suggestions for autocomplete
const NICHE_SUGGESTIONS = [
  'Fashion & Apparel',
  'Beauty & Cosmetics',
  'Health & Wellness',
  'Electronics & Tech',
  'Home & Garden',
  'Food & Beverage',
  'Sports & Outdoors',
  'Toys & Games',
  'Pet Supplies',
  'Jewelry & Accessories',
  'Automotive',
  'SaaS',
  'B2B Services',
  'Financial Services',
  'Education',
  'Travel & Hospitality',
  'Real Estate',
  'Entertainment & Media',
];

// Market options grouped by type
const MARKET_OPTIONS = {
  special: ['Worldwide'],
  continents: ['North America', 'Europe', 'Asia', 'South America', 'Africa', 'Oceania'],
  countries: [
    'United States',
    'United Kingdom',
    'Germany',
    'France',
    'Netherlands',
    'Canada',
    'Australia',
    'Spain',
    'Italy',
    'Japan',
    'South Korea',
    'Brazil',
    'Mexico',
    'India',
    'Singapore',
    'UAE',
  ],
};

// Brand voice options
const BRAND_VOICE_OPTIONS = [
  { value: 'Professional', desc: 'Formal and business-like' },
  { value: 'Casual', desc: 'Friendly and approachable' },
  { value: 'Luxury', desc: 'Premium and sophisticated' },
  { value: 'Playful', desc: 'Fun and energetic' },
  { value: 'Technical', desc: 'Data-driven and precise' },
];

export default function StepBusinessProfile({
  formData,
  updateFormData,
  aiSuggestions,
  onNext,
  onBack,
  onSkip,
}) {
  // Niche autocomplete state
  const [nicheQuery, setNicheQuery] = useState(formData.niche || '');
  const [showNicheSuggestions, setShowNicheSuggestions] = useState(false);
  const nicheRef = useRef(null);

  // Markets dropdown state
  const [showMarkets, setShowMarkets] = useState(false);
  const [marketQuery, setMarketQuery] = useState('');
  const marketsRef = useRef(null);

  // Filter niche suggestions
  const filteredNiches = NICHE_SUGGESTIONS.filter((n) =>
    n.toLowerCase().includes(nicheQuery.toLowerCase())
  );

  // Flatten and filter market options
  const allMarkets = [
    ...MARKET_OPTIONS.special,
    ...MARKET_OPTIONS.continents,
    ...MARKET_OPTIONS.countries,
  ];
  const filteredMarkets = allMarkets.filter((m) =>
    m.toLowerCase().includes(marketQuery.toLowerCase())
  );

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (nicheRef.current && !nicheRef.current.contains(e.target)) {
        setShowNicheSuggestions(false);
      }
      if (marketsRef.current && !marketsRef.current.contains(e.target)) {
        setShowMarkets(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Handle niche selection
  const selectNiche = (niche) => {
    setNicheQuery(niche);
    updateFormData({ niche });
    setShowNicheSuggestions(false);
  };

  // Handle market toggle
  const toggleMarket = (market) => {
    const current = formData.target_markets || [];
    if (current.includes(market)) {
      updateFormData({ target_markets: current.filter((m) => m !== market) });
    } else {
      updateFormData({ target_markets: [...current, market] });
    }
  };

  // Remove market chip
  const removeMarket = (market) => {
    const current = formData.target_markets || [];
    updateFormData({ target_markets: current.filter((m) => m !== market) });
  };

  return (
    <div>
      {/* Header */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-indigo-100 mb-4">
          <Briefcase className="w-6 h-6 text-indigo-600" />
        </div>
        <h1 className="text-2xl font-semibold text-slate-900">
          Tell us about your business
        </h1>
        <p className="mt-2 text-slate-500">
          This helps us personalize your experience
        </p>
      </div>

      {/* Niche field */}
      <div className="mb-5" ref={nicheRef}>
        <label className="block text-sm font-medium text-slate-700 mb-1.5">
          Industry / Niche
        </label>
        <div className="relative">
          <input
            type="text"
            value={nicheQuery}
            onChange={(e) => {
              setNicheQuery(e.target.value);
              updateFormData({ niche: e.target.value });
              setShowNicheSuggestions(true);
            }}
            onFocus={() => setShowNicheSuggestions(true)}
            placeholder="e.g., Fashion, SaaS, E-commerce"
            className="w-full px-4 py-2.5 rounded-xl border border-slate-200
              focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          />

          {/* Suggestions dropdown */}
          {showNicheSuggestions && filteredNiches.length > 0 && (
            <div className="absolute z-10 mt-1 w-full bg-white rounded-xl border border-slate-200 shadow-lg max-h-48 overflow-y-auto">
              {filteredNiches.map((niche) => (
                <button
                  key={niche}
                  type="button"
                  onClick={() => selectNiche(niche)}
                  className="w-full px-4 py-2 text-left text-sm hover:bg-slate-50 first:rounded-t-xl last:rounded-b-xl"
                >
                  {niche}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Target Markets field */}
      <div className="mb-5" ref={marketsRef}>
        <label className="block text-sm font-medium text-slate-700 mb-1.5">
          Target Markets
        </label>

        {/* Selected markets as chips */}
        {(formData.target_markets || []).length > 0 && (
          <div className="flex flex-wrap gap-2 mb-2">
            {(formData.target_markets || []).map((market) => (
              <span
                key={market}
                className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm
                  bg-indigo-100 text-indigo-700"
              >
                {market}
                <button
                  type="button"
                  onClick={() => removeMarket(market)}
                  className="hover:text-indigo-900"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
          </div>
        )}

        {/* Markets dropdown trigger */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setShowMarkets(!showMarkets)}
            className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-left
              flex items-center justify-between hover:border-slate-300 transition-colors"
          >
            <span className="text-slate-500 text-sm">
              {(formData.target_markets || []).length === 0
                ? 'Select markets...'
                : `${(formData.target_markets || []).length} selected`}
            </span>
            <ChevronDown className="w-4 h-4 text-slate-400" />
          </button>

          {/* Markets dropdown */}
          {showMarkets && (
            <div className="absolute z-10 mt-1 w-full bg-white rounded-xl border border-slate-200 shadow-lg max-h-64 overflow-y-auto">
              {/* Search */}
              <div className="p-2 border-b border-slate-100">
                <input
                  type="text"
                  value={marketQuery}
                  onChange={(e) => setMarketQuery(e.target.value)}
                  placeholder="Search..."
                  className="w-full px-3 py-1.5 text-sm rounded-lg border border-slate-200
                    focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              {/* Options */}
              <div className="py-1">
                {filteredMarkets.map((market) => {
                  const isSelected = (formData.target_markets || []).includes(market);
                  const isSpecial = MARKET_OPTIONS.special.includes(market);
                  const isContinent = MARKET_OPTIONS.continents.includes(market);

                  return (
                    <button
                      key={market}
                      type="button"
                      onClick={() => toggleMarket(market)}
                      className={`
                        w-full px-4 py-2 text-left text-sm flex items-center gap-2
                        hover:bg-slate-50
                        ${isSpecial ? 'font-medium text-indigo-600' : ''}
                        ${isContinent ? 'font-medium' : ''}
                      `}
                    >
                      <div
                        className={`
                          w-4 h-4 rounded border flex items-center justify-center
                          ${isSelected
                            ? 'bg-indigo-600 border-indigo-600'
                            : 'border-slate-300'}
                        `}
                      >
                        {isSelected && <Check className="w-3 h-3 text-white" />}
                      </div>
                      {market}
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Brand Voice field */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-slate-700 mb-1.5">
          Brand Voice
        </label>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {BRAND_VOICE_OPTIONS.map((opt) => {
            const isSelected = formData.brand_voice === opt.value;
            return (
              <button
                key={opt.value}
                type="button"
                onClick={() => updateFormData({ brand_voice: opt.value })}
                className={`
                  px-3 py-2 rounded-xl border text-sm text-left transition-all
                  ${isSelected
                    ? 'border-indigo-600 bg-indigo-50 text-indigo-700'
                    : 'border-slate-200 hover:border-slate-300'}
                `}
              >
                <div className="font-medium">{opt.value}</div>
                <div className="text-xs text-slate-500 mt-0.5">{opt.desc}</div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        <button
          type="button"
          onClick={onBack}
          className="px-4 py-3 rounded-xl border border-slate-200 text-slate-600 font-medium
            hover:bg-slate-50 transition-colors flex items-center gap-2"
        >
          <ArrowLeft className="w-4 h-4" />
          Back
        </button>

        <button
          type="button"
          onClick={onSkip}
          className="flex-1 px-4 py-3 rounded-xl border border-slate-200 text-slate-600 font-medium
            hover:bg-slate-50 transition-colors"
        >
          Skip
        </button>

        <button
          type="button"
          onClick={onNext}
          className="flex-1 px-4 py-3 rounded-xl bg-indigo-600 text-white font-medium
            hover:bg-indigo-700 transition-colors flex items-center justify-center gap-2"
        >
          Continue
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
