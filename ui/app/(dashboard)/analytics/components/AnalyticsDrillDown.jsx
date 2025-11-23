/**
 * AnalyticsDrillDown Component
 * ==============================
 * 
 * WHAT:
 *   A dynamic drill-down interface for campaign performance analytics.
 *   Shows campaigns by default, and switches to ad sets when a campaign is selected.
 *   Also displays top-performing creatives for Meta campaigns.
 * 
 * WHY:
 *   Marketing analysts need to explore performance data at different hierarchy levels
 *   (campaigns → ad sets → ads) and filter by advertising platforms (Meta, Google, etc.)
 *   without navigating to different pages.
 * 
 * HOW IT WORKS:
 *   1. **Provider Filtering**: When user selects a provider (e.g., "Meta"), only campaigns
 *      from that provider are shown. This is done by passing the provider to the API.
 * 
 *   2. **Campaign Drill-Down**: When user selects a campaign from the filter modal,
 *      the table switches from showing campaigns to showing ad sets within that campaign.
 * 
 *   3. **Meta Creatives**: Shows top Meta creatives for the selected date range,
 *      regardless of other filters, so users always get fresh creative insights.
 * 
 * DYNAMIC BEHAVIOR:
 *   - selectedProvider = 'all', selectedCampaign = null → Show all campaigns
 *   - selectedProvider = 'meta', selectedCampaign = null → Show only Meta campaigns
 *   - selectedProvider = 'all', selectedCampaign = {id: 'xyz'} → Show ad sets in campaign xyz
 *   - selectedProvider = 'meta', selectedCampaign = {id: 'xyz'} → Show ad sets + top creatives
 *   - rangeDays = 7 → Show data for last 7 days
 *   - rangeDays = 30 → Show data for last 30 days
 *   - customStartDate & customEndDate set → Show data for custom date range
 * 
 * PROPS:
 *   @param {string} workspaceId - Current workspace identifier
 *   @param {string} selectedProvider - Current provider filter ('all', 'meta', 'google', etc.)
 *   @param {number} rangeDays - Number of days for data range
 *   @param {string} customStartDate - Custom date range start (optional)
 *   @param {string} customEndDate - Custom date range end (optional)
 *   @param {object} selectedCampaign - Selected campaign object with {id, name, platform}
 *   @param {string} selectedTimeframe - Selected timeframe preset ('7d', '30d', etc.)
 * 
 * REFERENCES:
 *   - /lib/api.js::fetchEntityPerformance - API client for entity metrics
 *   - /analytics/page.jsx - Parent component that manages filter state
 *   - /backend/app/routers/entity_performance.py - Backend API endpoint
 */
"use client";
import { useEffect, useState } from "react";
import { fetchEntityPerformance } from "@/lib/api";
import { Facebook, Instagram, Filter, Download, ArrowUp, ArrowUpRight, Minus } from "lucide-react";

export default function AnalyticsDrillDown({
    workspaceId,
    selectedProvider,
    timeFilters,
    selectedCampaign,
}) {
    const [data, setData] = useState([]);
    const [creatives, setCreatives] = useState([]);
    const [loading, setLoading] = useState(true);
    const [expandedRow, setExpandedRow] = useState(null);

    const metaProvider = 'meta';
    const isMetaCampaign = selectedCampaign?.platform?.toLowerCase()?.includes('meta');
    const showGlobalMetaCreatives = !selectedCampaign && (selectedProvider === 'meta' || selectedProvider === 'all');
    const showCampaignMetaCreatives = Boolean(selectedCampaign && isMetaCampaign);
    const shouldShowCreatives = showGlobalMetaCreatives || showCampaignMetaCreatives;

    // Determine the context
    // 1. If selectedProvider is 'all', show cross-platform campaigns/ads
    // 2. If selectedProvider is specific (e.g. 'meta'), filter by that provider
    // 3. If selectedCampaign is set, drill down into ad sets
    // 4. Time filters apply to all data fetches
    //
    // BEHAVIOR MATRIX:
    // | selectedProvider | selectedCampaign | timeFilters | Result                                    |
    // |------------------|------------------|-------------|-------------------------------------------|
    // | all              | null             | any         | All campaigns, all platforms, time filter |
    // | meta             | null             | any         | Meta campaigns only, time filter          |
    // | google           | null             | any         | Google campaigns only, time filter        |
    // | meta             | campaign_123     | any         | Ad sets within campaign_123, time filter  |
    // | all              | campaign_123     | any         | Ad sets within campaign_123, time filter  |
    //
    // KEY FEATURES:
    // - **Provider Filtering**: Filters campaign/ad set data by selected ad platform (Meta, Google, TikTok, Other)
    // - **Campaign Drill-Down**: Shows ad sets when a campaign is selected; returns to campaigns when cleared
    // - **Top Creatives**: Fetches and displays creative ranking (Meta context only, when no campaign selected)
    // - **Time Filter Dynamics**: All data respects selected time range (preset or custom dates)
    // - **Dynamic Titles**: Headers reflect current context (provider + campaign selection state)

    useEffect(() => {
        if (!workspaceId) return;

        setLoading(true);
        let mounted = true;

        // SECTION 0: Provider filter logic
        // WHY: If user picks 'Meta', we should only show Meta entities. If 'all', show everything.
        // WHAT: We translate 'all' -> null for the API (means "no filter")
        const providerFilter = selectedProvider === 'all' ? null : selectedProvider;

        // SECTION 1: Build timeRange object
        // WHY: API expects either {start, end} for custom dates or {last_n_days} for presets
        // WHAT: This ensures data is fetched for the correct time period
        const buildTimeRange = () => {
            if (timeFilters.type === 'custom' && timeFilters.customStart && timeFilters.customEnd) {
                return {
                    start: timeFilters.customStart,
                    end: timeFilters.customEnd
                };
            }
            return {
                last_n_days: timeFilters.rangeDays
            };
        };

        const timeRange = buildTimeRange();

        // Base parameters shared across all API calls
        const baseParams = {
            workspaceId,
            timeRange,
            provider: providerFilter
        };

        const fetchMetaAds = async () => {
            const response = await fetchEntityPerformance({
                workspaceId,
                entityType: 'ad',
                timeRange,
                provider: metaProvider,
                limit: 50,
                sortBy: 'roas',
                sortDir: 'desc',
                status: 'all'
            }).catch(err => {
                console.error('Failed to fetch creatives:', err);
                return { items: [] };
            });
            return response?.items || [];
        };

        const fetchCampaignCreatives = async (adsetIds = []) => {
            const requests = adsetIds.map(adsetId =>
                fetchEntityPerformance({
                    workspaceId,
                    entityType: 'ad',
                    timeRange,
                    provider: metaProvider,
                    campaignId: adsetId,
                    limit: 20,
                    sortBy: 'roas',
                    sortDir: 'desc',
                    status: 'all'
                }).catch(err => {
                    console.error(`Failed to fetch creatives for ad set ${adsetId}:`, err);
                    return { items: [] };
                })
            );
            const results = await Promise.all(requests);
            return results.flatMap(res => res?.items || []);
        };

        const loadData = async () => {
            try {
                const tablePromise = selectedCampaign
                    ? fetchEntityPerformance({
                        ...baseParams,
                        entityType: 'adset',
                        campaignId: selectedCampaign.id,
                        limit: 10,
                        sortBy: 'roas',
                        sortDir: 'desc',
                        status: 'active'
                    }).catch(err => {
                        console.error('Failed to fetch ad sets:', err);
                        return { items: [] };
                    })
                    : fetchEntityPerformance({
                        ...baseParams,
                        entityType: 'campaign',
                        limit: 10,
                        sortBy: 'roas',
                        sortDir: 'desc',
                        status: 'active'
                    }).catch(err => {
                        console.error('Failed to fetch campaigns:', err);
                        return { items: [] };
                    });

                const creativesPromise = shouldShowCreatives ? fetchMetaAds() : Promise.resolve([]);
                const [tableRes, globalCreatives] = await Promise.all([tablePromise, creativesPromise]);

                if (!mounted) return;
                setData(tableRes?.items || []);

                if (shouldShowCreatives) {
                    let creativesSource = globalCreatives;
                    if (showCampaignMetaCreatives && selectedCampaign) {
                        const adsetIds = (tableRes?.items || []).map(item => item.id).slice(0, 5);
                        const campaignCreatives = await fetchCampaignCreatives(adsetIds);
                        creativesSource = campaignCreatives.length > 0 ? campaignCreatives : globalCreatives;
                    }

                    const seen = new Set();
                    const creativesList = creativesSource
                        .filter(creative => {
                            if (!creative?.id || seen.has(creative.id)) return false;
                            seen.add(creative.id);
                            return true;
                        })
                        .sort((a, b) => (b.roas || 0) - (a.roas || 0))
                        .slice(0, 5);
                    setCreatives(creativesList);
                } else {
                    setCreatives([]);
                }
            } finally {
                if (mounted) setLoading(false);
            }
        };

        loadData();

        return () => {
            mounted = false;
        };
    }, [workspaceId, selectedProvider, selectedCampaign, showGlobalMetaCreatives, showCampaignMetaCreatives, shouldShowCreatives, timeFilters.type, timeFilters.rangeDays, timeFilters.customStart, timeFilters.customEnd]);

    const formatCurrency = (val) => `$${(val || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
    const formatRoas = (val) => `${(val || 0).toFixed(2)}x`;
    const formatPct = (val) => `${((val || 0) * 100).toFixed(1)}%`;

    const isMetaContext = shouldShowCreatives;

    const getPlatformIcon = (platform) => {
        if (!platform) return <div className="w-3 h-3 bg-slate-400 rounded-full"></div>;
        const p = platform.toLowerCase();
        if (p.includes('facebook') || p.includes('meta')) return <Facebook className="w-3 h-3 text-white fill-current" />;
        if (p.includes('instagram')) return <Instagram className="w-3 h-3 text-white" />;
        return <div className="w-3 h-3 bg-slate-400 rounded-full"></div>;
    };

    /**
     * WHAT: Helper to generate contextual title for the Creative Ranking section
     * WHY: Clear labeling helps users understand which data they're viewing
     */
    const getCreativesTitle = () => {
        if (showCampaignMetaCreatives && selectedCampaign) return `Top Meta Creatives (${selectedCampaign.name}) (Top 5)`;
        return 'Top Meta Creatives (Top 5)';
    };

    /**
     * WHAT: Helper to generate contextual title for the Performance Table
     * WHY: Users need to know if they're viewing campaigns or ad sets, and for which provider
     */
    const getTableTitle = () => {
        const suffix = ' (Top 5)';
        if (selectedCampaign) {
            return `Ad Sets: ${selectedCampaign.name}${suffix}`;
        }
        if (selectedProvider !== 'all') {
            const providerName = selectedProvider.charAt(0).toUpperCase() + selectedProvider.slice(1);
            return `${providerName} Campaigns${suffix}`;
        }
        return `Campaign Performance${suffix}`;
    };

    return (
        <section className="grid grid-cols-1 xl:grid-cols-3 gap-6 animate-slide-up pb-10" style={{ animationDelay: '0.4s' }}>

            {/* Left: Creative Ranking */}
            <div className="xl:col-span-1 flex flex-col gap-4">
                <div className="flex justify-between items-center">
                    <h3 className="text-sm font-semibold text-slate-700">
                        {getCreativesTitle()}
                    </h3>
                    <button onClick={() => window.location.href = '/campaigns'} className="text-[10px] text-slate-500 hover:text-slate-800">View All</button>
                </div>

                {!isMetaContext ? (
                    <div className="glass-panel p-6 rounded-2xl text-center">
                        <div className="flex flex-col items-center gap-3">
                            <Facebook className="w-8 h-8 text-slate-300" />
                            <p className="text-xs text-slate-500 font-medium">Only available with Meta for now</p>
                            <p className="text-[10px] text-slate-400">Select Meta from the provider filter to view top creatives</p>
                        </div>
                    </div>
                ) : loading ? (
                    [1, 2].map(i => (
                        <div key={i} className="glass-panel p-3 rounded-2xl h-20 animate-pulse"></div>
                    ))
                ) : creatives.length === 0 ? (
                    <div className="glass-panel p-4 rounded-2xl text-center text-xs text-slate-400">No creative data available</div>
                ) : (
                    creatives.map((ad, idx) => (
                        <div key={ad.id || idx} className="glass-panel p-3 rounded-2xl flex items-center gap-4 hover:scale-[1.02] transition-transform duration-300 shadow-glass-hover cursor-pointer border border-transparent hover:border-cyan-200">
                            <div className="relative w-16 h-16 rounded-lg overflow-hidden shadow-sm bg-slate-200">
                                {ad.thumbnail_url ? (
                                    <img src={ad.thumbnail_url} className="w-full h-full object-cover" alt={ad.name} />
                                ) : (
                                    <div className="w-full h-full bg-gradient-to-br from-slate-200 to-slate-300 flex items-center justify-center text-xs text-slate-400">No Img</div>
                                )}
                                <div className="absolute bottom-0 left-0 w-full bg-black/50 backdrop-blur-sm py-0.5 text-center flex justify-center">
                                    {getPlatformIcon(ad.platform)}
                                </div>
                            </div>
                            <div className="flex-1 min-w-0">
                                <div className="text-xs font-bold text-slate-700 truncate" title={ad.name}>{ad.name}</div>
                                <div className="grid grid-cols-2 gap-2 mt-1 text-[10px] text-slate-500">
                                    <div>ROAS: <span className="text-emerald-600 font-bold">{formatRoas(ad.roas)}</span></div>
                                    <div className="text-right">Spend: <span className="text-slate-700 font-medium">{formatCurrency(ad.spend)}</span></div>
                                    <div>Revenue: <span className="text-emerald-600 font-bold">{formatCurrency(ad.revenue)}</span></div>
                                </div>
                            </div>
                        </div>
                    ))
                )}
            </div>

            {/* Right: Performance Table */}
            <div className="xl:col-span-2 glass-panel rounded-[24px] overflow-hidden flex flex-col">
                <div className="p-4 border-b border-white/60 flex justify-between items-center">
                    <h3 className="text-sm font-semibold text-slate-700">
                        {getTableTitle()}
                    </h3>
                    <div>
                        <button onClick={() => window.location.href = '/campaigns'} className="text-[10px] text-slate-500 hover:text-slate-800">View All</button>
                    </div>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                        <thead className="bg-slate-50/50 text-[10px] uppercase tracking-wider text-slate-400 font-semibold">
                            <tr>
                                <th className="px-6 py-3">{selectedCampaign ? 'Ad Set' : 'Campaign'}</th>
                                <th className="px-6 py-3">Status</th>
                                <th className="px-6 py-3 text-right">Spend</th>
                                <th className="px-6 py-3 text-right">ROAS</th>
                                <th className="px-6 py-3 text-right">Revenue</th>
                            </tr>
                        </thead>
                        <tbody className="text-sm divide-y divide-slate-100">
                            {loading ? (
                                <tr><td colSpan="5" className="px-6 py-8 text-center text-slate-400">Loading data...</td></tr>
                            ) : data.length === 0 ? (
                                <tr><td colSpan="5" className="px-6 py-8 text-center text-slate-400">No active items found</td></tr>
                            ) : (
                                data.slice(0, 5).map((item) => (
                                    <tr key={item.id} className="table-row-animate group cursor-pointer">
                                        <td className="px-6 py-4 font-medium text-slate-700">
                                            <div className="truncate max-w-[200px]" title={item.name}>{item.name}</div>
                                            {!selectedCampaign && (
                                                <div className="text-[10px] text-slate-400 font-normal capitalize">{item.platform || 'Unknown'} • {item.objective || 'Conversion'}</div>
                                            )}
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-100/50 text-emerald-600 text-[10px] font-medium border border-emerald-200">
                                                <span className="w-1 h-1 rounded-full bg-emerald-500 animate-pulse"></span> Active
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 text-right text-slate-600">{formatCurrency(item.spend)}</td>
                                        <td className="px-6 py-4 text-right">
                                            <div className="flex items-center justify-end gap-1">
                                                <span className="font-bold text-slate-800">{formatRoas(item.roas)}</span>
                                                <ArrowUp className="w-3 h-3 text-emerald-500" />
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 text-right font-medium text-emerald-600 bg-emerald-50/10 group-hover:bg-emerald-50/30 transition-colors">
                                            {formatCurrency(item.revenue)}
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </section>
    );
}
