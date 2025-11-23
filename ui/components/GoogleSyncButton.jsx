'use client'

import { useState, useEffect, useRef } from 'react';
import { RefreshCw, CheckCircle2, AlertCircle, Loader2, Clock } from 'lucide-react';
import { enqueueSyncJob, getSyncStatus } from '@/lib/api';

/**
 * Google Ads Sync Button Component
 * 
 * WHAT: Button that triggers Google Ads data sync via async job queue
 * WHY: Non-blocking sync with real-time status polling and progress feedback
 * WHERE USED: Settings page
 * 
 * Features:
 * - Enqueues async job instead of blocking HTTP sync
 * - Polls for completion status every 2 seconds
 * - Shows elapsed time during sync
 * - Prevents duplicate clicks while syncing
 * - Auto-detects completion and shows results
 * - Detects if new data was actually synced
 * 
 * REFERENCES:
 * - docs/living-docs/GOOGLE_INTEGRATION_STATUS.MD
 * - docs/living-docs/REALTIME_SYNC_STATUS.md
 */
export default function GoogleSyncButton({ workspaceId, connectionId, onSyncComplete = null }) {
  const [syncing, setSyncing] = useState(false);
  const [status, setStatus] = useState(null); // 'success' | 'error' | null
  const [message, setMessage] = useState('');
  const [elapsed, setElapsed] = useState(0);
  const [stats, setStats] = useState(null);
  
  const pollingIntervalRef = useRef(null);
  const elapsedIntervalRef = useRef(null);
  const initialStatsRef = useRef(null);

  // Cleanup intervals on unmount
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) clearTimeout(pollingIntervalRef.current);
      if (elapsedIntervalRef.current) clearInterval(elapsedIntervalRef.current);
    };
  }, []);

  const handleSync = async () => {
    if (syncing) return;
    
    setSyncing(true);
    setStatus(null);
    setMessage('Enqueueing sync job...');
    setElapsed(0);
    setStats(null);

    try {
      // Get initial stats before sync
      const initialStatus = await getSyncStatus({ connectionId });
      initialStatsRef.current = {
        attempts: initialStatus.total_syncs_attempted,
        changes: initialStatus.total_syncs_with_changes
      };

      // Enqueue job
      const result = await enqueueSyncJob({ connectionId });
      setMessage(`Job queued • Processing...`);

      // Start elapsed time counter
      const startTime = Date.now();
      elapsedIntervalRef.current = setInterval(() => {
        setElapsed(Math.floor((Date.now() - startTime) / 1000));
      }, 1000);

      // Poll for completion
      let attempts = 0;
      const maxAttempts = 60; // 2 minutes max

      const pollStatus = async () => {
        try {
          const currentStatus = await getSyncStatus({ connectionId });
          
          // Still processing
          if (currentStatus.sync_status === 'syncing' || currentStatus.sync_status === 'queued') {
            attempts++;
            if (attempts < maxAttempts) {
              pollingIntervalRef.current = setTimeout(pollStatus, 2000); // Check again in 2s
            } else {
              throw new Error('Sync is taking longer than expected. Check back in a few minutes.');
            }
          }
          // Completed successfully
          else if (currentStatus.sync_status === 'idle') {
            // Clear intervals
            if (elapsedIntervalRef.current) clearInterval(elapsedIntervalRef.current);
            if (pollingIntervalRef.current) clearTimeout(pollingIntervalRef.current);
            
            // Calculate changes
            const newChanges = currentStatus.total_syncs_with_changes - (initialStatsRef.current?.changes || 0);
            const wasDataChange = newChanges > 0;
            
            setStatus('success');
            setMessage(wasDataChange 
              ? `✓ Sync complete! New data synced.`
              : `✓ Sync complete! No changes detected (data is up to date).`
            );
            setStats({
              attempts: currentStatus.total_syncs_attempted,
              changes: currentStatus.total_syncs_with_changes,
              lastCompleted: currentStatus.last_sync_completed_at,
              hadChanges: wasDataChange
            });
            setSyncing(false);
            
            if (onSyncComplete) onSyncComplete();
          }
          // Error state
          else if (currentStatus.sync_status === 'error') {
            if (elapsedIntervalRef.current) clearInterval(elapsedIntervalRef.current);
            if (pollingIntervalRef.current) clearTimeout(pollingIntervalRef.current);
            
            throw new Error(currentStatus.last_sync_error || 'Sync failed');
          }
        } catch (pollError) {
          if (elapsedIntervalRef.current) clearInterval(elapsedIntervalRef.current);
          if (pollingIntervalRef.current) clearTimeout(pollingIntervalRef.current);
          
          setStatus('error');
          setMessage(pollError.message || 'Failed to check sync status');
          setSyncing(false);
        }
      };

      // Start polling after 2 seconds
      pollingIntervalRef.current = setTimeout(pollStatus, 2000);

    } catch (error) {
      if (elapsedIntervalRef.current) clearInterval(elapsedIntervalRef.current);
      if (pollingIntervalRef.current) clearTimeout(pollingIntervalRef.current);
      
      setStatus('error');
      setMessage(error.message || 'Failed to enqueue sync job');
      setSyncing(false);
    }
  };

  return (
    <div className="space-y-2">
      <button
        onClick={handleSync}
        disabled={syncing}
        className={`
          inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium
          transition-all disabled:opacity-50 disabled:cursor-not-allowed
          ${syncing 
            ? 'bg-blue-50 text-blue-700 border border-blue-200 cursor-wait' 
            : status === 'success'
            ? 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200'
            : status === 'error'
            ? 'bg-red-50 text-red-700 hover:bg-red-100 border border-red-200'
            : 'bg-cyan-50 text-cyan-700 hover:bg-cyan-100 border border-cyan-200'
          }
        `}
      >
        {syncing ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Syncing... {elapsed}s</span>
          </>
        ) : status === 'success' ? (
          <>
            <CheckCircle2 className="w-4 h-4" />
            <span>Sync Complete</span>
          </>
        ) : status === 'error' ? (
          <>
            <AlertCircle className="w-4 h-4" />
            <span>Sync Failed</span>
          </>
        ) : (
          <>
            <RefreshCw className="w-4 h-4" />
            <span>Sync Google Ads</span>
          </>
        )}
      </button>

      {message && (
        <p className={`text-xs ${status === 'error' ? 'text-red-600' : status === 'success' ? 'text-emerald-600' : 'text-blue-600'}`}>
          {message}
        </p>
      )}

      {stats && status === 'success' && (
        <div className="text-xs text-neutral-500 space-y-1 mt-2 p-2 bg-neutral-50 rounded border border-neutral-200">
          <div className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            <span>Completed in {elapsed}s</span>
          </div>
          <div>
            Total attempts: {stats.attempts} • Changes detected: {stats.changes}
          </div>
          {stats.hadChanges && (
            <div className="text-emerald-600 font-medium">
              ✨ New data available!
            </div>
          )}
        </div>
      )}
    </div>
  );
}
