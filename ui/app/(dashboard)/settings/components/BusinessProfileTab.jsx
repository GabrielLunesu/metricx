/**
 * Business Profile Tab - Edit business/workspace profile settings.
 *
 * WHAT: Allows users to edit business profile info collected during onboarding
 * WHY: Users may want to update their niche, markets, or brand voice over time
 *
 * REFERENCES:
 *   - ui/app/onboarding/components/StepBusinessProfile.jsx (similar fields)
 *   - backend/app/routers/onboarding.py (API endpoints)
 */

'use client';

import { useEffect, useState, useRef } from 'react';
import {
  Briefcase,
  Globe,
  Save,
  Loader2,
  AlertCircle,
  CheckCircle,
  X,
  Check,
  ChevronDown,
} from 'lucide-react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { toast } from 'sonner';
import { businessProfileSchema } from '@/lib/validation';

// Market options (same as onboarding)
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

// Brand voice options
const BRAND_VOICE_OPTIONS = [
  { value: 'Professional', desc: 'Formal and business-like' },
  { value: 'Casual', desc: 'Friendly and approachable' },
  { value: 'Luxury', desc: 'Premium and sophisticated' },
  { value: 'Playful', desc: 'Fun and energetic' },
  { value: 'Technical', desc: 'Data-driven and precise' },
];

export default function BusinessProfileTab({ user }) {
  const [message, setMessage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState(null);

  // Niche autocomplete state
  const [nicheQuery, setNicheQuery] = useState('');
  const [showNicheSuggestions, setShowNicheSuggestions] = useState(false);
  const nicheRef = useRef(null);

  // Markets dropdown state
  const [showMarkets, setShowMarkets] = useState(false);
  const [marketQuery, setMarketQuery] = useState('');
  const marketsRef = useRef(null);

  // Selected markets (controlled separately for UI)
  const [selectedMarkets, setSelectedMarkets] = useState([]);

  const form = useForm({
    resolver: zodResolver(businessProfileSchema),
    defaultValues: {
      domain: '',
      domain_description: '',
      niche: '',
      target_markets: [],
      brand_voice: '',
    },
  });

  // Fetch current profile on mount
  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const res = await fetch('/api/onboarding/profile', {
          credentials: 'include',
        });
        if (res.ok) {
          const data = await res.json();
          setProfile(data);
          setNicheQuery(data.niche || '');
          setSelectedMarkets(data.target_markets || []);
          form.reset({
            domain: data.domain || '',
            domain_description: data.domain_description || '',
            niche: data.niche || '',
            target_markets: data.target_markets || [],
            brand_voice: data.brand_voice || '',
          });
        }
      } catch (err) {
        console.error('Failed to fetch business profile:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchProfile();
  }, [form]);

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

  // Handle niche selection
  const selectNiche = (niche) => {
    setNicheQuery(niche);
    form.setValue('niche', niche);
    setShowNicheSuggestions(false);
  };

  // Handle market toggle
  const toggleMarket = (market) => {
    const current = [...selectedMarkets];
    if (current.includes(market)) {
      const updated = current.filter((m) => m !== market);
      setSelectedMarkets(updated);
      form.setValue('target_markets', updated);
    } else {
      const updated = [...current, market];
      setSelectedMarkets(updated);
      form.setValue('target_markets', updated);
    }
  };

  // Remove market chip
  const removeMarket = (market) => {
    const updated = selectedMarkets.filter((m) => m !== market);
    setSelectedMarkets(updated);
    form.setValue('target_markets', updated);
  };

  const handleSubmit = form.handleSubmit(async (values) => {
    setMessage(null);
    try {
      const res = await fetch('/api/onboarding/profile', {
        method: 'PUT',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to update profile');
      }

      const data = await res.json();
      setProfile(data);
      setMessage({ type: 'success', text: 'Business profile updated' });
      toast.success('Business profile saved');
    } catch (err) {
      const msg = err?.message || 'Failed to update profile';
      setMessage({ type: 'error', text: msg });
      toast.error(msg);
    }
  });

  const errors = form.formState.errors;

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-neutral-400" />
      </div>
    );
  }

  return (
    <div>
      {message && (
        <div
          className={`p-4 mb-6 rounded-xl flex items-center gap-3 ${
            message.type === 'success'
              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
              : 'bg-red-50 text-red-700 border border-red-200'
          }`}
        >
          {message.type === 'success' ? (
            <CheckCircle className="w-5 h-5" />
          ) : (
            <AlertCircle className="w-5 h-5" />
          )}
          {message.text}
        </div>
      )}

      <div className="bg-white p-6 rounded-xl border border-neutral-200 shadow-sm">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-lg bg-indigo-100 flex items-center justify-center">
            <Briefcase className="w-5 h-5 text-indigo-600" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-neutral-900">Business Profile</h2>
            <p className="text-sm text-neutral-500">
              This information helps personalize your Copilot experience
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5" noValidate>
          {/* Domain */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1">
              Website Domain
            </label>
            <div className="relative">
              <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
              <input
                type="text"
                {...form.register('domain')}
                placeholder="yourbusiness.com"
                className="w-full pl-10 pr-4 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all"
              />
            </div>
            {errors.domain && (
              <p className="text-xs text-red-600 mt-1">{errors.domain.message}</p>
            )}
          </div>

          {/* Domain Description */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1">
              About Your Business
            </label>
            <textarea
              {...form.register('domain_description')}
              rows={3}
              placeholder="Brief description of what your business does..."
              className="w-full px-4 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all resize-none"
            />
            {errors.domain_description && (
              <p className="text-xs text-red-600 mt-1">{errors.domain_description.message}</p>
            )}
          </div>

          {/* Niche with autocomplete */}
          <div ref={nicheRef}>
            <label className="block text-sm font-medium text-neutral-700 mb-1">
              Industry / Niche
            </label>
            <div className="relative">
              <input
                type="text"
                value={nicheQuery}
                onChange={(e) => {
                  setNicheQuery(e.target.value);
                  form.setValue('niche', e.target.value);
                  setShowNicheSuggestions(true);
                }}
                onFocus={() => setShowNicheSuggestions(true)}
                placeholder="e.g., Fashion, SaaS, E-commerce"
                className="w-full px-4 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all"
              />

              {/* Suggestions dropdown */}
              {showNicheSuggestions && filteredNiches.length > 0 && (
                <div className="absolute z-20 mt-1 w-full bg-white rounded-lg border border-neutral-200 shadow-lg max-h-48 overflow-y-auto">
                  {filteredNiches.map((niche) => (
                    <button
                      key={niche}
                      type="button"
                      onClick={() => selectNiche(niche)}
                      className="w-full px-4 py-2 text-left text-sm hover:bg-neutral-50 first:rounded-t-lg last:rounded-b-lg"
                    >
                      {niche}
                    </button>
                  ))}
                </div>
              )}
            </div>
            {errors.niche && (
              <p className="text-xs text-red-600 mt-1">{errors.niche.message}</p>
            )}
          </div>

          {/* Target Markets multi-select */}
          <div ref={marketsRef}>
            <label className="block text-sm font-medium text-neutral-700 mb-1">
              Target Markets
            </label>

            {/* Selected markets as chips */}
            {selectedMarkets.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-2">
                {selectedMarkets.map((market) => (
                  <span
                    key={market}
                    className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm bg-indigo-100 text-indigo-700"
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
                className="w-full px-4 py-2 rounded-lg border border-neutral-300 text-left flex items-center justify-between hover:border-neutral-400 transition-colors"
              >
                <span className="text-neutral-500 text-sm">
                  {selectedMarkets.length === 0
                    ? 'Select markets...'
                    : `${selectedMarkets.length} selected`}
                </span>
                <ChevronDown className="w-4 h-4 text-neutral-400" />
              </button>

              {/* Markets dropdown */}
              {showMarkets && (
                <div className="absolute z-20 mt-1 w-full bg-white rounded-lg border border-neutral-200 shadow-lg max-h-64 overflow-y-auto">
                  {/* Search */}
                  <div className="p-2 border-b border-neutral-100">
                    <input
                      type="text"
                      value={marketQuery}
                      onChange={(e) => setMarketQuery(e.target.value)}
                      placeholder="Search..."
                      className="w-full px-3 py-1.5 text-sm rounded-md border border-neutral-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                    />
                  </div>

                  {/* Options */}
                  <div className="py-1">
                    {filteredMarkets.map((market) => {
                      const isSelected = selectedMarkets.includes(market);
                      const isSpecial = MARKET_OPTIONS.special.includes(market);
                      const isContinent = MARKET_OPTIONS.continents.includes(market);

                      return (
                        <button
                          key={market}
                          type="button"
                          onClick={() => toggleMarket(market)}
                          className={`
                            w-full px-4 py-2 text-left text-sm flex items-center gap-2
                            hover:bg-neutral-50
                            ${isSpecial ? 'font-medium text-indigo-600' : ''}
                            ${isContinent ? 'font-medium' : ''}
                          `}
                        >
                          <div
                            className={`
                              w-4 h-4 rounded border flex items-center justify-center
                              ${isSelected ? 'bg-indigo-600 border-indigo-600' : 'border-neutral-300'}
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
            {errors.target_markets && (
              <p className="text-xs text-red-600 mt-1">{errors.target_markets.message}</p>
            )}
          </div>

          {/* Brand Voice */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1">
              Brand Voice
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {BRAND_VOICE_OPTIONS.map((opt) => {
                const isSelected = form.watch('brand_voice') === opt.value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => form.setValue('brand_voice', opt.value)}
                    className={`
                      px-3 py-2 rounded-lg border text-sm text-left transition-all
                      ${
                        isSelected
                          ? 'border-indigo-600 bg-indigo-50 text-indigo-700'
                          : 'border-neutral-200 hover:border-neutral-300'
                      }
                    `}
                  >
                    <div className="font-medium">{opt.value}</div>
                    <div className="text-xs text-neutral-500 mt-0.5">{opt.desc}</div>
                  </button>
                );
              })}
            </div>
            {errors.brand_voice && (
              <p className="text-xs text-red-600 mt-1">{errors.brand_voice.message}</p>
            )}
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={form.formState.isSubmitting}
            className="w-full flex items-center justify-center gap-2 bg-indigo-600 text-white py-2.5 px-4 rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50"
          >
            {form.formState.isSubmitting ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            Save Changes
          </button>
        </form>
      </div>
    </div>
  );
}
