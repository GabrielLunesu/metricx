/**
 * Pixel Event WebSocket Stream Hook.
 *
 * WHAT:
 *   React hook for real-time pixel events via WebSocket.
 *   Receives page views, product views, add-to-carts, checkouts, and purchases
 *   as they happen — no polling required.
 *
 * WHY:
 *   The attribution page "Live Feed" panel needs instant visibility into
 *   customer activity. WebSocket streaming eliminates polling latency and
 *   gives merchants a true real-time view.
 *
 * USAGE:
 *   const { events, isConnected, connectionState } = usePixelStream(workspaceId);
 *
 * PROTOCOL:
 *   1. Connects to ws(s)://host/api/v1/pixel-events/stream?token=<clerk_jwt>
 *   2. Receives "connected" message on success
 *   3. Receives "initial_batch" with last 30 events
 *   4. Receives "pixel_event" messages in real-time
 *   5. Sends "ping" every 30s; expects "pong" back
 *   6. Auto-reconnects on disconnect (max 5 retries, 3s delay)
 *
 * REFERENCES:
 *   - ui/hooks/useAgentStream.js (pattern source)
 *   - backend/app/routers/pixel_events.py (WebSocket endpoint)
 *   - backend/app/services/pixel_websocket_manager.py (connection manager)
 */

import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Get the WebSocket URL for the backend.
 *
 * WHAT: Constructs WebSocket URL that connects directly to the backend
 * WHY: Next.js rewrites (next.config.mjs) only handle HTTP, not WebSocket
 *      upgrades. WebSocket must connect directly to the backend origin.
 *
 * ENVIRONMENTS:
 *   - Local dev:  ws://localhost:8000/v1
 *   - Production: wss://api.metricx.ai/v1  (backend on api.metricx.ai)
 *
 * @returns {string} WebSocket base URL
 */
function getWebSocketUrl() {
    if (typeof window === 'undefined') return '';

    // NEXT_PUBLIC_API_BASE points to the real backend (e.g. "https://api.metricx.ai")
    const apiBase = process.env.NEXT_PUBLIC_API_BASE;
    if (apiBase) {
        const wsBase = apiBase.replace(/^http/, 'ws');
        return `${wsBase}/v1`;
    }

    // Local dev — connect directly to backend on port 8000
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        return `ws://${window.location.hostname}:8000/v1`;
    }

    // Production fallback — derive api subdomain from current host
    // e.g. metricx.ai → wss://api.metricx.ai/v1
    return `wss://api.${window.location.host}/v1`;
}

/** Connection state enum. */
export const ConnectionState = {
    CONNECTING: 'connecting',
    CONNECTED: 'connected',
    DISCONNECTED: 'disconnected',
    RECONNECTING: 'reconnecting',
    ERROR: 'error',
};

/**
 * Hook for streaming pixel events via WebSocket.
 *
 * @param {string|null} workspaceId - Workspace ID to stream events for
 * @param {Object} options - Configuration options
 * @param {boolean} options.enabled - Whether to connect (default: true)
 * @param {number} options.maxEvents - Max events to buffer (default: 100)
 * @param {number} options.reconnectDelay - Delay between reconnect attempts in ms (default: 3000)
 * @param {number} options.maxReconnects - Max reconnection attempts (default: 5)
 *
 * @returns {Object} Hook state
 * @returns {Array} returns.events - Array of pixel events (newest first)
 * @returns {boolean} returns.isConnected - Whether WebSocket is connected
 * @returns {string} returns.connectionState - Current connection state
 */
export default function usePixelStream(workspaceId, options = {}) {
    const {
        enabled = true,
        maxEvents = 100,
        reconnectDelay = 3000,
        maxReconnects = 5,
    } = options;

    // State
    const [events, setEvents] = useState([]);
    const [connectionState, setConnectionState] = useState(ConnectionState.DISCONNECTED);

    // Refs (persist across renders without triggering re-render)
    const wsRef = useRef(null);
    const reconnectCountRef = useRef(0);
    const reconnectTimeoutRef = useRef(null);
    const pingIntervalRef = useRef(null);

    /**
     * Get Clerk session token for WebSocket auth.
     *
     * WHAT: Waits for Clerk to be ready, then gets a fresh session token
     * WHY: WebSocket auth passes token as query param — needs to be fresh
     *
     * @returns {Promise<string|null>} JWT token or null
     */
    const getToken = useCallback(async () => {
        if (typeof window === 'undefined') return null;

        // Wait for Clerk to be ready (max 5s)
        let attempts = 0;
        while (!window.Clerk?.session && attempts < 50) {
            await new Promise(resolve => setTimeout(resolve, 100));
            attempts++;
        }

        if (window.Clerk?.session) {
            try {
                return await window.Clerk.session.getToken();
            } catch (e) {
                console.error('[usePixelStream] Failed to get Clerk token:', e);
                return null;
            }
        }
        return null;
    }, []);

    /**
     * Connect to the pixel event WebSocket.
     */
    const connect = useCallback(async () => {
        if (!enabled || !workspaceId) return;

        const token = await getToken();
        if (!token) {
            console.warn('[usePixelStream] No auth token available');
            setConnectionState(ConnectionState.ERROR);
            return;
        }

        // Clean up existing connection
        if (wsRef.current) {
            wsRef.current.close();
        }

        setConnectionState(ConnectionState.CONNECTING);

        const baseUrl = getWebSocketUrl();
        const wsUrl = `${baseUrl}/pixel-events/stream?token=${encodeURIComponent(token)}`;

        try {
            const ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                console.log('[usePixelStream] Connected');
                setConnectionState(ConnectionState.CONNECTED);
                reconnectCountRef.current = 0;

                // Start ping interval (every 30 seconds)
                pingIntervalRef.current = setInterval(() => {
                    if (ws.readyState === WebSocket.OPEN) {
                        ws.send(JSON.stringify({ type: 'ping' }));
                    }
                }, 30000);
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);

                    // Handle different message types
                    if (data.type === 'pong' || data.type === 'connected') {
                        return;
                    }

                    if (data.type === 'initial_batch') {
                        // Replace events with initial batch (already newest-first from server)
                        setEvents(data.events || []);
                        return;
                    }

                    if (data.type === 'pixel_event') {
                        // Prepend new event, cap at maxEvents
                        setEvents(prev => {
                            const updated = [data, ...prev];
                            return updated.slice(0, maxEvents);
                        });
                    }
                } catch (e) {
                    console.error('[usePixelStream] Failed to parse message:', e);
                }
            };

            ws.onerror = (event) => {
                console.error('[usePixelStream] WebSocket error:', event);
            };

            ws.onclose = (event) => {
                console.log('[usePixelStream] Disconnected:', event.code, event.reason);

                // Clear ping interval
                if (pingIntervalRef.current) {
                    clearInterval(pingIntervalRef.current);
                    pingIntervalRef.current = null;
                }

                // Don't reconnect if closed normally or max retries reached
                if (event.code === 1000 || reconnectCountRef.current >= maxReconnects) {
                    setConnectionState(ConnectionState.DISCONNECTED);
                    return;
                }

                // Attempt reconnection
                setConnectionState(ConnectionState.RECONNECTING);
                reconnectCountRef.current += 1;

                console.log(
                    `[usePixelStream] Reconnecting in ${reconnectDelay}ms ` +
                    `(attempt ${reconnectCountRef.current}/${maxReconnects})`
                );

                reconnectTimeoutRef.current = setTimeout(() => {
                    connect();
                }, reconnectDelay);
            };

            wsRef.current = ws;
        } catch (e) {
            console.error('[usePixelStream] Failed to create WebSocket:', e);
            setConnectionState(ConnectionState.ERROR);
        }
    }, [enabled, workspaceId, maxEvents, reconnectDelay, maxReconnects, getToken]);

    /**
     * Disconnect from WebSocket.
     */
    const disconnect = useCallback(() => {
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
        }
        if (pingIntervalRef.current) {
            clearInterval(pingIntervalRef.current);
            pingIntervalRef.current = null;
        }
        if (wsRef.current) {
            wsRef.current.close(1000, 'Client disconnected');
            wsRef.current = null;
        }
        setConnectionState(ConnectionState.DISCONNECTED);
    }, []);

    // Connect when workspaceId is available, disconnect on unmount
    useEffect(() => {
        if (enabled && workspaceId) {
            connect();
        }
        return () => {
            disconnect();
        };
    }, [enabled, workspaceId, connect, disconnect]);

    return {
        events,
        isConnected: connectionState === ConnectionState.CONNECTED,
        connectionState,
    };
}
