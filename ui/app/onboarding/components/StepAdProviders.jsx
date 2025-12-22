/**
 * Step 4: Connect Ad Accounts
 * ===========================
 *
 * WHAT: Let users connect their Meta and Google ad accounts via OAuth.
 * WHY: Core functionality - users need ad accounts to use the platform.
 *
 * NOTE: Uses actual OAuth flow - redirects to provider and back.
 *       Shows sync timing info after successful connection.
 */

'use client';

import { useState, useEffect } from 'react';
import { ArrowLeft, Loader2, Check, Rocket, ExternalLink, Clock, Info } from 'lucide-react';
import { getApiBase } from '@/lib/config';
import MetaAccountSelectionModal from '@/components/MetaAccountSelectionModal';
import GoogleAccountSelectionModal from '@/components/GoogleAccountSelectionModal';

export default function StepAdProviders({
  formData,
  updateFormData,
  onComplete,
  onBack,
  onSkip,
  submitting,
}) {
  const [connections, setConnections] = useState({ meta: [], google: [] });
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState(null);
  const [messageType, setMessageType] = useState(null);

  // Modal states for account selection
  const [showMetaModal, setShowMetaModal] = useState(false);
  const [showGoogleModal, setShowGoogleModal] = useState(false);
  const [metaSessionId, setMetaSessionId] = useState(null);
  const [googleSessionId, setGoogleSessionId] = useState(null);

  // Fetch existing connections on mount
  useEffect(() => {
    fetchConnections();
    handleOAuthCallback();
  }, []);

  const fetchConnections = async () => {
    try {
      const res = await fetch('/api/connections', { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        // API returns { connections: [...], total: N }
        const allConnections = data.connections || [];
        const meta = allConnections.filter((c) => c.provider === 'meta');
        const google = allConnections.filter((c) => c.provider === 'google');
        setConnections({ meta, google });
      }
    } catch (err) {
      console.error('Failed to fetch connections:', err);
    } finally {
      setLoading(false);
    }
  };

  // Handle OAuth callback parameters
  const handleOAuthCallback = () => {
    const params = new URLSearchParams(window.location.search);

    // Meta OAuth callback
    const metaStatus = params.get('meta_oauth');
    const metaSessionId = params.get('session_id');
    if (metaStatus === 'select' && metaSessionId) {
      setMetaSessionId(metaSessionId);
      setShowMetaModal(true);
      window.history.replaceState({}, '', window.location.pathname);
    } else if (metaStatus === 'success') {
      setMessage('Meta ad account connected successfully!');
      setMessageType('success');
      window.history.replaceState({}, '', window.location.pathname);
      fetchConnections();
    } else if (metaStatus === 'error') {
      setMessage(params.get('message') || 'Failed to connect Meta');
      setMessageType('error');
      window.history.replaceState({}, '', window.location.pathname);
    }

    // Google OAuth callback
    const googleStatus = params.get('google_oauth');
    const googleSessionId = params.get('session_id');
    if (googleStatus === 'select' && googleSessionId) {
      setGoogleSessionId(googleSessionId);
      setShowGoogleModal(true);
      window.history.replaceState({}, '', window.location.pathname);
    } else if (googleStatus === 'success') {
      setMessage('Google Ads account connected successfully!');
      setMessageType('success');
      window.history.replaceState({}, '', window.location.pathname);
      fetchConnections();
    } else if (googleStatus === 'error') {
      setMessage(params.get('message') || 'Failed to connect Google Ads');
      setMessageType('error');
      window.history.replaceState({}, '', window.location.pathname);
    }
  };

  const handleConnectMeta = () => {
    const baseUrl = getApiBase();
    // Add return URL so OAuth redirects back to onboarding
    window.location.href = `${baseUrl}/auth/meta/authorize?return_url=${encodeURIComponent(window.location.pathname)}`;
  };

  const handleConnectGoogle = () => {
    const baseUrl = getApiBase();
    window.location.href = `${baseUrl}/auth/google/authorize?return_url=${encodeURIComponent(window.location.pathname)}`;
  };

  const hasAnyConnection = connections.meta.length > 0 || connections.google.length > 0;

  return (
    <div>
      {/* Header */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-indigo-100 mb-4">
          <Rocket className="w-6 h-6 text-indigo-600" />
        </div>
        <h1 className="text-2xl font-semibold text-slate-900">
          Connect your ad accounts
        </h1>
        <p className="mt-2 text-slate-500">
          Start tracking your advertising performance
        </p>
      </div>

      {/* Status message */}
      {message && (
        <div
          className={`mb-6 p-4 rounded-xl flex items-start gap-3 ${
            messageType === 'success'
              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
              : 'bg-red-50 text-red-700 border border-red-200'
          }`}
        >
          {messageType === 'success' ? (
            <Check className="w-5 h-5 flex-shrink-0 mt-0.5" />
          ) : (
            <Info className="w-5 h-5 flex-shrink-0 mt-0.5" />
          )}
          <div>
            <p className="font-medium">{message}</p>
            {messageType === 'success' && (
              <p className="text-sm mt-1 opacity-80">
                We'll start syncing your data right away.
              </p>
            )}
          </div>
        </div>
      )}

      {/* Provider cards */}
      <div className="space-y-4 mb-6">
        {/* Meta Ads */}
        <div className="p-4 rounded-xl border border-slate-200 bg-white">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-blue-100 flex items-center justify-center text-blue-600">
              <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2.04c-5.5 0-10 4.49-10 10.02 0 5 3.66 9.15 8.44 9.9v-7H7.9v-2.9h2.54V9.85c0-2.52 1.49-3.92 3.78-3.92 1.09 0 2.24.2 2.24.2v2.46h-1.26c-1.24 0-1.63.78-1.63 1.57v1.88h2.78l-.45 2.9h-2.33v7a10 10 0 008.44-9.9c0-5.53-4.5-10.02-10-10.02z" />
              </svg>
            </div>
            <div className="flex-1">
              <div className="font-medium text-slate-900">Meta Ads</div>
              <div className="text-sm text-slate-500">Facebook & Instagram Ads</div>
            </div>
            {connections.meta.length > 0 ? (
              <div className="flex items-center gap-2 text-emerald-600">
                <Check className="w-5 h-5" />
                <span className="text-sm font-medium">
                  {connections.meta.length} connected
                </span>
              </div>
            ) : (
              <button
                onClick={handleConnectMeta}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors flex items-center gap-2"
              >
                <ExternalLink className="w-4 h-4" />
                Connect
              </button>
            )}
          </div>
        </div>

        {/* Google Ads */}
        <div className="p-4 rounded-xl border border-slate-200 bg-white">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-slate-100 flex items-center justify-center">
              <svg className="w-6 h-6" viewBox="0 0 24 24">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
              </svg>
            </div>
            <div className="flex-1">
              <div className="font-medium text-slate-900">Google Ads</div>
              <div className="text-sm text-slate-500">Search, Display, YouTube</div>
            </div>
            {connections.google.length > 0 ? (
              <div className="flex items-center gap-2 text-emerald-600">
                <Check className="w-5 h-5" />
                <span className="text-sm font-medium">
                  {connections.google.length} connected
                </span>
              </div>
            ) : (
              <button
                onClick={handleConnectGoogle}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors flex items-center gap-2"
              >
                <ExternalLink className="w-4 h-4" />
                Connect
              </button>
            )}
          </div>
        </div>

        {/* TikTok (Coming Soon) */}
        <div className="p-4 rounded-xl border border-slate-100 bg-slate-50 opacity-60">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-slate-200 flex items-center justify-center text-slate-400">
              <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
                <path d="M19.59 6.69a4.83 4.83 0 01-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 01-5.2 1.74 2.89 2.89 0 012.31-4.64 2.93 2.93 0 01.88.13V9.4a6.84 6.84 0 00-1-.05A6.33 6.33 0 005 20.1a6.34 6.34 0 0010.86-4.43v-7a8.16 8.16 0 004.77 1.52v-3.4a4.85 4.85 0 01-1-.1z" />
              </svg>
            </div>
            <div className="flex-1">
              <div className="font-medium text-slate-500">TikTok Ads</div>
              <div className="text-sm text-slate-400">Coming soon</div>
            </div>
          </div>
        </div>
      </div>

      {/* Sync timing info - show when at least one account is connected */}
      {hasAnyConnection && (
        <div className="mb-6 p-4 rounded-xl bg-blue-50 border border-blue-100">
          <div className="flex items-start gap-3">
            <Clock className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-blue-800">
              <p className="font-medium mb-1">Data sync schedule</p>
              <ul className="space-y-1 text-blue-700">
                <li>New data syncs every 15 minutes</li>
                <li>Historical data will have daily data points (not hourly)</li>
                <li>Give it a few minutes to complete the initial sync</li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Settings note */}
      <p className="text-sm text-slate-500 text-center mb-6">
        You can add, change, or remove ad accounts anytime in Settings.
      </p>

      {/* Actions */}
      <div className="flex gap-3">
        <button
          type="button"
          onClick={onBack}
          disabled={submitting}
          className="px-4 py-3 rounded-xl border border-slate-200 text-slate-600 font-medium
            hover:bg-slate-50 transition-colors flex items-center gap-2
            disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <ArrowLeft className="w-4 h-4" />
          Back
        </button>

        <button
          type="button"
          onClick={onSkip}
          disabled={submitting}
          className="flex-1 px-4 py-3 rounded-xl border border-slate-200 text-slate-600 font-medium
            hover:bg-slate-50 transition-colors
            disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {hasAnyConnection ? 'Skip for now' : 'Skip'}
        </button>

        <button
          type="button"
          onClick={onComplete}
          disabled={submitting}
          className="flex-1 px-4 py-3 rounded-xl bg-indigo-600 text-white font-medium
            hover:bg-indigo-700 transition-colors flex items-center justify-center gap-2
            disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {submitting ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Finishing...
            </>
          ) : (
            <>
              {hasAnyConnection ? 'Go to Dashboard' : 'Complete Setup'}
              <Rocket className="w-4 h-4" />
            </>
          )}
        </button>
      </div>

      {/* Meta Account Selection Modal */}
      {showMetaModal && metaSessionId && (
        <MetaAccountSelectionModal
          open={showMetaModal}
          onClose={() => {
            setShowMetaModal(false);
            setMetaSessionId(null);
          }}
          sessionId={metaSessionId}
          existingConnections={connections.meta}
          onSuccess={(data) => {
            setMessage(`Successfully connected ${data.total} Meta ad account${data.total !== 1 ? 's' : ''}!`);
            setMessageType('success');
            setShowMetaModal(false);
            setMetaSessionId(null);
            fetchConnections();
          }}
        />
      )}

      {/* Google Account Selection Modal */}
      {showGoogleModal && googleSessionId && (
        <GoogleAccountSelectionModal
          open={showGoogleModal}
          onClose={() => {
            setShowGoogleModal(false);
            setGoogleSessionId(null);
          }}
          sessionId={googleSessionId}
          onSuccess={(data) => {
            setMessage(`Successfully connected ${data.total} Google Ads account${data.total !== 1 ? 's' : ''}!`);
            setMessageType('success');
            setShowGoogleModal(false);
            setGoogleSessionId(null);
            fetchConnections();
          }}
        />
      )}
    </div>
  );
}
