/**
 * Finance & P&L Page v3.0 - Redesigned Financial Dashboard
 * =========================================================
 *
 * WHAT: Clean, minimalistic finance page with new design system
 * WHY: Improved UX matching Metricx v3.0 design language
 *
 * LAYOUT:
 *   - Header: Title, subtitle, date range picker (This Month / Last Month / 90 Days / Custom)
 *   - 4 KPI cards: Revenue, Spend, Gross Profit, Net ROAS
 *   - Middle section: P&L Table + Spend Breakdown
 *   - Bottom section: Revenue Chart + AI Copilot
 *
 * DATA FLOW:
 *   - Date range selection → fetch P&L from /workspaces/{id}/finance/pnl
 *   - Manual costs CRUD → refetch P&L on changes
 */
"use client";

import { useState, useEffect, useMemo } from "react";
import { toast } from "sonner";
import { format, startOfMonth, endOfDay } from "date-fns";
import { currentUser } from "@/lib/workspace";
import { getPnLStatement } from "@/lib/financeApiClient";
import { adaptPnLStatement } from "@/lib/pnlAdapter";

// New Components
import FinanceHeader from "./components/FinanceHeader";
import FinanceKpiCards from "./components/FinanceKpiCards";
import FinancePLTable from "./components/FinancePLTable";
import FinanceSpendBreakdown from "./components/FinanceSpendBreakdown";
import FinanceRevenueChart from "./components/FinanceRevenueChart";
import FinanceCopilot from "./components/FinanceCopilot";

// Keep ManualCostModal for adding costs
import ManualCostModal from "./components/ManualCostModal";

/**
 * Get default date range (this month)
 */
function getDefaultDateRange() {
  const now = new Date();
  return {
    from: startOfMonth(now),
    to: endOfDay(now),
  };
}

export default function FinancePage() {
  // Auth state
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);

  // Date range state (replaces year/month)
  const [dateRange, setDateRange] = useState(getDefaultDateRange);

  // Data state
  const [viewModel, setViewModel] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Manual cost modal state
  const [showAddCost, setShowAddCost] = useState(false);
  const [editingCost, setEditingCost] = useState(null);
  const [manualCosts, setManualCosts] = useState([]);

  // ============================================
  // AUTH & DATA FETCHING
  // ============================================

  // Get current user
  useEffect(() => {
    let mounted = true;
    currentUser()
      .then((u) => {
        if (!mounted) return;
        setUser(u);
      })
      .catch((err) => {
        console.error("Failed to get user:", err);
        if (mounted) setUser(null);
      })
      .finally(() => {
        if (mounted) setAuthLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  // Fetch manual costs when user loads
  useEffect(() => {
    if (!user) return;

    async function fetchManualCosts() {
      try {
        const { listManualCosts } = await import("@/lib/financeApiClient");
        const costs = await listManualCosts({ workspaceId: user.workspace_id });
        setManualCosts(costs);
      } catch (err) {
        console.error("Failed to fetch manual costs:", err);
      }
    }

    fetchManualCosts();
  }, [user]);

  // Fetch P&L data when user/dateRange changes
  useEffect(() => {
    if (!user || !dateRange?.from || !dateRange?.to) return;

    async function fetchData() {
      setLoading(true);
      setError(null);

      try {
        // Format dates for API (YYYY-MM-DD)
        const periodStart = format(dateRange.from, "yyyy-MM-dd");
        const periodEnd = format(dateRange.to, "yyyy-MM-dd");

        const apiResponse = await getPnLStatement({
          workspaceId: user.workspace_id,
          granularity: "month",
          periodStart,
          periodEnd,
          compare: true,
        });

        const adapted = adaptPnLStatement(apiResponse);
        setViewModel(adapted);
      } catch (err) {
        console.error("Failed to fetch P&L:", err);
        setError("Failed to load financial data. Please try again.");
        toast.error("Finance data failed to load");
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [user, dateRange]);

  // ============================================
  // COMPUTED VALUES
  // ============================================

  // Calculate totals from viewModel
  const totals = useMemo(() => {
    if (!viewModel) return { totalRevenue: 0, totalSpend: 0, netProfit: 0 };

    const totalRevenue = viewModel.summary?.totalRevenue?.rawValue || 0;
    const totalSpend = viewModel.rows?.reduce((sum, row) => sum + (row.actualRaw || 0), 0) || 0;
    const netProfit = totalRevenue - totalSpend;

    return { totalRevenue, totalSpend, netProfit };
  }, [viewModel]);

  // Get selected period info for Copilot
  const selectedPeriod = useMemo(() => {
    if (!dateRange?.from) {
      const now = new Date();
      return { year: now.getFullYear(), month: now.getMonth() + 1 };
    }
    return {
      year: dateRange.from.getFullYear(),
      month: dateRange.from.getMonth() + 1,
    };
  }, [dateRange]);

  // ============================================
  // EVENT HANDLERS
  // ============================================

  const handleDateRangeChange = (newRange) => {
    setDateRange(newRange);
  };

  const handleAddCost = () => {
    setEditingCost(null);
    setShowAddCost(true);
  };

  const handleEditCost = (row) => {
    // Row contains costIds array from backend (list of UUIDs that make up this aggregated category)
    // If there's exactly one cost in this category, open the edit modal directly
    // If there are multiple, we could show a list picker (future enhancement)
    const costIds = row.costIds || [];
    
    if (costIds.length === 0) {
      // Fallback: try to find by category (for backward compatibility)
      const byCategory = manualCosts.filter((c) => c.category === row.category);
      if (byCategory.length === 1) {
        setEditingCost(byCategory[0]);
        setShowAddCost(true);
      } else if (byCategory.length > 1) {
        toast.info(`${byCategory.length} costs in this category. Please manage them individually from the costs list.`);
      }
      return;
    }
    
    if (costIds.length === 1) {
      // Single cost - open edit modal directly
      const fullCost = manualCosts.find((c) => c.id === costIds[0]);
      if (fullCost) {
        setEditingCost(fullCost);
        setShowAddCost(true);
      }
    } else {
      // Multiple costs aggregated - inform user
      toast.info(`${costIds.length} costs in "${row.category}". Click "Add Cost" to manage individual entries.`);
    }
  };

  const handleSubmitCost = async (payload) => {
    try {
      if (editingCost) {
        const { updateManualCost } = await import("@/lib/financeApiClient");
        await updateManualCost({
          workspaceId: user.workspace_id,
          costId: editingCost.id,
          updates: payload,
        });
      } else {
        const { createManualCost } = await import("@/lib/financeApiClient");
        await createManualCost({ workspaceId: user.workspace_id, cost: payload });
      }

      setShowAddCost(false);
      setEditingCost(null);

      // Refetch data
      const { listManualCosts } = await import("@/lib/financeApiClient");
      const costs = await listManualCosts({ workspaceId: user.workspace_id });
      setManualCosts(costs);

      const periodStart = format(dateRange.from, "yyyy-MM-dd");
      const periodEnd = format(dateRange.to, "yyyy-MM-dd");
      
      const apiResponse = await getPnLStatement({
        workspaceId: user.workspace_id,
        granularity: "month",
        periodStart,
        periodEnd,
        compare: true,
      });
      const adapted = adaptPnLStatement(apiResponse);
      setViewModel(adapted);

      toast.success(editingCost ? "Cost updated" : "Cost added");
    } catch (err) {
      console.error("Failed to save cost:", err);
      toast.error(err?.message || "Failed to save cost");
    }
  };

  const handleDeleteCost = async (costId) => {
    try {
      const { deleteManualCost } = await import("@/lib/financeApiClient");
      await deleteManualCost({ workspaceId: user.workspace_id, costId });

      setShowAddCost(false);
      setEditingCost(null);

      // Refetch data
      const { listManualCosts } = await import("@/lib/financeApiClient");
      const costs = await listManualCosts({ workspaceId: user.workspace_id });
      setManualCosts(costs);

      const periodStart = format(dateRange.from, "yyyy-MM-dd");
      const periodEnd = format(dateRange.to, "yyyy-MM-dd");
      
      const apiResponse = await getPnLStatement({
        workspaceId: user.workspace_id,
        granularity: "month",
        periodStart,
        periodEnd,
        compare: true,
      });
      const adapted = adaptPnLStatement(apiResponse);
      setViewModel(adapted);

      toast.success("Cost deleted");
    } catch (err) {
      console.error("Failed to delete cost:", err);
      toast.error(err?.message || "Failed to delete cost");
    }
  };

  // ============================================
  // RENDER
  // ============================================

  // Auth loading
  if (authLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-neutral-900 border-t-transparent rounded-full animate-spin" />
          <span className="text-neutral-500 text-sm">Checking authentication...</span>
        </div>
      </div>
    );
  }

  // Not authenticated
  if (!user) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="text-center">
          <h2 className="text-xl font-medium mb-2 text-neutral-900">
            You must be signed in.
          </h2>
          <a
            href="/sign-in"
            className="text-neutral-600 hover:text-neutral-900 underline"
          >
            Go to sign in
          </a>
        </div>
      </div>
    );
  }

  // Data loading
  if (loading && !viewModel) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-neutral-900 border-t-transparent rounded-full animate-spin" />
          <span className="text-neutral-500 text-sm">Loading financial data...</span>
        </div>
      </div>
    );
  }

  // Error state
  if (error && !viewModel) {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700">
          {error}
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Header with Date Range Picker */}
      <FinanceHeader
        dateRange={dateRange}
        onDateRangeChange={handleDateRangeChange}
      />

      {/* Main Content */}
      <div className="space-y-4 md:space-y-6 max-w-[1600px] mx-auto pb-16 md:pb-0">
        {/* KPI Cards */}
        <FinanceKpiCards
          summary={viewModel?.summary}
          loading={loading}
          currency="EUR"
        />

        {/* Middle Section: P&L + Spend Breakdown */}
        <section className="grid grid-cols-12 gap-4 md:gap-6">
          {/* P&L Table */}
          <div className="col-span-12 xl:col-span-7">
            <FinancePLTable
              rows={viewModel?.rows || []}
              totalRevenue={totals.totalRevenue}
              netProfit={totals.netProfit}
              onAddCost={handleAddCost}
              onEditCost={handleEditCost}
              loading={loading}
              currency="EUR"
            />
          </div>

          {/* Spend Breakdown */}
          <div className="col-span-12 xl:col-span-5">
            <FinanceSpendBreakdown
              composition={viewModel?.composition || []}
              totalRevenue={totals.totalRevenue}
              totalSpend={totals.totalSpend}
              loading={loading}
              currency="EUR"
            />
          </div>
        </section>

        {/* Bottom Section: Chart + Copilot */}
        <section className="grid grid-cols-12 gap-4 md:gap-6">
          {/* Revenue Chart */}
          <div className="col-span-12 xl:col-span-8">
            <FinanceRevenueChart
              timeseries={viewModel?.timeseries || []}
              loading={loading}
              currency="EUR"
            />
          </div>

          {/* AI Copilot */}
          <div className="col-span-12 xl:col-span-4">
            <FinanceCopilot
              workspaceId={user.workspace_id}
              selectedPeriod={selectedPeriod}
              summary={viewModel?.summary}
            />
          </div>
        </section>
      </div>

      {/* Manual Cost Modal */}
      {showAddCost && (
        <ManualCostModal
          open={showAddCost}
          onClose={() => {
            setShowAddCost(false);
            setEditingCost(null);
          }}
          onSubmit={handleSubmitCost}
          onDelete={handleDeleteCost}
          defaultMonth={selectedPeriod.month}
          defaultYear={selectedPeriod.year}
          editingCost={editingCost}
        />
      )}
    </>
  );
}
