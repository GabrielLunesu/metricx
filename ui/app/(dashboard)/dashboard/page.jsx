"use client";
import { useEffect, useState } from "react";
import { currentUser } from "../../../lib/auth";
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
        <KpiStrip workspaceId={user.workspace_id} timeframe={timeframe} />
      </div>

      {/* Middle Section: Money Pulse & AI Insights */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-8">
        <MoneyPulseChart workspaceId={user.workspace_id} timeframe={timeframe} />
        <AiInsightsPanel workspaceId={user.workspace_id} timeframe={timeframe} />
      </div>

      {/* Attribution Section */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mt-8">
        <AttributionCard workspaceId={user.workspace_id} timeframe={timeframe} />
        <LiveAttributionFeed workspaceId={user.workspace_id} />
      </div>

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
