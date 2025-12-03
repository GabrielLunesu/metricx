/**
 * AttributionTab - Attribution setup and status in Settings.
 *
 * WHAT: Shows attribution configuration status and campaign warnings
 * WHY: Attribution is secondary to ad analytics - it's a "verification layer"
 *      that enhances your numbers. This keeps it in settings, not front and center.
 *
 * REFERENCES:
 *   - .claude/CLAUDE.md (Ad Analytics First, Attribution Second strategy)
 *   - Previously: CampaignWarningsPanel on campaigns page
 */
'use client';

import { useState, useEffect } from 'react';
import { AlertTriangle, CheckCircle, ExternalLink, RefreshCw, Loader2 } from 'lucide-react';
import { fetchCampaignWarnings, fetchWorkspaceStatus } from '@/lib/api';
import UTMSetupGuide from './UTMSetupGuide';

/**
 * Get styling for warning types.
 */
function getWarningStyle(type) {
    switch (type) {
        case 'no_attribution':
            return {
                bg: 'bg-blue-50',
                border: 'border-blue-200',
                badge: 'bg-blue-100 text-blue-700',
                icon: 'text-blue-500',
                label: 'Waiting for Orders'
            };
        case 'no_utm':
            return {
                bg: 'bg-amber-50',
                border: 'border-amber-200',
                badge: 'bg-amber-100 text-amber-700',
                icon: 'text-amber-500',
                label: 'Missing UTMs'
            };
        case 'low_confidence':
            return {
                bg: 'bg-orange-50',
                border: 'border-orange-200',
                badge: 'bg-orange-100 text-orange-700',
                icon: 'text-orange-500',
                label: 'Low Confidence'
            };
        default:
            return {
                bg: 'bg-neutral-50',
                border: 'border-neutral-200',
                badge: 'bg-neutral-100 text-neutral-700',
                icon: 'text-neutral-500',
                label: 'Unknown'
            };
    }
}

/**
 * Single campaign status card.
 */
function CampaignStatusCard({ warning }) {
    const style = getWarningStyle(warning.warning_type);
    const isConfigured = warning.warning_type === 'no_attribution';

    return (
        <div className={`p-4 rounded-xl border ${style.border} ${style.bg}`}>
            <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                    {isConfigured ? (
                        <CheckCircle className="w-5 h-5 text-green-500 mt-0.5" />
                    ) : (
                        <AlertTriangle className={`w-5 h-5 ${style.icon} mt-0.5`} />
                    )}
                    <div>
                        <div className="flex items-center gap-2">
                            <span className="font-medium text-neutral-900">{warning.campaign_name}</span>
                            <span className={`text-xs px-2 py-0.5 rounded-full ${style.badge}`}>
                                {style.label}
                            </span>
                        </div>
                        <p className="text-sm text-neutral-600 mt-1">{warning.message}</p>
                        {warning.attributed_orders > 0 && (
                            <p className="text-xs text-neutral-500 mt-1">
                                {warning.attributed_orders} attributed order{warning.attributed_orders !== 1 ? 's' : ''}
                            </p>
                        )}
                    </div>
                </div>
                <span className="text-xs text-neutral-400 uppercase">{warning.provider}</span>
            </div>
        </div>
    );
}

export default function AttributionTab({ user }) {
    const [warnings, setWarnings] = useState([]);
    const [status, setStatus] = useState(null);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState(null);

    const loadData = async () => {
        if (!user?.workspace_id) return;

        try {
            const [warningsResult, statusResult] = await Promise.all([
                fetchCampaignWarnings({ workspaceId: user.workspace_id, days: 30 }),
                fetchWorkspaceStatus({ workspaceId: user.workspace_id })
            ]);
            setWarnings(warningsResult.warnings || []);
            setStatus(statusResult);
            setError(null);
        } catch (err) {
            console.error('Failed to load attribution data:', err);
            setError(err.message || 'Failed to load attribution data');
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    useEffect(() => {
        loadData();
    }, [user?.workspace_id]);

    const handleRefresh = () => {
        setRefreshing(true);
        loadData();
    };

    // Separate campaigns by status
    const missingUtm = warnings.filter(w => w.warning_type === 'no_utm');
    const waitingForOrders = warnings.filter(w => w.warning_type === 'no_attribution');
    const lowConfidence = warnings.filter(w => w.warning_type === 'low_confidence');
    const configured = waitingForOrders.length; // These have UTM configured

    if (loading) {
        return (
            <div className="flex justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-neutral-400" />
            </div>
        );
    }

    return (
        <div className="space-y-8">
            {/* Header */}
            <div>
                <h2 className="text-lg font-semibold text-neutral-900">Attribution Setup</h2>
                <p className="text-sm text-neutral-500 mt-1">
                    Configure UTM parameters on your ads to track which campaigns drive conversions.
                    This is optional but enhances your analytics with verified attribution data.
                </p>
            </div>

            {/* Status Overview */}
            {!status?.has_shopify ? (
                <div className="p-4 rounded-xl border border-neutral-200 bg-neutral-50">
                    <div className="flex items-start gap-3">
                        <AlertTriangle className="w-5 h-5 text-neutral-400 mt-0.5" />
                        <div>
                            <p className="font-medium text-neutral-700">Shopify not connected</p>
                            <p className="text-sm text-neutral-500 mt-1">
                                Connect your Shopify store in the Connections tab to enable order attribution.
                                Without Shopify, we can't match orders to your ad campaigns.
                            </p>
                        </div>
                    </div>
                </div>
            ) : (
                <div className="grid grid-cols-3 gap-4">
                    <div className="p-4 rounded-xl border border-green-200 bg-green-50">
                        <div className="text-2xl font-bold text-green-700">{configured}</div>
                        <div className="text-sm text-green-600">UTM Configured</div>
                    </div>
                    <div className="p-4 rounded-xl border border-amber-200 bg-amber-50">
                        <div className="text-2xl font-bold text-amber-700">{missingUtm.length}</div>
                        <div className="text-sm text-amber-600">Missing UTMs</div>
                    </div>
                    <div className="p-4 rounded-xl border border-orange-200 bg-orange-50">
                        <div className="text-2xl font-bold text-orange-700">{lowConfidence.length}</div>
                        <div className="text-sm text-orange-600">Low Confidence</div>
                    </div>
                </div>
            )}

            {/* UTM Setup Guide */}
            <UTMSetupGuide />

            {/* Campaign Status List */}
            {status?.has_shopify && warnings.length > 0 && (
                <div className="space-y-4">
                    <div className="flex items-center justify-between">
                        <h3 className="text-md font-medium text-neutral-900">Campaign Status</h3>
                        <button
                            onClick={handleRefresh}
                            disabled={refreshing}
                            className="flex items-center gap-2 text-sm text-neutral-500 hover:text-neutral-700"
                        >
                            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
                            Refresh
                        </button>
                    </div>

                    {error && (
                        <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
                            {error}
                        </div>
                    )}

                    {/* Missing UTMs - Action Required */}
                    {missingUtm.length > 0 && (
                        <div className="space-y-3">
                            <h4 className="text-sm font-medium text-amber-700">Action Required</h4>
                            {missingUtm.map((warning) => (
                                <CampaignStatusCard key={warning.campaign_id} warning={warning} />
                            ))}
                        </div>
                    )}

                    {/* Waiting for Orders - Configured */}
                    {waitingForOrders.length > 0 && (
                        <div className="space-y-3">
                            <h4 className="text-sm font-medium text-blue-700">Configured - Waiting for Orders</h4>
                            {waitingForOrders.map((warning) => (
                                <CampaignStatusCard key={warning.campaign_id} warning={warning} />
                            ))}
                        </div>
                    )}

                    {/* Low Confidence */}
                    {lowConfidence.length > 0 && (
                        <div className="space-y-3">
                            <h4 className="text-sm font-medium text-orange-700">Low Confidence Attribution</h4>
                            {lowConfidence.map((warning) => (
                                <CampaignStatusCard key={warning.campaign_id} warning={warning} />
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* All Good State */}
            {status?.has_shopify && warnings.length === 0 && (
                <div className="p-6 rounded-xl border border-green-200 bg-green-50 text-center">
                    <CheckCircle className="w-8 h-8 text-green-500 mx-auto mb-2" />
                    <p className="font-medium text-green-700">All campaigns are properly configured!</p>
                    <p className="text-sm text-green-600 mt-1">Your attribution tracking is set up correctly.</p>
                </div>
            )}
        </div>
    );
}
