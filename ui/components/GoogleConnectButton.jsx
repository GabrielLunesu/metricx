'use client';

import { useState, useEffect } from 'react';
import { ExternalLink } from 'lucide-react';
import GoogleAccountSelectionModal from './GoogleAccountSelectionModal';
import { getApiBase } from '../lib/config';

/**
 * GoogleConnectButton Component
 * 
 * WHAT: Button that initiates Google OAuth flow
 * WHY: Allow users to connect their Google Ads accounts via OAuth
 * WHERE USED: Settings page
 * 
 * Features:
 * - Redirects to backend OAuth authorize endpoint
 * - Handles success/error query params on return
 * - Shows connection status messages
 */
export default function GoogleConnectButton({ onConnectionComplete }) {
  const [message, setMessage] = useState(null);
  const [messageType, setMessageType] = useState(null); // 'success' or 'error'
  const [showSelectionModal, setShowSelectionModal] = useState(false);
  const [selectionSessionId, setSelectionSessionId] = useState(null);

  useEffect(() => {
    // Check for OAuth callback parameters
    const params = new URLSearchParams(window.location.search);
    const oauthStatus = params.get('google_oauth');
    const errorMessage = params.get('message');
    const connectionId = params.get('connection_id');
    const connectionsCount = params.get('connections_count');
    const sessionId = params.get('session_id');

    if (oauthStatus === 'select' && sessionId) {
      // Show account selection modal
      setSelectionSessionId(sessionId);
      setShowSelectionModal(true);

      // Clear URL parameters
      window.history.replaceState({}, '', window.location.pathname);
    } else if (oauthStatus === 'success') {
      if (connectionsCount && parseInt(connectionsCount) > 1) {
        setMessage(`Successfully connected ${connectionsCount} Google Ads accounts!`);
      } else {
        setMessage('Google Ads account connected successfully!');
      }
      setMessageType('success');

      // Clear URL parameters
      window.history.replaceState({}, '', window.location.pathname);

      // Notify parent to refresh connections
      if (onConnectionComplete) {
        onConnectionComplete();
      }

      // Clear message after 5 seconds
      setTimeout(() => {
        setMessage(null);
        setMessageType(null);
      }, 5000);
    } else if (oauthStatus === 'error') {
      const errorMessages = {
        'missing_code': 'Authorization failed. No authorization code received.',
        'token_exchange_failed': 'Failed to exchange authorization code for tokens.',
        'missing_tokens': 'OAuth tokens were not received from Google.',
        'missing_state': 'OAuth state parameter missing. Please try again.',
        'invalid_workspace': 'Invalid workspace. Please try again.',
        'oauth_not_configured': 'Google OAuth is not configured on the server.',
        'developer_token_missing': 'Google Ads developer token is not configured.',
        'sdk_not_installed': 'Google Ads SDK is not installed on the server.',
        'no_customers': 'No Google Ads accounts found for this Google account.',
        'no_ad_accounts': 'No ad accounts available. Only MCC accounts were found. Please add ad accounts under your MCC first.',
        'customer_fetch_failed': 'Failed to fetch Google Ads account details.',
        'connection_save_failed': 'Failed to save connection. Please try again.',
      };

      setMessage(errorMessages[errorMessage] || `Connection failed: ${errorMessage || 'Unknown error'}`);
      setMessageType('error');

      // Clear URL parameters
      window.history.replaceState({}, '', window.location.pathname);

      // Clear error message after 10 seconds
      setTimeout(() => {
        setMessage(null);
        setMessageType(null);
      }, 10000);
    }
  }, [onConnectionComplete]);

  const handleConnect = () => {
    // Redirect to backend OAuth authorize endpoint
    const baseUrl = getApiBase();
    window.location.href = `${baseUrl}/auth/google/authorize`;
  };

  return (
    <div>
      {message && (
        <div className={`mb-4 p-3 rounded-lg text-sm ${messageType === 'success'
            ? 'bg-green-50 text-green-800 border border-green-200'
            : 'bg-red-50 text-red-800 border border-red-200'
          }`}>
          {message}
        </div>
      )}

      <button
        onClick={handleConnect}
        className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors flex items-center gap-2"
      >
        <ExternalLink className="w-4 h-4" />
        Connect Google Ads
      </button>

      <p className="mt-2 text-xs text-neutral-500">
        You'll be redirected to Google to authorize access to your Google Ads account.
      </p>

      {/* Account Selection Modal */}
      {showSelectionModal && (
        <GoogleAccountSelectionModal
          open={showSelectionModal}
          onClose={() => {
            setShowSelectionModal(false);
            setSelectionSessionId(null);
          }}
          sessionId={selectionSessionId}
          onSuccess={(data) => {
            setMessage(`Successfully connected ${data.total} Google Ads account${data.total !== 1 ? 's' : ''} !`);
            setMessageType('success');
            setShowSelectionModal(false);
            setSelectionSessionId(null);

            // Notify parent to refresh connections
            if (onConnectionComplete) {
              onConnectionComplete();
            }

            // Clear message after 5 seconds
            setTimeout(() => {
              setMessage(null);
              setMessageType(null);
            }, 5000);
          }}
        />
      )}
    </div>
  );
}


