"use client";
/**
 * AnalyticsDataSourcePanel Component
 * ===================================
 *
 * WHAT: Platform and campaign multi-select panel for filtering chart data
 * WHY: Allow users to drill down into specific platforms/campaigns
 *
 * RELATED:
 * - AnalyticsGraphEngine.jsx (receives selected platforms/campaigns)
 * - page.jsx (manages selection state)
 */
import { useState, memo, useCallback } from "react";
import { ChevronDown, ChevronRight, Check, Layers, Target } from "lucide-react";

/**
 * All possible ad platforms with their display config.
 * Only platforms that are connected will be shown.
 * NOTE: Shopify excluded per CLAUDE.md - analytics is for ad platforms only
 */
const ALL_PLATFORMS = [
    { key: 'meta', label: 'Meta Ads', color: '#1877F2' },
    { key: 'google', label: 'Google Ads', color: '#4285F4' },
    { key: 'tiktok', label: 'TikTok Ads', color: '#000000' },
];

/**
 * Checkbox component for selection lists.
 * Extracted to prevent recreation on parent re-renders.
 */
const SelectionCheckbox = memo(function SelectionCheckbox({
    checked,
    onChange,
    label,
    color,
    sublabel
}) {
    return (
        <button
            onClick={onChange}
            className="w-full flex items-center gap-2 p-2 rounded-lg hover:bg-white/50 transition-colors text-left group"
        >
            <div className={`
                w-4 h-4 rounded border-2 flex items-center justify-center transition-all shrink-0
                ${checked
                    ? 'bg-cyan-500 border-cyan-500'
                    : 'border-slate-300 group-hover:border-slate-400'
                }
            `}>
                {checked && <Check className="w-3 h-3 text-white" strokeWidth={3} />}
            </div>
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                    {color && (
                        <div
                            className="w-2 h-2 rounded-full shrink-0"
                            style={{ backgroundColor: color }}
                        />
                    )}
                    <span className="text-xs text-slate-700 truncate">{label}</span>
                </div>
                {sublabel && (
                    <span className="text-[10px] text-slate-400 truncate block">{sublabel}</span>
                )}
            </div>
        </button>
    );
});

/**
 * Collapsible section header with select all toggle.
 */
const SectionHeader = memo(function SectionHeader({
    icon: Icon,
    title,
    expanded,
    onToggle,
    selectedCount,
    totalCount,
    onSelectAll
}) {
    return (
        <div className="flex items-center justify-between mb-2">
            <button
                onClick={onToggle}
                className="flex items-center gap-2 text-xs font-semibold text-slate-600 hover:text-slate-800 transition-colors"
            >
                {expanded ? (
                    <ChevronDown className="w-3.5 h-3.5" />
                ) : (
                    <ChevronRight className="w-3.5 h-3.5" />
                )}
                <Icon className="w-3.5 h-3.5" />
                <span>{title}</span>
            </button>
            <div className="flex items-center gap-2">
                <span className="text-[10px] text-slate-400">
                    {selectedCount}/{totalCount}
                </span>
                <button
                    onClick={onSelectAll}
                    className="text-[10px] text-cyan-600 hover:text-cyan-700 font-medium"
                >
                    {selectedCount === totalCount ? 'Clear' : 'All'}
                </button>
            </div>
        </div>
    );
});

/**
 * Maximum campaigns to show in scrollable list.
 * Campaigns beyond this require scrolling.
 */
const MAX_VISIBLE_CAMPAIGNS = 5;

export default function AnalyticsDataSourcePanel({
    campaigns = [],
    connectedPlatforms = [],
    selectedPlatforms = [],
    onPlatformsChange,
    selectedCampaigns = [],
    onCampaignsChange
}) {
    const [platformsExpanded, setPlatformsExpanded] = useState(true);
    const [campaignsExpanded, setCampaignsExpanded] = useState(true);

    // Filter platforms to only show connected ones
    const availablePlatforms = ALL_PLATFORMS.filter(p =>
        connectedPlatforms.includes(p.key)
    );

    // Toggle platform selection
    const togglePlatform = useCallback((platformKey) => {
        if (selectedPlatforms.includes(platformKey)) {
            onPlatformsChange(selectedPlatforms.filter(p => p !== platformKey));
        } else {
            onPlatformsChange([...selectedPlatforms, platformKey]);
        }
    }, [selectedPlatforms, onPlatformsChange]);

    // Toggle campaign selection
    const toggleCampaign = useCallback((campaignId) => {
        if (selectedCampaigns.includes(campaignId)) {
            onCampaignsChange(selectedCampaigns.filter(c => c !== campaignId));
        } else {
            onCampaignsChange([...selectedCampaigns, campaignId]);
        }
    }, [selectedCampaigns, onCampaignsChange]);

    // Select/deselect all platforms
    const toggleAllPlatforms = useCallback(() => {
        if (selectedPlatforms.length === availablePlatforms.length) {
            onPlatformsChange([]);
        } else {
            onPlatformsChange(availablePlatforms.map(p => p.key));
        }
    }, [selectedPlatforms.length, availablePlatforms, onPlatformsChange]);

    // Select/deselect all campaigns
    const toggleAllCampaigns = useCallback(() => {
        if (selectedCampaigns.length === campaigns.length) {
            onCampaignsChange([]);
        } else {
            onCampaignsChange(campaigns.map(c => c.id || c.campaign_id));
        }
    }, [selectedCampaigns.length, campaigns, onCampaignsChange]);

    return (
        <div className="dashboard-module flex-1 overflow-hidden flex flex-col">
            <h3 className="text-[11px] font-medium uppercase tracking-[0.12em] text-slate-500 mb-4">
                Data Sources
            </h3>

            {/* Platforms Section */}
            <div className="mb-4">
                <SectionHeader
                    icon={Layers}
                    title="Platforms"
                    expanded={platformsExpanded}
                    onToggle={() => setPlatformsExpanded(!platformsExpanded)}
                    selectedCount={selectedPlatforms.length}
                    totalCount={availablePlatforms.length}
                    onSelectAll={toggleAllPlatforms}
                />
                {platformsExpanded && (
                    <div className="space-y-0.5 ml-1">
                        {availablePlatforms.length === 0 ? (
                            <div className="text-[10px] text-slate-400 p-2 text-center">
                                No platforms connected
                            </div>
                        ) : (
                            availablePlatforms.map((platform) => (
                                <SelectionCheckbox
                                    key={platform.key}
                                    checked={selectedPlatforms.includes(platform.key)}
                                    onChange={() => togglePlatform(platform.key)}
                                    label={platform.label}
                                    color={platform.color}
                                />
                            ))
                        )}
                    </div>
                )}
            </div>

            {/* Campaigns Section */}
            <div className="flex-1 overflow-hidden flex flex-col min-h-0">
                <SectionHeader
                    icon={Target}
                    title="Campaigns"
                    expanded={campaignsExpanded}
                    onToggle={() => setCampaignsExpanded(!campaignsExpanded)}
                    selectedCount={selectedCampaigns.length}
                    totalCount={campaigns.length}
                    onSelectAll={toggleAllCampaigns}
                />
                {campaignsExpanded && (
                    <div
                        className="overflow-y-auto space-y-0.5 ml-1 pr-1 -mr-1"
                        style={{
                            maxHeight: `${MAX_VISIBLE_CAMPAIGNS * 44}px` // ~44px per item
                        }}
                    >
                        {campaigns.length === 0 ? (
                            <div className="text-[10px] text-slate-400 p-2 text-center">
                                No campaigns available
                            </div>
                        ) : (
                            campaigns.map((campaign) => {
                                const campaignId = campaign.id || campaign.campaign_id;
                                const campaignName = campaign.name || campaign.campaign_name || 'Unnamed Campaign';
                                // Spend comes from entity performance API as a number
                                const spend = campaign.spend ?? 0;

                                return (
                                    <SelectionCheckbox
                                        key={campaignId}
                                        checked={selectedCampaigns.includes(campaignId)}
                                        onChange={() => toggleCampaign(campaignId)}
                                        label={campaignName}
                                        sublabel={`$${Number(spend).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })} spend`}
                                    />
                                );
                            })
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
