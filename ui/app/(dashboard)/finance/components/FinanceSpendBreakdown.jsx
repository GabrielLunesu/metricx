"use client";

/**
 * FinanceSpendBreakdown - Platform spend breakdown with progress bars
 * 
 * WHAT: Shows spend distribution across platforms (Meta, Google)
 * WHY: Visual representation of where ad budget is allocated
 * 
 * REFERENCES:
 *   - Metricx v3.0 design system
 */

/**
 * Currency symbols
 */
const CURRENCY_SYMBOLS = {
  USD: "$",
  EUR: "€",
  GBP: "£",
  CAD: "C$",
  AUD: "A$",
};

/**
 * Format currency value
 */
function formatCurrency(value, currency = "EUR") {
  if (value === null || value === undefined) return "—";
  const symbol = CURRENCY_SYMBOLS[currency] || "€";
  
  if (Math.abs(value) >= 1000000) {
    return `${symbol}${(value / 1000000).toFixed(2)}M`;
  }
  if (Math.abs(value) >= 1000) {
    return `${symbol}${(value / 1000).toFixed(1)}k`;
  }
  return `${symbol}${new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value)}`;
}

/**
 * Platform Icon Component
 */
function PlatformIcon({ platform }) {
  const normalized = (platform || "").toLowerCase();

  if (normalized.includes("meta") || normalized.includes("facebook")) {
    return (
      <svg className="w-4 h-4 text-neutral-900" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2C6.477 2 2 6.477 2 12c0 4.991 3.657 9.128 8.438 9.879V14.89h-2.54V12h2.54V9.797c0-2.506 1.492-3.89 3.777-3.89 1.094 0 2.238.195 2.238.195v2.46h-1.26c-1.243 0-1.63.771-1.63 1.562V12h2.773l-.443 2.89h-2.33v6.989C18.343 21.129 22 16.99 22 12c0-5.523-4.477-10-10-10z"/>
      </svg>
    );
  }

  if (normalized.includes("google")) {
    return (
      <svg className="w-4 h-4 text-neutral-900" viewBox="0 0 24 24" fill="currentColor">
        <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
        <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
        <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
        <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
      </svg>
    );
  }

  return (
    <div className="w-4 h-4 rounded bg-neutral-200 flex items-center justify-center">
      <span className="text-[10px] text-neutral-500">?</span>
    </div>
  );
}

/**
 * Single Platform Spend Row
 */
function SpendRow({ platform, spend, percentage, currency }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <PlatformIcon platform={platform} />
          <span className="text-sm font-medium text-neutral-900">{platform}</span>
        </div>
        <div className="text-right">
          <div className="text-sm font-semibold text-neutral-900 tabular-nums">
            {formatCurrency(spend, currency)}
          </div>
          <div className="text-[10px] text-neutral-500 font-medium uppercase tracking-wider">
            {percentage.toFixed(0)}% of spend
          </div>
        </div>
      </div>
      <div className="w-full bg-neutral-100 rounded-full h-1.5 overflow-hidden">
        <div
          className="bg-neutral-900 h-1.5 rounded-full transition-all duration-500"
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>
    </div>
  );
}

export default function FinanceSpendBreakdown({
  composition = [],
  totalRevenue = 0,
  totalSpend = 0,
  loading = false,
  currency = "EUR",
}) {
  // Filter to only ad spend rows
  const adSpendRows = composition.filter(
    (item) => item.label?.toLowerCase().includes("ad spend")
  );

  // Calculate blended margin
  const blendedMargin = totalRevenue > 0
    ? ((totalRevenue - totalSpend) / totalRevenue) * 100
    : 0;

  if (loading) {
    return (
      <div className="p-6 border border-neutral-200 bg-white rounded-xl h-full">
        <div className="h-5 w-32 bg-neutral-100 rounded animate-pulse mb-6" />
        <div className="space-y-8">
          {[1, 2].map((i) => (
            <div key={i} className="space-y-3">
              <div className="flex justify-between">
                <div className="h-4 w-24 bg-neutral-100 rounded animate-pulse" />
                <div className="h-4 w-20 bg-neutral-100 rounded animate-pulse" />
              </div>
              <div className="h-1.5 bg-neutral-100 rounded-full animate-pulse" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 border border-neutral-200 bg-white rounded-xl shadow-[0_1px_2px_rgba(0,0,0,0.02)] h-full">
      <h3 className="text-base font-semibold text-neutral-900 tracking-tight mb-6">
        Spend Breakdown
      </h3>

      <div className="flex flex-col gap-8">
        {/* Platform rows */}
        {adSpendRows.length > 0 ? (
          adSpendRows.map((item) => {
            const percentage = totalSpend > 0 ? (item.value / totalSpend) * 100 : 0;
            // Extract platform name from "Ad Spend - Meta" format
            const platformName = item.label.replace("Ad Spend - ", "").replace("Ads", "").trim() + " Ads";
            
            return (
              <SpendRow
                key={item.label}
                platform={platformName}
                spend={item.value}
                percentage={percentage}
                currency={currency}
              />
            );
          })
        ) : (
          <div className="text-center py-8 text-neutral-400 text-sm">
            No ad spend data available
          </div>
        )}

        {/* Blended Margin */}
        <div className="mt-auto pt-6 border-t border-neutral-100">
          <div className="flex justify-between items-center">
            <span className="text-xs text-neutral-500 font-medium">Blended Margin</span>
            <span className="text-2xl font-semibold text-neutral-900 tracking-tight">
              {blendedMargin.toFixed(1)}%
            </span>
          </div>
          <p className="text-xs text-neutral-400 mt-1">
            Calculated after all expenses and ad spend.
          </p>
        </div>
      </div>
    </div>
  );
}
