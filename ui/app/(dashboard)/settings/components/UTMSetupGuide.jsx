'use client';

/**
 * UTMSetupGuide component for Settings page.
 *
 * WHAT: Platform-specific UTM setup instructions with copy-paste templates
 * WHY: Users need clear guidance on how to set up UTM parameters for proper attribution
 *
 * REFERENCES:
 * - docs/ATTRIBUTION_UX_COMPREHENSIVE_PLAN.md (UTM Setup Guide section)
 */

import { useState } from 'react';
import { Copy, Check, ExternalLink, Lightbulb, ChevronDown, ChevronUp } from 'lucide-react';
import { toast } from 'sonner';

// Platform-specific UTM templates
const PLATFORM_TEMPLATES = {
    meta: {
        name: 'Meta Ads',
        icon: '📘',
        description: 'Facebook & Instagram Ads',
        template: `?utm_source=facebook&utm_medium=paid&utm_campaign={{campaign.name}}&utm_content={{adset.name}}&utm_term={{ad.name}}`,
        steps: [
            'Go to Meta Ads Manager',
            'Select your Campaign → Ad Set → Ad',
            'In the ad editing view, find "Website URL" or "Destination"',
            'Add the UTM parameters to your URL (after the base URL)',
            'Use the dynamic parameters shown above - Meta will auto-fill them'
        ],
        tips: [
            'Meta automatically adds fbclid to URLs, but UTMs give you campaign-level detail',
            'Use {{campaign.name}} syntax for dynamic values that Meta fills in automatically',
            'Test your URLs in Preview mode before publishing'
        ],
        docsUrl: 'https://www.facebook.com/business/help/1016122818401732'
    },
    google: {
        name: 'Google Ads',
        icon: '🔍',
        description: 'Search, Display, Shopping & YouTube',
        template: `{lpurl}?utm_source=google&utm_medium=cpc&utm_campaign={campaignid}&utm_content={adgroupid}&utm_term={keyword}`,
        altTemplate: `?utm_source=google&utm_medium=cpc&utm_campaign={_campaign}&utm_content={_adgroup}`,
        steps: [
            'Go to Google Ads → Campaign → Ad Group → Ad',
            'Click "Edit" on your ad',
            'In "Final URL suffix" or "Tracking template", add the UTM parameters',
            'Use {lpurl} as the base URL placeholder in tracking templates',
            'Google will automatically append the parameters to your landing page URL'
        ],
        tips: [
            'If you enable Auto-tagging (gclid), Metricx can resolve clicks to exact campaigns automatically',
            'gclid + UTMs together gives you the best attribution accuracy',
            'Use ValueTrack parameters like {campaignid} for dynamic values',
            'For custom campaign names, use {_campaign} custom parameters'
        ],
        docsUrl: 'https://support.google.com/google-ads/answer/6305348'
    },
    manual: {
        name: 'Manual / Other',
        icon: '✏️',
        description: 'Any platform or custom setup',
        template: `?utm_source=YOUR_SOURCE&utm_medium=YOUR_MEDIUM&utm_campaign=YOUR_CAMPAIGN&utm_content=YOUR_AD`,
        steps: [
            'Replace YOUR_SOURCE with the platform name (e.g., linkedin, email, affiliate)',
            'Replace YOUR_MEDIUM with the marketing medium (e.g., paid, cpc, social, email)',
            'Replace YOUR_CAMPAIGN with your campaign name (use lowercase, no spaces)',
            'Replace YOUR_AD with your ad or content identifier',
            'Append the complete UTM string to your destination URL'
        ],
        tips: [
            'Use consistent naming conventions across all campaigns',
            'Avoid spaces - use underscores or hyphens instead',
            'Keep source names lowercase for consistency',
            'Document your UTM conventions in a spreadsheet'
        ],
        docsUrl: null
    }
};

/**
 * Copy button with feedback
 */
function CopyButton({ text, label = 'Copy' }) {
    const [copied, setCopied] = useState(false);

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(text);
            setCopied(true);
            toast.success('Copied to clipboard!');
            setTimeout(() => setCopied(false), 2000);
        } catch (err) {
            toast.error('Failed to copy');
        }
    };

    return (
        <button
            onClick={handleCopy}
            className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-cyan-600 hover:text-cyan-700 hover:bg-cyan-50 rounded-lg transition-colors"
        >
            {copied ? (
                <>
                    <Check className="w-4 h-4" />
                    Copied!
                </>
            ) : (
                <>
                    <Copy className="w-4 h-4" />
                    {label}
                </>
            )}
        </button>
    );
}

/**
 * Collapsible section for tips
 */
function TipsSection({ tips }) {
    const [expanded, setExpanded] = useState(false);

    if (!tips || tips.length === 0) return null;

    return (
        <div className="mt-4">
            <button
                onClick={() => setExpanded(!expanded)}
                className="flex items-center gap-2 text-sm font-medium text-amber-700 hover:text-amber-800"
            >
                <Lightbulb className="w-4 h-4" />
                Pro Tips
                {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
            {expanded && (
                <ul className="mt-2 space-y-1 text-sm text-amber-600">
                    {tips.map((tip, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                            <span className="text-amber-400 mt-0.5">💡</span>
                            {tip}
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}

export default function UTMSetupGuide({ onComplete }) {
    const [activeTab, setActiveTab] = useState('meta');
    const [completedSetup, setCompletedSetup] = useState(false);

    const platform = PLATFORM_TEMPLATES[activeTab];

    const handleComplete = () => {
        setCompletedSetup(true);
        toast.success('Great! Your UTM setup is marked as complete.');
        onComplete?.();
    };

    return (
        <div className="p-6 bg-white border border-neutral-200 rounded-xl">
            {/* Header */}
            <div className="mb-6">
                <h3 className="text-lg font-semibold text-neutral-900 mb-2">
                    Attribution Setup Guide
                </h3>
                <p className="text-sm text-neutral-600">
                    To track which ads drive sales, add UTM parameters to your ad URLs.
                    Select your ad platform below for specific instructions.
                </p>
            </div>

            {/* Platform Tabs */}
            <div className="flex flex-wrap gap-2 mb-6 p-1 bg-neutral-100 rounded-lg">
                {Object.entries(PLATFORM_TEMPLATES).map(([key, p]) => (
                    <button
                        key={key}
                        onClick={() => setActiveTab(key)}
                        className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                            activeTab === key
                                ? 'bg-white text-neutral-900 shadow-sm'
                                : 'text-neutral-600 hover:text-neutral-900'
                        }`}
                    >
                        <span>{p.icon}</span>
                        {p.name}
                    </button>
                ))}
            </div>

            {/* Platform Content */}
            <div className="space-y-6">
                {/* Template */}
                <div>
                    <div className="flex items-center justify-between mb-2">
                        <h4 className="text-sm font-medium text-neutral-700">
                            UTM Template for {platform.name}
                        </h4>
                        <CopyButton text={platform.template} />
                    </div>
                    <div className="p-4 bg-neutral-900 rounded-lg overflow-x-auto">
                        <code className="text-sm text-emerald-400 whitespace-pre-wrap break-all">
                            {platform.template}
                        </code>
                    </div>
                    {platform.altTemplate && (
                        <div className="mt-3">
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-xs text-neutral-500">Alternative (custom parameters):</span>
                                <CopyButton text={platform.altTemplate} label="Copy Alt" />
                            </div>
                            <div className="p-3 bg-neutral-100 rounded-lg overflow-x-auto">
                                <code className="text-xs text-neutral-700 whitespace-pre-wrap break-all">
                                    {platform.altTemplate}
                                </code>
                            </div>
                        </div>
                    )}
                </div>

                {/* Steps */}
                <div>
                    <h4 className="text-sm font-medium text-neutral-700 mb-3">Setup Steps</h4>
                    <ol className="space-y-2">
                        {platform.steps.map((step, idx) => (
                            <li key={idx} className="flex items-start gap-3 text-sm text-neutral-600">
                                <span className="flex-shrink-0 w-6 h-6 flex items-center justify-center bg-cyan-100 text-cyan-700 rounded-full text-xs font-medium">
                                    {idx + 1}
                                </span>
                                {step}
                            </li>
                        ))}
                    </ol>
                </div>

                {/* Tips */}
                <TipsSection tips={platform.tips} />

                {/* Documentation Link */}
                {platform.docsUrl && (
                    <a
                        href={platform.docsUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-sm text-cyan-600 hover:text-cyan-700"
                    >
                        View {platform.name} Documentation
                        <ExternalLink className="w-3 h-3" />
                    </a>
                )}
            </div>

            {/* Example URL */}
            <div className="mt-6 p-4 bg-neutral-50 border border-neutral-200 rounded-lg">
                <h4 className="text-sm font-medium text-neutral-700 mb-2">Example Final URL</h4>
                <code className="text-xs text-neutral-600 break-all">
                    https://yourstore.com/products/awesome-product{platform.template}
                </code>
            </div>

            {/* Complete Button */}
            <div className="mt-6 pt-4 border-t border-neutral-200 flex items-center justify-between">
                <p className="text-sm text-neutral-500">
                    {completedSetup
                        ? '✅ Setup marked as complete'
                        : 'Click below when you\'ve set up your UTMs'}
                </p>
                <button
                    onClick={handleComplete}
                    disabled={completedSetup}
                    className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                        completedSetup
                            ? 'bg-emerald-100 text-emerald-700 cursor-default'
                            : 'bg-cyan-600 text-white hover:bg-cyan-700'
                    }`}
                >
                    {completedSetup ? 'Setup Complete' : 'I\'ve Set Up My UTMs'}
                </button>
            </div>
        </div>
    );
}
