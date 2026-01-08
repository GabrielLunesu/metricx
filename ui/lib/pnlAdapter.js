/**
 * P&L View Model Adapter
 * 
 * WHAT: Maps API responses to UI-friendly view models
 * WHY: Isolates UI from API contracts, handles formatting and safe defaults
 * REFERENCES:
 *   - lib/financeApiClient.js: Source data
 *   - app/(dashboard)/finance/components/*.jsx: Consumers
 * 
 * Design principles:
 *   - All currency formatting happens here (not in components)
 *   - Safe defaults for null/undefined (no crashes)
 *   - No business logic (no calculations)
 *   - Field names match UI needs (not API names)
 */

/**
 * Format currency for display.
 * @param {number} value
 * @returns {string} e.g., "$1,234.56"
 */
function formatCurrency(value) {
  if (value === null || value === undefined) return '$0.00';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD'
  }).format(value);
}

/**
 * Format percentage for display.
 * @param {number} value - Decimal (0.15 = 15%)
 * @returns {string} e.g., "+15.0%" or "-5.2%"
 */
function formatPercentage(value) {
  if (value === null || value === undefined) return 'N/A';
  const sign = value >= 0 ? '+' : '';
  return `${sign}${(value * 100).toFixed(1)}%`;
}

/**
 * Format ratio for display.
 * @param {number} value
 * @returns {string} e.g., "2.45×"
 */
function formatRatio(value) {
  if (value === null || value === undefined) return 'N/A';
  return `${value.toFixed(2)}×`;
}

/**
 * Map P&L statement response to view model.
 * 
 * WHAT: Converts API response to UI-ready format
 * WHY: Components only display, never compute or format
 * 
 * @param {PnLStatementResponse} apiResponse
 * @returns {Object} View model for Finance page
 */
export function adaptPnLStatement(apiResponse) {
  const { summary, rows, composition, timeseries } = apiResponse;
  
  return {
    // Summary cards (top of page)
    summary: {
      totalRevenue: {
        label: 'Total Revenue',
        value: formatCurrency(summary.total_revenue),
        rawValue: summary.total_revenue,
        delta: summary.compare?.revenue_delta_pct 
          ? formatPercentage(summary.compare.revenue_delta_pct) 
          : null
      },
      totalSpend: {
        label: 'Total Spend',
        value: formatCurrency(summary.total_spend),
        rawValue: summary.total_spend,
        delta: summary.compare?.spend_delta_pct 
          ? formatPercentage(summary.compare.spend_delta_pct) 
          : null
      },
      grossProfit: {
        label: 'Gross Profit',
        value: formatCurrency(summary.gross_profit),
        rawValue: summary.gross_profit,
        delta: summary.compare?.profit_delta_pct 
          ? formatPercentage(summary.compare.profit_delta_pct) 
          : null
      },
      netRoas: {
        label: 'Net ROAS',
        value: formatRatio(summary.net_roas),
        rawValue: summary.net_roas,
        delta: summary.compare?.roas_delta 
          ? formatRatio(summary.compare.roas_delta) 
          : null
      }
    },
    
    // P&L table rows
    rows: rows.map(row => ({
      id: row.id,
      category: row.category,
      actual: formatCurrency(row.actual_dollar),
      actualRaw: row.actual_dollar,
      planned: row.planned_dollar ? formatCurrency(row.planned_dollar) : '—',
      plannedRaw: row.planned_dollar,
      variance: row.variance_pct ? formatPercentage(row.variance_pct) : '—',
      varianceRaw: row.variance_pct,
      notes: row.notes || '',
      source: row.source,
      isAdSpend: row.source === 'ads',
      isManual: row.source === 'manual',
      // For manual costs: list of individual cost UUIDs that make up this aggregated row
      costIds: row.cost_ids || []
    })),
    
    // Composition pie chart
    composition: composition.map(slice => ({
      label: slice.label,
      value: slice.value,
      formatted: formatCurrency(slice.value)
    })),
    
    // Future: Daily timeseries (not used yet)
    timeseries: timeseries || null,
    
    // Comparison mode flag
    hasComparison: !!summary.compare
  };
}

/**
 * Map manual cost list to view model.
 * 
 * @param {ManualCostOut[]} costs
 * @returns {Object[]}
 */
export function adaptManualCosts(costs) {
  return costs.map(cost => ({
    id: cost.id,
    label: cost.label,
    category: cost.category,
    amount: formatCurrency(cost.amount_dollar),
    amountRaw: cost.amount_dollar,
    allocationType: cost.allocation.type,
    allocationDate: cost.allocation.date || null,
    allocationRange: cost.allocation.start_date && cost.allocation.end_date
      ? `${cost.allocation.start_date} to ${cost.allocation.end_date}`
      : null,
    notes: cost.notes || '',
    createdAt: new Date(cost.created_at).toLocaleDateString()
  }));
}

/**
 * Generate period dates for a given month.
 * 
 * WHAT: Helper to compute period_start and period_end from month selection
 * WHY: Finance page selects by month, API needs date range
 * 
 * @param {number} year
 * @param {number} month - 1-indexed (1 = January)
 * @returns {{periodStart: string, periodEnd: string}} ISO dates
 */
export function getPeriodDatesForMonth(year, month) {
  const periodStart = new Date(year, month - 1, 1).toISOString().split('T')[0];
  const periodEnd = new Date(year, month, 1).toISOString().split('T')[0]; // First day of next month (exclusive)
  
  return { periodStart, periodEnd };
}


