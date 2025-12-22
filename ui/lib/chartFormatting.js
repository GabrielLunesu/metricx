/**
 * Chart Formatting Utilities
 * ==========================
 *
 * WHAT: Unified formatting functions for charts and KPIs
 * WHY: Consolidates 4 duplicate implementations across the codebase
 *
 * Used by: UnifiedGraphEngine, KpiCardsModule, BreakdownTable, MetricSelector
 *
 * @module lib/chartFormatting
 */

// =============================================================================
// PLATFORM COLORS
// =============================================================================

/**
 * Consistent platform colors used across all charts
 * Based on official brand colors where available
 */
export const PLATFORM_COLORS = {
  google: '#4285F4',    // Google Blue
  meta: '#0668E1',      // Meta Blue
  tiktok: '#00F2EA',    // TikTok Cyan
  shopify: '#96BF48',   // Shopify Green
  direct: '#6B7280',    // Gray for direct traffic
  organic: '#10B981',   // Green for organic
  unknown: '#9CA3AF',   // Light gray for unknown
  blended: '#8B5CF6',   // Purple for blended/combined
};

/**
 * Extended color palette for multi-series charts
 */
export const CHART_COLORS = [
  '#4285F4', // Blue
  '#10B981', // Green
  '#F59E0B', // Amber
  '#EF4444', // Red
  '#8B5CF6', // Purple
  '#EC4899', // Pink
  '#14B8A6', // Teal
  '#F97316', // Orange
];

// =============================================================================
// METRIC CONFIGURATION
// =============================================================================

/**
 * Complete metric definitions with labels, formats, and colors
 * All 22 metrics exposed in the UI
 */
export const METRIC_CONFIG = {
  // Revenue & Profit metrics
  revenue: {
    label: 'Revenue',
    format: 'currency',
    color: '#10B981',
    group: 'Revenue & Profit',
    description: 'Total revenue attributed to ads'
  },
  profit: {
    label: 'Profit',
    format: 'currency',
    color: '#059669',
    group: 'Revenue & Profit',
    description: 'Revenue minus ad spend'
  },
  poas: {
    label: 'POAS',
    format: 'multiplier',
    color: '#7C3AED',
    group: 'Revenue & Profit',
    description: 'Profit on Ad Spend'
  },
  aov: {
    label: 'AOV',
    format: 'currency',
    color: '#A855F7',
    group: 'Revenue & Profit',
    description: 'Average Order Value'
  },
  arpv: {
    label: 'ARPV',
    format: 'currency',
    color: '#C084FC',
    group: 'Revenue & Profit',
    description: 'Average Revenue Per Visitor'
  },

  // Cost & Efficiency metrics
  spend: {
    label: 'Spend',
    format: 'currency',
    color: '#EF4444',
    group: 'Cost & Efficiency',
    description: 'Total ad spend'
  },
  cpc: {
    label: 'CPC',
    format: 'currency',
    color: '#EC4899',
    group: 'Cost & Efficiency',
    description: 'Cost Per Click'
  },
  cpm: {
    label: 'CPM',
    format: 'currency',
    color: '#F97316',
    group: 'Cost & Efficiency',
    description: 'Cost Per 1,000 Impressions'
  },
  cpl: {
    label: 'CPL',
    format: 'currency',
    color: '#F43F5E',
    group: 'Cost & Efficiency',
    description: 'Cost Per Lead'
  },
  cpi: {
    label: 'CPI',
    format: 'currency',
    color: '#FB923C',
    group: 'Cost & Efficiency',
    description: 'Cost Per Install'
  },
  cpp: {
    label: 'CPP',
    format: 'currency',
    color: '#E11D48',
    group: 'Cost & Efficiency',
    description: 'Cost Per Purchase'
  },
  cpa: {
    label: 'CPA',
    format: 'currency',
    color: '#FB7185',
    group: 'Cost & Efficiency',
    description: 'Cost Per Acquisition'
  },

  // Performance metrics
  roas: {
    label: 'ROAS',
    format: 'multiplier',
    color: '#8B5CF6',
    group: 'Performance',
    description: 'Return on Ad Spend'
  },
  conversions: {
    label: 'Conversions',
    format: 'number',
    color: '#F59E0B',
    group: 'Performance',
    description: 'Total conversions'
  },
  purchases: {
    label: 'Purchases',
    format: 'number',
    color: '#4ADE80',
    group: 'Performance',
    description: 'Total purchases'
  },
  leads: {
    label: 'Leads',
    format: 'number',
    color: '#0EA5E9',
    group: 'Performance',
    description: 'Total leads generated'
  },
  installs: {
    label: 'Installs',
    format: 'number',
    color: '#22D3EE',
    group: 'Performance',
    description: 'App installs'
  },

  // Engagement metrics
  impressions: {
    label: 'Impressions',
    format: 'compact',
    color: '#6366F1',
    group: 'Engagement',
    description: 'Total ad impressions'
  },
  clicks: {
    label: 'Clicks',
    format: 'compact',
    color: '#3B82F6',
    group: 'Engagement',
    description: 'Total ad clicks'
  },
  ctr: {
    label: 'CTR',
    format: 'percentage',
    color: '#14B8A6',
    group: 'Engagement',
    description: 'Click-Through Rate'
  },
  cvr: {
    label: 'CVR',
    format: 'percentage',
    color: '#84CC16',
    group: 'Engagement',
    description: 'Conversion Rate'
  },
  visitors: {
    label: 'Visitors',
    format: 'compact',
    color: '#A78BFA',
    group: 'Engagement',
    description: 'Unique visitors'
  },
};

/**
 * Metric groups for organized display
 */
export const METRIC_GROUPS = {
  'Revenue & Profit': ['revenue', 'profit', 'poas', 'aov', 'arpv'],
  'Cost & Efficiency': ['spend', 'cpc', 'cpm', 'cpl', 'cpi', 'cpp', 'cpa'],
  'Performance': ['roas', 'conversions', 'purchases', 'leads', 'installs'],
  'Engagement': ['impressions', 'clicks', 'ctr', 'cvr', 'visitors'],
};

// =============================================================================
// FORMATTING FUNCTIONS
// =============================================================================

/**
 * Formats a value as currency
 *
 * @param {number} value - The value to format
 * @param {string} currency - ISO currency code (default: USD)
 * @param {boolean} compact - Use compact notation for large numbers
 * @returns {string} Formatted currency string
 *
 * @example
 * formatCurrency(12500) // "$12,500"
 * formatCurrency(1500000, 'USD', true) // "$1.5M"
 */
export function formatCurrency(value, currency = 'USD', compact = false) {
  if (value === null || value === undefined || isNaN(value)) {
    return '-';
  }

  const options = {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: value < 10 ? 2 : 0,
  };

  if (compact && Math.abs(value) >= 10000) {
    options.notation = 'compact';
    options.maximumFractionDigits = 1;
  }

  return new Intl.NumberFormat('en-US', options).format(value);
}

/**
 * Formats a value as percentage
 *
 * @param {number} value - The value (0-100 scale or 0-1 scale)
 * @param {number} decimals - Decimal places (default: 1)
 * @param {boolean} isDecimal - If true, value is 0-1 scale
 * @returns {string} Formatted percentage string
 *
 * @example
 * formatPercentage(3.456) // "3.5%"
 * formatPercentage(0.0345, 2, true) // "3.45%"
 */
export function formatPercentage(value, decimals = 1, isDecimal = false) {
  if (value === null || value === undefined || isNaN(value)) {
    return '-';
  }

  const percentage = isDecimal ? value * 100 : value;
  return `${percentage.toFixed(decimals)}%`;
}

/**
 * Formats a value as a number with optional compact notation
 *
 * @param {number} value - The value to format
 * @param {boolean} compact - Use compact notation (K, M, B)
 * @returns {string} Formatted number string
 *
 * @example
 * formatNumber(12345) // "12,345"
 * formatNumber(1500000, true) // "1.5M"
 */
export function formatNumber(value, compact = false) {
  if (value === null || value === undefined || isNaN(value)) {
    return '-';
  }

  const options = {
    minimumFractionDigits: 0,
    maximumFractionDigits: value < 10 ? 2 : 0,
  };

  if (compact && Math.abs(value) >= 1000) {
    options.notation = 'compact';
    options.maximumFractionDigits = 1;
  }

  return new Intl.NumberFormat('en-US', options).format(value);
}

/**
 * Formats a multiplier value (e.g., ROAS)
 *
 * @param {number} value - The multiplier value
 * @param {number} decimals - Decimal places (default: 2)
 * @returns {string} Formatted multiplier string
 *
 * @example
 * formatMultiplier(3.456) // "3.46x"
 */
export function formatMultiplier(value, decimals = 2) {
  if (value === null || value === undefined || isNaN(value)) {
    return '-';
  }
  return `${value.toFixed(decimals)}x`;
}

/**
 * Formats a date for chart axis display
 *
 * @param {string|Date} date - The date to format
 * @param {string} granularity - "hour" | "day" | "week" | "month"
 * @returns {string} Formatted date string
 *
 * @example
 * formatDateForAxis('2024-12-15', 'day') // "Dec 15"
 * formatDateForAxis('2024-12-15T14:00:00', 'hour') // "2 PM"
 */
export function formatDateForAxis(date, granularity = 'day') {
  if (!date) return '-';

  const d = new Date(date);

  switch (granularity) {
    case 'hour':
      return d.toLocaleTimeString('en-US', { hour: 'numeric', hour12: true });
    case 'day':
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    case 'week':
      return `Week of ${d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`;
    case 'month':
      return d.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
    default:
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }
}

/**
 * Formats a timestamp for display (tooltip, table cells)
 *
 * @param {string|Date} timestamp - The timestamp to format
 * @param {boolean} includeTime - Include time in output
 * @returns {string} Formatted timestamp string
 *
 * @example
 * formatTimestamp('2024-12-15T14:30:00') // "Dec 15, 2024"
 * formatTimestamp('2024-12-15T14:30:00', true) // "Dec 15, 2024 2:30 PM"
 */
export function formatTimestamp(timestamp, includeTime = false) {
  if (!timestamp) return '-';

  const d = new Date(timestamp);
  const dateStr = d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  });

  if (includeTime) {
    const timeStr = d.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    });
    return `${dateStr} ${timeStr}`;
  }

  return dateStr;
}

/**
 * Gets the appropriate formatter for a metric
 *
 * @param {string} metricKey - The metric key (e.g., 'revenue', 'roas')
 * @returns {function} Formatter function for the metric
 *
 * @example
 * const formatter = getMetricFormatter('revenue');
 * formatter(12500) // "$12,500"
 */
export function getMetricFormatter(metricKey) {
  const config = METRIC_CONFIG[metricKey];
  if (!config) {
    return (value) => formatNumber(value);
  }

  switch (config.format) {
    case 'currency':
      return (value) => formatCurrency(value);
    case 'percentage':
      return (value) => formatPercentage(value);
    case 'multiplier':
      return (value) => formatMultiplier(value);
    case 'compact':
      return (value) => formatNumber(value, true);
    case 'number':
    default:
      return (value) => formatNumber(value);
  }
}

/**
 * Formats a metric value using its configured format
 *
 * @param {string} metricKey - The metric key
 * @param {number} value - The value to format
 * @returns {string} Formatted value string
 *
 * @example
 * formatMetricValue('revenue', 12500) // "$12,500"
 * formatMetricValue('roas', 3.45) // "3.45x"
 */
export function formatMetricValue(metricKey, value) {
  const formatter = getMetricFormatter(metricKey);
  return formatter(value);
}

/**
 * Formats a delta/change value with sign and percentage
 *
 * @param {number} value - The delta value
 * @param {boolean} isPercentage - If true, add % sign
 * @returns {object} { formatted, isPositive, color }
 *
 * @example
 * formatDelta(12.5) // { formatted: "+12.5%", isPositive: true, color: "text-green-600" }
 * formatDelta(-5.3) // { formatted: "-5.3%", isPositive: false, color: "text-red-600" }
 */
export function formatDelta(value, isPercentage = true) {
  if (value === null || value === undefined || isNaN(value)) {
    return { formatted: '-', isPositive: null, color: 'text-gray-500' };
  }

  const isPositive = value > 0;
  const sign = isPositive ? '+' : '';
  const suffix = isPercentage ? '%' : '';
  const formatted = `${sign}${value.toFixed(1)}${suffix}`;
  const color = isPositive ? 'text-green-600' : value < 0 ? 'text-red-600' : 'text-gray-500';

  return { formatted, isPositive, color };
}

// =============================================================================
// CAMPAIGN TYPE UTILITIES
// =============================================================================

/**
 * Campaign type definitions with drill-down capabilities
 */
export const CAMPAIGN_TYPES = {
  // Google campaign types
  SEARCH: {
    label: 'Search',
    platform: 'google',
    drillDownLevels: ['campaign', 'ad_group', 'ad'],
    description: 'Google Search campaigns'
  },
  DISPLAY: {
    label: 'Display',
    platform: 'google',
    drillDownLevels: ['campaign', 'ad_group', 'ad'],
    description: 'Google Display Network campaigns'
  },
  SHOPPING: {
    label: 'Shopping',
    platform: 'google',
    drillDownLevels: ['campaign', 'ad_group', 'product_group'],
    description: 'Google Shopping campaigns',
    limitations: ['Product-level data available in Products tab']
  },
  VIDEO: {
    label: 'Video',
    platform: 'google',
    drillDownLevels: ['campaign', 'ad_group', 'ad'],
    description: 'YouTube video campaigns'
  },
  PERFORMANCE_MAX: {
    label: 'Performance Max',
    platform: 'google',
    drillDownLevels: ['campaign'],
    description: 'Google Performance Max campaigns',
    limitations: [
      'Performance Max only reports at campaign level',
      'Asset group performance available separately'
    ]
  },
  APP: {
    label: 'App',
    platform: 'google',
    drillDownLevels: ['campaign', 'ad_group'],
    description: 'Google App campaigns'
  },
  DEMAND_GEN: {
    label: 'Demand Gen',
    platform: 'google',
    drillDownLevels: ['campaign', 'ad_group', 'ad'],
    description: 'Google Demand Gen campaigns'
  },

  // Meta campaign types
  META_STANDARD: {
    label: 'Standard',
    platform: 'meta',
    drillDownLevels: ['campaign', 'ad_set', 'ad'],
    description: 'Standard Meta campaigns'
  },
  ADVANTAGE_PLUS_SHOPPING: {
    label: 'Advantage+ Shopping',
    platform: 'meta',
    drillDownLevels: ['campaign'],
    description: 'Meta Advantage+ Shopping campaigns',
    limitations: [
      'Advantage+ Shopping only reports at campaign level',
      'Individual ad performance not available'
    ]
  },
  ADVANTAGE_PLUS_APP: {
    label: 'Advantage+ App',
    platform: 'meta',
    drillDownLevels: ['campaign'],
    description: 'Meta Advantage+ App campaigns',
    limitations: ['Reports at campaign level only']
  },
};

/**
 * Gets drill-down capabilities for a campaign type
 *
 * @param {string} campaignType - The campaign type
 * @returns {object} { levels, limitations, canDrillDown }
 */
export function getCampaignDrillDownInfo(campaignType) {
  const config = CAMPAIGN_TYPES[campaignType];
  if (!config) {
    return {
      levels: ['campaign', 'ad_group', 'ad'],
      limitations: [],
      canDrillDown: true
    };
  }

  return {
    levels: config.drillDownLevels,
    limitations: config.limitations || [],
    canDrillDown: config.drillDownLevels.length > 1
  };
}

/**
 * Returns a user-friendly message about drill-down limitations
 *
 * @param {string} campaignType - The campaign type
 * @returns {string|null} Limitation message or null if no limitations
 */
export function getDrillDownLimitationMessage(campaignType) {
  const info = getCampaignDrillDownInfo(campaignType);
  if (info.limitations.length === 0) return null;
  return info.limitations[0];
}

// =============================================================================
// CHART UTILITIES
// =============================================================================

/**
 * Determines optimal chart granularity based on date range
 *
 * @param {Date} startDate - Start of range
 * @param {Date} endDate - End of range
 * @returns {string} "hour" | "day"
 */
export function getChartGranularity(startDate, endDate) {
  const diffDays = Math.ceil((endDate - startDate) / (1000 * 60 * 60 * 24));

  if (diffDays <= 2) return 'hour';
  return 'day';
}

/**
 * Generates gradient ID for Recharts area fills
 *
 * @param {string} metricKey - The metric key
 * @returns {string} Gradient ID for use in fill prop
 */
export function getGradientId(metricKey) {
  return `gradient-${metricKey}`;
}

/**
 * Checks if a metric should use the right Y-axis (different scale)
 * ROAS and percentages should be on right axis when combined with currency
 *
 * @param {string} metricKey - The metric key
 * @param {string[]} selectedMetrics - All selected metrics
 * @returns {boolean} True if should use right Y-axis
 */
export function shouldUseRightAxis(metricKey, selectedMetrics) {
  const config = METRIC_CONFIG[metricKey];
  if (!config) return false;

  // If only one metric, always use left axis
  if (selectedMetrics.length === 1) return false;

  // Check if there are mixed format types
  const formats = selectedMetrics.map(m => METRIC_CONFIG[m]?.format);
  const hasCurrency = formats.includes('currency');
  const hasNonCurrency = formats.some(f => f !== 'currency');

  // Use right axis for non-currency metrics when mixed with currency
  if (hasCurrency && hasNonCurrency) {
    return config.format !== 'currency';
  }

  return false;
}

/**
 * Gets platform display name
 *
 * @param {string} platform - Platform key (google, meta, etc.)
 * @returns {string} Display name
 */
export function getPlatformDisplayName(platform) {
  const names = {
    google: 'Google Ads',
    meta: 'Meta Ads',
    tiktok: 'TikTok Ads',
    shopify: 'Shopify',
    blended: 'All Platforms',
  };
  return names[platform] || platform;
}
