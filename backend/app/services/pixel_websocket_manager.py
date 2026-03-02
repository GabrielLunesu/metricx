"""
Pixel Event WebSocket Manager.

WHAT:
    Manages WebSocket connections for streaming real-time pixel events
    (page views, product views, add-to-carts, checkouts) to connected
    dashboard clients.

WHY:
    Real-time visibility into pixel events lets merchants see customer
    activity as it happens — no polling, no page refresh. This powers
    the "Live Feed" panel on the attribution page.

USAGE:
    # In pixel_events.py after saving a PixelEvent to DB:
    from app.services.pixel_websocket_manager import pixel_ws_manager
    await pixel_ws_manager.broadcast(workspace_id, event_data)

    # In frontend:
    const ws = new WebSocket('/api/v1/pixel-events/stream?token=...')
    ws.onmessage = (event) => { ... }

REFERENCES:
    - backend/app/services/agents/websocket_manager.py (pattern source)
    - backend/app/routers/pixel_events.py (WebSocket endpoint + broadcast caller)
    - ui/hooks/usePixelStream.js (frontend consumer)
"""

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Set
from uuid import UUID

from fastapi import WebSocket

logger = logging.getLogger(__name__)


@dataclass
class PixelWSConnection:
    """
    Metadata for a single pixel WebSocket connection.

    WHAT: Tracks which workspace this connection belongs to
    WHY: Broadcasts are scoped to workspace — only send events to viewers of the same workspace
    """
    websocket: WebSocket
    workspace_id: UUID
    connected_at: datetime = field(default_factory=datetime.utcnow)


class PixelWebSocketManager:
    """
    Manages WebSocket connections for pixel event live streaming.

    WHAT:
        Simplified version of AgentWebSocketManager — only workspace-level
        connections (no agent subscriptions). Handles:
        - Connection registration/deregistration
        - Broadcasting pixel events to workspace viewers
        - Graceful cleanup of dead connections

    WHY:
        Centralized manager ensures all connected attribution page viewers
        receive pixel events instantly without polling.
    """

    def __init__(self):
        # workspace_id -> set of WebSocket connections
        self._workspace_connections: Dict[UUID, Set[WebSocket]] = defaultdict(set)
        # websocket -> connection metadata
        self._connection_metadata: Dict[WebSocket, PixelWSConnection] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, workspace_id: UUID) -> None:
        """
        Register a new WebSocket connection for pixel event streaming.

        Parameters:
            websocket: The FastAPI WebSocket connection
            workspace_id: Workspace to receive events for

        WHAT: Accept the WebSocket and register it for broadcasts
        WHY: Connection must be tracked to receive pixel events for this workspace
        """
        await websocket.accept()

        async with self._lock:
            connection = PixelWSConnection(
                websocket=websocket,
                workspace_id=workspace_id,
            )
            self._connection_metadata[websocket] = connection
            self._workspace_connections[workspace_id].add(websocket)

        logger.info(f"[PIXEL_WS] Connected for workspace {workspace_id}")

        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "workspace_id": str(workspace_id),
            "timestamp": datetime.utcnow().isoformat(),
        })

    async def disconnect(self, websocket: WebSocket) -> None:
        """
        Remove a WebSocket connection.

        Parameters:
            websocket: The WebSocket to remove

        WHAT: Clean up connection from all tracking structures
        WHY: Prevent memory leaks and sending to dead connections
        """
        async with self._lock:
            connection = self._connection_metadata.pop(websocket, None)

            if connection:
                self._workspace_connections[connection.workspace_id].discard(websocket)
                # Clean up empty workspace entry
                if not self._workspace_connections[connection.workspace_id]:
                    del self._workspace_connections[connection.workspace_id]

                logger.info(f"[PIXEL_WS] Disconnected from workspace {connection.workspace_id}")

    async def broadcast(self, workspace_id: UUID, event_data: dict) -> None:
        """
        Broadcast a pixel event to all connected clients for a workspace.

        Parameters:
            workspace_id: The workspace the event belongs to
            event_data: Pixel event payload to send

        WHAT: Send event to all WebSocket clients viewing this workspace
        WHY: Real-time pixel event feed without polling
        """
        async with self._lock:
            connections = set(self._workspace_connections.get(workspace_id, set()))

        if not connections:
            return

        # Broadcast to all connections, track failures
        disconnected = []

        for websocket in connections:
            try:
                await websocket.send_json(event_data)
            except Exception as e:
                logger.warning(f"[PIXEL_WS] Failed to send message: {e}")
                disconnected.append(websocket)

        # Clean up failed connections
        for websocket in disconnected:
            await self.disconnect(websocket)

    def get_connection_count(self, workspace_id: UUID = None) -> int:
        """
        Get number of active connections.

        Parameters:
            workspace_id: Optional workspace to filter by

        Returns:
            Number of active WebSocket connections

        WHAT: Count active connections for monitoring
        WHY: Useful for debugging and metrics
        """
        if workspace_id:
            return len(self._workspace_connections.get(workspace_id, set()))
        return len(self._connection_metadata)


# Singleton instance
# WHAT: Global manager accessible from pixel_events router
# WHY: Ingestion endpoint needs to broadcast events to connected clients
pixel_ws_manager = PixelWebSocketManager()
