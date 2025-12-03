/**
 * Dashboard Page - Primary ad analytics view.
 *
 * WHAT: Main dashboard showing ad performance metrics, charts, and insights
 * WHY: Users need a single place to see how their ads are performing
 *
 * CONDITIONAL RENDERING:
 *   - Attribution section only shows if Shopify is connected (has_shopify)
 *   - KPI source indicators show connected platforms dynamically
 *
 * REFERENCES:
 *   - docs/living-docs/FRONTEND_REFACTOR_PLAN.md
 *   - Strategic vision: Ad Analytics First, Attribution Second
 */
"use client";
import { useEffect, useState } from "react";
import { currentUser } from "../../../lib/auth";
import { fetchWorkspaceStatus } from "../../../lib/api";
import HeroHeader from "./components/HeroHeader";
import KpiStrip from "./components/KpiStrip";
import MoneyPulseChart from "./components/MoneyPulseChart";
import AiInsightsPanel from "./components/AiInsightsPanel";
import TopCreative from "./components/TopCreative";
import PlatformSpendMix from "./components/PlatformSpendMix";
import UnitEconomicsTable from "./components/UnitEconomicsTable";
import TimeframeSelector from "./components/TimeframeSelector";
import AttributionCard from "./components/AttributionCard";
import LiveAttributionFeed from "./components/LiveAttributionFeed";

export default function DashboardPage() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [timeframe, setTimeframe] = useState('last_7_days');

  // Workspace status for conditional rendering
  // WHY: Only show attribution widgets if Shopify is connected
  const [status, setStatus] = useState(null);

  useEffect(() => {
    let mounted = true;
    currentUser()
      .then((u) => {
        if (!mounted) return;
        setUser(u);

        // Fetch workspace status for conditional UI rendering
        if (u?.workspace_id) {
          fetchWorkspaceStatus({ workspaceId: u.workspace_id })
            .then((s) => {
              if (mounted) setStatus(s);
            })
            .catch((err) => {
              console.error("Failed to fetch workspace status:", err);
              // Don't block dashboard if status fetch fails
            });
        }
      })
      .catch((err) => {
        console.error("Failed to get user:", err);
        if (mounted) setUser(null);
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  if (loading) {
    return <div className="p-6 text-slate-500">Loading dashboard...</div>;
  }

  if (!user) {
    return (
      <div className="p-6">
        <div className="max-w-2xl mx-auto glass-panel rounded-3xl p-6">
          <h2 className="text-xl font-medium mb-2 text-slate-900">You must be signed in.</h2>
          <a href="/login" className="text-cyan-600 hover:text-cyan-700 underline">Go to sign in</a>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Hero Header */}
      <HeroHeader
        user={user}
        actions={<TimeframeSelector value={timeframe} onChange={setTimeframe} />}
      />

      {/* KPI Strip */}
      <div className="mt-8">
        <KpiStrip
          workspaceId={user.workspace_id}
          timeframe={timeframe}
          connectedPlatforms={status?.connected_platforms}
        />
      </div>

      {/* Middle Section: Money Pulse & AI Insights */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-8">
        <MoneyPulseChart workspaceId={user.workspace_id} timeframe={timeframe} />
        <AiInsightsPanel workspaceId={user.workspace_id} timeframe={timeframe} />
      </div>

      {/* Attribution Section - Only show if Shopify is connected */}
      {/* WHY: Attribution requires Shopify for order data. Without it, these widgets
          would show empty states, making the product feel incomplete.
          Reference: docs/living-docs/FRONTEND_REFACTOR_PLAN.md */}
      {status?.has_shopify && (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mt-8">
          <AttributionCard workspaceId={user.workspace_id} timeframe={timeframe} />
          <LiveAttributionFeed workspaceId={user.workspace_id} />
        </div>
      )}

      {/* Bottom Section: Top Ads & Product Table */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mt-8 pb-8">
        <TopCreative workspaceId={user.workspace_id} timeframe={timeframe} />
        <div className="flex flex-col gap-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-medium text-slate-800 tracking-tight">Platform Spend Mix</h3>
          </div>
          <PlatformSpendMix workspaceId={user.workspace_id} timeframe={timeframe} />
          <UnitEconomicsTable workspaceId={user.workspace_id} timeframe={timeframe} />
        </div>
      </div>
    </div>
  );
}
