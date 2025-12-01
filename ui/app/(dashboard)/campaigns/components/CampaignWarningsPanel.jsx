'use client';

/**
 * CampaignWarningsPanel component for Campaigns page.
 *
 * WHAT: Displays campaigns that have attribution issues (no UTMs, no orders, etc.)
 * WHY: Users need to know which campaigns aren't being tracked properly
 *
 * REFERENCES:
 * - docs/ATTRIBUTION_UX_COMPREHENSIVE_PLAN.md (Campaign Attribution Warnings section)
 * - backend/app/routers/attribution.py (warnings endpoint)
 */

import { useState, useEffect } from 'react';
import { AlertTriangle, ChevronDown, ChevronUp, ExternalLink, X } from 'lucide-react';
import { fetchCampaignWarnings } from '@/lib/api';

/**
 * Get warning type styling
 */
function getWarningStyle(type) {
    const styles = {
        no_attribution: {
            bg: 'bg-red-50',
            border: 'border-red-200',
            icon: 'text-red-500',
            text: 'text-red-700',
            label: 'No Attribution',
        },
        no_utm: {
            bg: 'bg-amber-50',
            border: 'border-amber-200',
            icon: 'text-amber-500',
            text: 'text-amber-700',
            label: 'Missing UTMs',
        },
        low_confidence: {
            bg: 'bg-orange-50',
            border: 'border-orange-200',
            icon: 'text-orange-500',
            text: 'text-orange-700',
            label: 'Low Confidence',
        },
    };
    return styles[type] || styles.no_attribution;
}

/**
 * Single warning item
 */
function WarningItem({ warning, onDismiss }) {
    const style = getWarningStyle(warning.warning_type);

    return (
        <div className={`p-3 ${style.bg} ${style.border} border rounded-lg`}>
            <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3 flex-1">
                    <AlertTriangle className={`w-4 h-4 ${style.icon} flex-shrink-0 mt-0.5`} />
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                            <span className="font-medium text-sm text-neutral-900 truncate">
                                {warning.campaign_name}
                            </span>
                            <span className={`px-1.5 py-0.5 text-[10px] font-medium rounded ${style.bg} ${style.text}`}>
                                {style.label}
                            </span>
                        </div>
                        <p className={`text-xs ${style.text}`}>
                            {warning.message}
                        </p>
                        {warning.attributed_orders > 0 && (
                            <p className="text-xs text-neutral-500 mt-1">
                                {warning.attributed_orders} orders attributed
                            </p>
                        )}
                    </div>
                </div>
                {onDismiss && (
                    <button
                        onClick={() => onDismiss(warning.campaign_id)}
                        className="p-1 text-neutral-400 hover:text-neutral-600 rounded"
                    >
                        <X className="w-3 h-3" />
                    </button>
                )}
            </div>
        </div>
    );
}

export default function CampaignWarningsPanel({ workspaceId }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [expanded, setExpanded] = useState(true);
    const [dismissedIds, setDismissedIds] = useState(new Set());

    useEffect(() => {
        if (!workspaceId) return;

        async function loadWarnings() {
            try {
                setLoading(true);
                const result = await fetchCampaignWarnings({ workspaceId, days: 30 });
                setData(result);
                setError(null);
            } catch (err) {
                console.error('Failed to load campaign warnings:', err);
                setError(err.message);
            } finally {
                setLoading(false);
            }
        }

        loadWarnings();
    }, [workspaceId]);

    const handleDismiss = (campaignId) => {
        setDismissedIds((prev) => new Set([...prev, campaignId]));
    };

    // Filter out dismissed warnings
    const visibleWarnings = data?.warnings?.filter(
        (w) => !dismissedIds.has(w.campaign_id)
    ) || [];

    // Don't render if loading, error, or no warnings
    if (loading) return null;
    if (error) return null;
    if (visibleWarnings.length === 0) return null;

    return (
        <div className="mb-4 rounded-2xl border border-amber-200 bg-amber-50/50 overflow-hidden">
            {/* Header */}
            <button
                onClick={() => setExpanded(!expanded)}
                className="w-full px-4 py-3 flex items-center justify-between hover:bg-amber-100/50 transition-colors"
            >
                <div className="flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-amber-500" />
                    <span className="text-sm font-medium text-amber-800">
                        {visibleWarnings.length} campaign{visibleWarnings.length !== 1 ? 's' : ''} with attribution issues
                    </span>
                </div>
                <div className="flex items-center gap-2">
                    <a
                        href="/settings"
                        onClick={(e) => e.stopPropagation()}
                        className="text-xs text-amber-600 hover:text-amber-700 flex items-center gap-1"
                    >
                        Setup Guide
                        <ExternalLink className="w-3 h-3" />
                    </a>
                    {expanded ? (
                        <ChevronUp className="w-4 h-4 text-amber-500" />
                    ) : (
                        <ChevronDown className="w-4 h-4 text-amber-500" />
                    )}
                </div>
            </button>

            {/* Content */}
            {expanded && (
                <div className="px-4 pb-4 space-y-2">
                    {visibleWarnings.slice(0, 5).map((warning) => (
                        <WarningItem
                            key={warning.campaign_id}
                            warning={warning}
                            onDismiss={handleDismiss}
                        />
                    ))}
                    {visibleWarnings.length > 5 && (
                        <p className="text-xs text-amber-600 text-center pt-2">
                            +{visibleWarnings.length - 5} more campaigns with warnings
                        </p>
                    )}
                </div>
            )}
        </div>
    );
}
