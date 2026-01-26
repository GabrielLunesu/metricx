/**
 * Agent WebSocket Stream Hook.
 *
 * WHAT:
 *   React hook for real-time agent updates via WebSocket.
 *   Receives evaluation events, triggers, and status changes.
 *
 * WHY:
 *   Real-time updates provide better UX:
 *   - Agent detail page shows live evaluation results
 *   - Dashboard shows agent activity feed
 *   - No polling required
 *
 * USAGE:
 *   // For single agent
 *   const { events, isConnected, lastEvent } = useAgentStream(agentId);
 *
 *   // For all workspace agents
 *   const { events, isConnected } = useAgentStream(null, workspaceId);
 *
 * REFERENCES:
 *   - backend/app/routers/agents.py (WebSocket endpoints)
 *   - backend/app/services/agents/websocket_manager.py
 */

import { useState, useEffect, useRef, useCallback } from "react";

/**
 * Get the WebSocket URL for the backend.
 *
 * WHAT: Constructs WebSocket URL based on current location
 * WHY: Need to use ws:// or wss:// based on whether we're on HTTPS
 *
 * @returns {string} WebSocket base URL
 */
function getWebSocketUrl() {
  if (typeof window === "undefined") return "";

  // Use the same host as the current page
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.host;

  // WebSocket connects directly to backend via the /api proxy
  return `${protocol}//${host}/api/v1`;
}

/**
 * WebSocket connection states
 */
export const ConnectionState = {
  CONNECTING: "connecting",
  CONNECTED: "connected",
  DISCONNECTED: "disconnected",
  RECONNECTING: "reconnecting",
  ERROR: "error",
};

/**
 * Event types received from WebSocket
 */
export const AgentEventType = {
  CONNECTED: "connected",
  EVALUATION: "evaluation",
  TRIGGER: "trigger",
  STATUS_CHANGE: "status_change",
  PONG: "pong",
};

/**
 * Hook for streaming agent events via WebSocket.
 *
 * @param {string|null} agentId - Agent ID to subscribe to (null for all workspace agents)
 * @param {string|null} workspaceId - Workspace ID (required if agentId is null)
 * @param {Object} options - Configuration options
 * @param {boolean} options.enabled - Whether to connect (default: true)
 * @param {number} options.maxEvents - Max events to keep in memory (default: 100)
 * @param {number} options.reconnectDelay - Delay between reconnect attempts in ms (default: 3000)
 * @param {number} options.maxReconnects - Max reconnection attempts (default: 5)
 * @param {function} options.onEvent - Callback when event is received
 * @param {function} options.onConnect - Callback when connected
 * @param {function} options.onDisconnect - Callback when disconnected
 * @param {function} options.onError - Callback when error occurs
 *
 * @returns {Object} Hook state and controls
 */
export function useAgentStream(
  agentId = null,
  workspaceId = null,
  options = {}
) {
  const {
    enabled = true,
    maxEvents = 100,
    reconnectDelay = 3000,
    maxReconnects = 5,
    onEvent = null,
    onConnect = null,
    onDisconnect = null,
    onError = null,
  } = options;

  // State
  const [events, setEvents] = useState([]);
  const [connectionState, setConnectionState] = useState(
    ConnectionState.DISCONNECTED
  );
  const [lastEvent, setLastEvent] = useState(null);
  const [error, setError] = useState(null);

  // Refs
  const wsRef = useRef(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimeoutRef = useRef(null);
  const pingIntervalRef = useRef(null);

  /**
   * Connect to WebSocket.
   *
   * @param {string} token - Auth token for connection
   */
  const connect = useCallback(
    (token) => {
      if (!enabled) return;
      if (!token) {
        console.warn("[useAgentStream] No token provided");
        return;
      }

      // Clean up existing connection
      if (wsRef.current) {
        wsRef.current.close();
      }

      setConnectionState(ConnectionState.CONNECTING);

      // Build WebSocket URL
      const baseUrl = getWebSocketUrl();
      let wsUrl;

      if (agentId) {
        // Subscribe to single agent
        wsUrl = `${baseUrl}/agents/${agentId}/stream?token=${encodeURIComponent(
          token
        )}`;
      } else if (workspaceId) {
        // Subscribe to all workspace agents
        wsUrl = `${baseUrl}/agents/workspace/stream?token=${encodeURIComponent(
          token
        )}&workspace_id=${workspaceId}`;
      } else {
        console.warn(
          "[useAgentStream] Either agentId or workspaceId required"
        );
        setConnectionState(ConnectionState.ERROR);
        setError("Either agentId or workspaceId is required");
        return;
      }

      try {
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          console.log("[useAgentStream] Connected");
          setConnectionState(ConnectionState.CONNECTED);
          setError(null);
          reconnectCountRef.current = 0;

          // Start ping interval (every 30 seconds)
          pingIntervalRef.current = setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
              ws.send(JSON.stringify({ type: "ping" }));
            }
          }, 30000);

          if (onConnect) onConnect();
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);

            // Ignore pong messages
            if (data.type === AgentEventType.PONG) return;

            // Add to events (with limit)
            setEvents((prev) => {
              const newEvents = [data, ...prev];
              return newEvents.slice(0, maxEvents);
            });

            setLastEvent(data);

            if (onEvent) onEvent(data);
          } catch (e) {
            console.error("[useAgentStream] Failed to parse message:", e);
          }
        };

        ws.onerror = (event) => {
          console.error("[useAgentStream] WebSocket error:", event);
          setError("WebSocket connection error");

          if (onError) onError(event);
        };

        ws.onclose = (event) => {
          console.log("[useAgentStream] Disconnected:", event.code, event.reason);

          // Clear ping interval
          if (pingIntervalRef.current) {
            clearInterval(pingIntervalRef.current);
            pingIntervalRef.current = null;
          }

          if (onDisconnect) onDisconnect(event);

          // Don't reconnect if closed normally or max reconnects reached
          if (event.code === 1000 || reconnectCountRef.current >= maxReconnects) {
            setConnectionState(ConnectionState.DISCONNECTED);
            return;
          }

          // Attempt reconnection
          setConnectionState(ConnectionState.RECONNECTING);
          reconnectCountRef.current += 1;

          console.log(
            `[useAgentStream] Reconnecting in ${reconnectDelay}ms (attempt ${reconnectCountRef.current}/${maxReconnects})`
          );

          reconnectTimeoutRef.current = setTimeout(() => {
            connect(token);
          }, reconnectDelay);
        };

        wsRef.current = ws;
      } catch (e) {
        console.error("[useAgentStream] Failed to create WebSocket:", e);
        setConnectionState(ConnectionState.ERROR);
        setError(e.message);
      }
    },
    [
      enabled,
      agentId,
      workspaceId,
      maxEvents,
      reconnectDelay,
      maxReconnects,
      onEvent,
      onConnect,
      onDisconnect,
      onError,
    ]
  );

  /**
   * Disconnect from WebSocket.
   */
  const disconnect = useCallback(() => {
    // Clear reconnect timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    // Clear ping interval
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }

    // Close WebSocket
    if (wsRef.current) {
      wsRef.current.close(1000, "Client disconnected");
      wsRef.current = null;
    }

    setConnectionState(ConnectionState.DISCONNECTED);
  }, []);

  /**
   * Clear events buffer.
   */
  const clearEvents = useCallback(() => {
    setEvents([]);
    setLastEvent(null);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    // State
    events,
    connectionState,
    isConnected: connectionState === ConnectionState.CONNECTED,
    isConnecting:
      connectionState === ConnectionState.CONNECTING ||
      connectionState === ConnectionState.RECONNECTING,
    lastEvent,
    error,

    // Controls
    connect,
    disconnect,
    clearEvents,
  };
}

/**
 * Get events of a specific type.
 *
 * @param {Array} events - Array of events
 * @param {string} type - Event type to filter by
 * @returns {Array} Filtered events
 */
export function filterEventsByType(events, type) {
  return events.filter((e) => e.type === type);
}

/**
 * Get trigger events only.
 *
 * @param {Array} events - Array of events
 * @returns {Array} Trigger events
 */
export function getTriggerEvents(events) {
  return filterEventsByType(events, AgentEventType.TRIGGER);
}

/**
 * Get evaluation events only.
 *
 * @param {Array} events - Array of events
 * @returns {Array} Evaluation events
 */
export function getEvaluationEvents(events) {
  return filterEventsByType(events, AgentEventType.EVALUATION);
}

/**
 * Get status change events only.
 *
 * @param {Array} events - Array of events
 * @returns {Array} Status change events
 */
export function getStatusChangeEvents(events) {
  return filterEventsByType(events, AgentEventType.STATUS_CHANGE);
}

export default useAgentStream;
