import { clsx } from "clsx";
import { twMerge } from "tailwind-merge"

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

/**
 * Currency symbols mapping.
 */
const CURRENCY_SYMBOLS = {
  USD: "$",
  EUR: "€",
  GBP: "£",
  CAD: "C$",
  AUD: "A$",
};

/**
 * Format a currency value for display.
 *
 * WHAT: Formats numbers as currency with appropriate suffixes (K, M)
 * WHY: Consistent currency display across the app
 *
 * @param {number|null|undefined} value - The value to format
 * @param {Object} options - Formatting options
 * @param {number} options.decimals - Decimal places for small values (default: 0)
 * @param {boolean} options.compact - Use K/M suffixes (default: true)
 * @param {string} options.currency - Currency code (default: "USD")
 * @returns {string} Formatted currency string
 */
export function formatCurrency(value, { decimals, compact = true, currency = "USD" } = {}) {
  if (value === null || value === undefined) return "—";

  const symbol = CURRENCY_SYMBOLS[currency] || currency;
  const absValue = Math.abs(value);

  if (compact) {
    if (absValue >= 1000000) return `${symbol}${(value / 1000000).toFixed(2)}M`;
    if (absValue >= 1000) return `${symbol}${(value / 1000).toFixed(1)}K`;
  }

  // Auto-determine decimals: 2 for small values (under $10), 0 otherwise
  const effectiveDecimals = decimals !== undefined ? decimals : (absValue < 10 ? 2 : 0);

  return `${symbol}${value.toLocaleString(undefined, {
    minimumFractionDigits: effectiveDecimals,
    maximumFractionDigits: effectiveDecimals
  })}`;
}

/**
 * Format a metric value based on its type.
 *
 * WHAT: Formats values appropriately based on metric type
 * WHY: Different metrics need different formatting (currency, percentage, multiplier)
 *
 * @param {number|null|undefined} value - The value to format
 * @param {string} format - The format type: 'currency', 'percentage', 'multiplier'
 * @param {Object} options - Additional formatting options
 * @param {string} options.currency - Currency code for currency formatting
 * @returns {string} Formatted value string
 */
export function formatMetricValue(value, format, { decimals = 0, currency = "USD" } = {}) {
  if (value === null || value === undefined) return "—";

  switch (format) {
    case 'currency':
      return formatCurrency(value, { decimals, currency });
    case 'percentage':
    case 'percent':
      return `${value.toFixed(2)}%`;
    case 'multiplier':
      return `${value.toFixed(2)}x`;
    case 'number':
      return value.toLocaleString(undefined, {
        minimumFractionDigits: 0,
        maximumFractionDigits: decimals
      });
    default:
      return value.toLocaleString();
  }
}

/**
 * Format a delta/change value as a percentage.
 *
 * WHAT: Formats period-over-period change values
 * WHY: Consistent display of change indicators with proper +/- signs
 *
 * @param {number|null|undefined} delta - The delta value (as decimal, e.g., 0.15 for 15%)
 * @param {boolean} inverse - If true, negative is good (e.g., for costs)
 * @returns {Object|null} Object with text, isGood, and color properties
 */
export function formatDelta(delta, inverse = false) {
  if (delta === null || delta === undefined) return null;

  const pct = (delta * 100).toFixed(0);
  const isPositive = delta > 0;
  const isGood = inverse ? !isPositive : isPositive;

  return {
    text: `${isPositive ? '+' : ''}${pct}%`,
    isGood,
    color: isGood ? 'text-emerald-600' : delta === 0 ? 'text-slate-400' : 'text-red-500'
  };
}
