/**
 * Finance & P&L Page
 * 
 * WHAT: Main Finance page with P&L statement, costs, and insights
 * WHY: Central view for financial performance
 * REFERENCES:
 *   - lib/financeApiClient.js: Data fetching
 *   - lib/pnlAdapter.js: View model mapping
 *   - components/*.jsx: Presentational components
 * 
 * State management:
 *   - selectedPeriod: {year, month} - User selection
 *   - compareEnabled: boolean - Toggle for comparison mode
 *   - viewModel: adapted P&L data (from adapter)
 *   - loading/error: UI states
 * 
 * Design:
 *   - Zero business logic (only display state)
 *   - Adapter handles all formatting
 *   - Components are presentational only
 */

"use client";
import { useState, useEffect } from "react";
import { currentUser } from "@/lib/auth";
import TopBar from "./components/TopBar";
import FinancialSummaryCards from "./components/FinancialSummaryCards";
import PLTable from "./components/PLTable";
import ManualCostModal from "./components/ManualCostModal";
import ChartsSection from "./components/ChartsSection";
import AIFinancialSummary from "./components/AIFinancialSummary";
import { getPnLStatement } from "@/lib/financeApiClient";
import { adaptPnLStatement, getPeriodDatesForMonth } from "@/lib/pnlAdapter";
import LoadingAnimation from "@/components/LoadingAnimation";

export default function FinancePage() {
  // Auth state
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);

  // UI state
  const [compareEnabled, setCompareEnabled] = useState(true);
  const [selectedPeriod, setSelectedPeriod] = useState(() => {
    const now = new Date();
    return { year: now.getFullYear(), month: now.getMonth() + 1 };
  });
  const [viewModel, setViewModel] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [excludedRows, setExcludedRows] = useState(new Set());
  const [showAddCost, setShowAddCost] = useState(false);
  const [editingCost, setEditingCost] = useState(null);
  const [manualCosts, setManualCosts] = useState([]);

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
        console.error('Failed to fetch manual costs:', err);
      }
    }

    fetchManualCosts();
  }, [user]);

  // Fetch P&L data when user/period/compare changes
  useEffect(() => {
    if (!user) return;

    async function fetchData() {
      setLoading(true);
      setError(null);

      try {
        const { periodStart, periodEnd } = getPeriodDatesForMonth(
          selectedPeriod.year,
          selectedPeriod.month
        );

        const apiResponse = await getPnLStatement({
          workspaceId: user.workspace_id,
          granularity: 'month',
          periodStart,
          periodEnd,
          compare: compareEnabled
        });

        const adapted = adaptPnLStatement(apiResponse);
        setViewModel(adapted);
      } catch (err) {
        console.error('Failed to fetch P&L:', err);
        setError('Failed to load financial data. Please try again.');
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [user, selectedPeriod, compareEnabled]);

  const handlePeriodChange = (period) => {
    setSelectedPeriod(period);
    setExcludedRows(new Set()); // Reset excluded rows when changing periods
  };

  const handleCompareToggle = (enabled) => {
    setCompareEnabled(enabled);
  };

  const handleRowToggle = (rowId) => {
    setExcludedRows(prev => {
      const newSet = new Set(prev);
      if (newSet.has(rowId)) {
        newSet.delete(rowId);
      } else {
        newSet.add(rowId);
      }
      return newSet;
    });
  };

  // Add/Edit manual cost
  const handleAddCost = () => {
    setEditingCost(null);
    setShowAddCost(true);
  };

  const handleEditCost = (cost) => {
    setEditingCost(cost);
    setShowAddCost(true);
  };

  const handleSubmitCost = async (payload) => {
    try {
      if (editingCost) {
        // Update existing cost
        const { updateManualCost } = await import("@/lib/financeApiClient");
        await updateManualCost({
          workspaceId: user.workspace_id,
          costId: editingCost.id,
          updates: payload
        });
      } else {
        // Create new cost
        const { createManualCost } = await import("@/lib/financeApiClient");
        await createManualCost({ workspaceId: user.workspace_id, cost: payload });
      }

      setShowAddCost(false);
      setEditingCost(null);

      // Refetch manual costs
      const { listManualCosts } = await import("@/lib/financeApiClient");
      const costs = await listManualCosts({ workspaceId: user.workspace_id });
      setManualCosts(costs);

      // Refetch P&L
      const { periodStart, periodEnd } = getPeriodDatesForMonth(
        selectedPeriod.year,
        selectedPeriod.month
      );
      const apiResponse = await getPnLStatement({
        workspaceId: user.workspace_id,
        granularity: 'month',
        periodStart,
        periodEnd,
        compare: compareEnabled
      });
      const adapted = adaptPnLStatement(apiResponse);
      setViewModel(adapted);
    } catch (err) {
      console.error('Failed to save cost:', err);
      alert('Failed to save cost: ' + err.message);
    }
  };

  const handleDeleteCost = async (costId) => {
    try {
      const { deleteManualCost } = await import("@/lib/financeApiClient");
      await deleteManualCost({ workspaceId: user.workspace_id, costId });

      setShowAddCost(false);
      setEditingCost(null);

      // Refetch manual costs
      const { listManualCosts } = await import("@/lib/financeApiClient");
      const costs = await listManualCosts({ workspaceId: user.workspace_id });
      setManualCosts(costs);

      // Refetch P&L
      const { periodStart, periodEnd } = getPeriodDatesForMonth(
        selectedPeriod.year,
        selectedPeriod.month
      );
      const apiResponse = await getPnLStatement({
        workspaceId: user.workspace_id,
        granularity: 'month',
        periodStart,
        periodEnd,
        compare: compareEnabled
      });
      const adapted = adaptPnLStatement(apiResponse);
      setViewModel(adapted);
    } catch (err) {
      console.error('Failed to delete cost:', err);
      alert('Failed to delete cost: ' + err.message);
    }
  };

  // Calculate adjusted totals based on excluded rows
  const getAdjustedTotals = () => {
    if (!viewModel) return { totalRevenue: 0, totalSpend: 0 };

    const activeSpend = viewModel.rows
      .filter(row => !excludedRows.has(row.id))
      .reduce((sum, row) => sum + (row.actualRaw || 0), 0);

    return {
      totalRevenue: viewModel.summary?.totalRevenue?.rawValue || 0,
      totalSpend: activeSpend
    };
  };

  // Auth loading state
  if (authLoading) {
    return <LoadingAnimation message="Checking authentication..." />;
  }

  // Not authenticated
  if (!user) {
    return (
      <div className="p-6">
        <div className="max-w-2xl mx-auto glass-card rounded-3xl border border-neutral-200/60 p-6">
          <h2 className="text-xl font-medium mb-2 text-neutral-900">You must be signed in.</h2>
          <a href="/" className="text-cyan-600 hover:text-cyan-700 underline">Go to sign in</a>
        </div>
      </div>
    );
  }

  // Loading P&L data
  if (loading) {
    return <LoadingAnimation message="Loading financial data..." />;
  }

  // Error state
  if (error) {
    return (
      <div className="p-8">
        <div className="bg-red-500/10 border border-red-500 rounded p-4 text-red-400">
          {error}
        </div>
      </div>
    );
  }

  // No data
  if (!viewModel) {
    return (
      <div className="p-8 text-gray-400">
        No financial data available for this period.
      </div>
    );
  }

  return (
    <>
      {/* Header / Controls */}
      <TopBar
        selectedPeriod={selectedPeriod}
        onPeriodChange={handlePeriodChange}
        compareEnabled={compareEnabled}
        onCompareToggle={handleCompareToggle}
      />

      {/* Main Finance Content */}
      <div className=" ">
        <div className="max-w-[1400px] mx-auto space-y-6">
          {/* Hero Finance Strip */}
          <FinancialSummaryCards
            summary={{
              ...viewModel.summary,
              totalSpend: {
                ...viewModel.summary.totalSpend,
                value: new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(getAdjustedTotals().totalSpend),
                rawValue: getAdjustedTotals().totalSpend
              },
              grossProfit: {
                ...viewModel.summary.grossProfit,
                value: new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(getAdjustedTotals().totalRevenue - getAdjustedTotals().totalSpend),
                rawValue: getAdjustedTotals().totalRevenue - getAdjustedTotals().totalSpend
              },
              netRoas: {
                ...viewModel.summary.netRoas,
                value: getAdjustedTotals().totalSpend > 0 ? `${(getAdjustedTotals().totalRevenue / getAdjustedTotals().totalSpend).toFixed(2)}×` : 'N/A',
                rawValue: getAdjustedTotals().totalSpend > 0 ? getAdjustedTotals().totalRevenue / getAdjustedTotals().totalSpend : 0
              }
            }}
            showComparison={viewModel.hasComparison}
          />

          {/* Middle Section: P&L + Charts + Composition + Copilot */}
          <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
            {/* Left Column: P&L + Revenue charts */}
            <div className="xl:col-span-7 flex flex-col gap-6">
              {/* Editable P&L Grid */}
              <PLTable
                selectedMonth={selectedPeriod.month}
                rows={viewModel.rows}
                excludedRows={excludedRows}
                onRowToggle={handleRowToggle}
                onAddCost={handleAddCost}
                manualCosts={manualCosts}
                onEditCost={handleEditCost}
                onDeleteCost={handleDeleteCost}
              />

              {/* Revenue Chart */}
              <ChartsSection
                composition={viewModel.composition}
                timeseries={viewModel.timeseries}
                totalRevenue={getAdjustedTotals().totalRevenue}
                totalSpend={getAdjustedTotals().totalSpend}
                excludedRows={excludedRows}
                rows={viewModel.rows}
                onRowToggle={handleRowToggle}
                mode="revenueOnly"
                selectedMonth={selectedPeriod.month}
              />
            </div>

            {/* Right Column: Composition + Financial Copilot */}
            <div className="xl:col-span-5 flex flex-col gap-6">
              <ChartsSection
                composition={viewModel.composition}
                timeseries={viewModel.timeseries}
                totalRevenue={getAdjustedTotals().totalRevenue}
                totalSpend={getAdjustedTotals().totalSpend}
                excludedRows={excludedRows}
                rows={viewModel.rows}
                onRowToggle={handleRowToggle}
                mode="compositionOnly"
                selectedMonth={selectedPeriod.month}
              />

              {/* Financial AI Summary (Copilot Integration) */}
              <AIFinancialSummary
                workspaceId={user.workspace_id}
                selectedPeriod={selectedPeriod}
              />
            </div>
          </div>
        </div>
      </div>

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
