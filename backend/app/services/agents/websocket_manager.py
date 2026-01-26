"""
WebSocket Connection Manager for Agent Real-Time Updates.

WHAT:
    Manages WebSocket connections for streaming agent evaluation events.
    Clients can subscribe to specific agents or all agents in a workspace.

WHY:
    Real-time updates provide better UX than polling:
    - Agent detail page shows live evaluation results
    - Dashboard can show live agent status changes
    - Users see immediate feedback when conditions are met

USAGE:
    # In evaluation engine after creating an event:
    from .websocket_manager import agent_ws_manager
    await agent_ws_manager.broadcast_event(workspace_id, agent_id, event_data)

    # In frontend:
    const ws = new WebSocket('/v1/agents/{agent_id}/stream')
    ws.onmessage = (event) => { ... }

REFERENCES:
    - backend/app/routers/agents.py (WebSocket endpoint)
    - ui/hooks/useAgentStream.ts (frontend consumer)
"""

import asyncio
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


@dataclass
class WebSocketConnection:
    """
    Represents a single WebSocket connection.

    WHAT: Stores connection metadata and the socket itself
    WHY: Need to track workspace/agent subscriptions per connection
    """
    websocket: WebSocket
    workspace_id: UUID
    agent_id: Optional[UUID] = None  # None = subscribed to all workspace agents
    connected_at: datetime = field(default_factory=datetime.utcnow)


class AgentWebSocketManager:
    """
    Manages WebSocket connections for agent real-time updates.

    WHAT:
        Singleton manager that handles:
        - Connection registration/deregistration
        - Broadcasting events to subscribed clients
        - Heartbeat/keep-alive management

    WHY:
        Centralized management ensures:
        - Events reach all subscribed clients
        - Clean disconnection handling
        - No memory leaks from stale connections
    """

    def __init__(self):
        # agent_id -> set of connections
        self._agent_connections: Dict[UUID, Set[WebSocket]] = defaultdict(set)
        # workspace_id -> set of connections (for workspace-wide subscriptions)
        self._workspace_connections: Dict[UUID, Set[WebSocket]] = defaultdict(set)
        # websocket -> connection metadata
        self._connection_metadata: Dict[WebSocket, WebSocketConnection] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        workspace_id: UUID,
        agent_id: Optional[UUID] = None,
    ) -> None:
        """
        Register a new WebSocket connection.

        Parameters:
            websocket: The FastAPI WebSocket connection
            workspace_id: User's workspace ID (for authorization)
            agent_id: Optional specific agent to subscribe to (None = all workspace agents)

        WHAT: Accept connection and register it for event broadcasting
        WHY: Connection must be tracked to receive relevant events
        """
        await websocket.accept()

        async with self._lock:
            connection = WebSocketConnection(
                websocket=websocket,
                workspace_id=workspace_id,
                agent_id=agent_id,
            )
            self._connection_metadata[websocket] = connection

            if agent_id:
                self._agent_connections[agent_id].add(websocket)
                logger.info(f"WebSocket connected for agent {agent_id}")
            else:
                self._workspace_connections[workspace_id].add(websocket)
                logger.info(f"WebSocket connected for workspace {workspace_id} (all agents)")

        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "agent_id": str(agent_id) if agent_id else None,
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
                if connection.agent_id:
                    self._agent_connections[connection.agent_id].discard(websocket)
                    if not self._agent_connections[connection.agent_id]:
                        del self._agent_connections[connection.agent_id]
                else:
                    self._workspace_connections[connection.workspace_id].discard(websocket)
                    if not self._workspace_connections[connection.workspace_id]:
                        del self._workspace_connections[connection.workspace_id]

                logger.info(f"WebSocket disconnected: agent={connection.agent_id}, workspace={connection.workspace_id}")

    async def broadcast_event(
        self,
        workspace_id: UUID,
        agent_id: UUID,
        event_type: str,
        data: dict,
    ) -> None:
        """
        Broadcast an event to all relevant subscribers.

        Parameters:
            workspace_id: The workspace the event belongs to
            agent_id: The agent that generated the event
            event_type: Type of event (evaluation, trigger, error, etc.)
            data: Event payload

        WHAT: Send event to all clients subscribed to this agent or workspace
        WHY: Real-time updates without polling
        """
        message = {
            "type": event_type,
            "agent_id": str(agent_id),
            "workspace_id": str(workspace_id),
            "timestamp": datetime.utcnow().isoformat(),
            "data": data,
        }

        # Get all relevant connections
        connections_to_notify: Set[WebSocket] = set()

        async with self._lock:
            # Connections subscribed to this specific agent
            connections_to_notify.update(self._agent_connections.get(agent_id, set()))
            # Connections subscribed to all workspace agents
            connections_to_notify.update(self._workspace_connections.get(workspace_id, set()))

        if not connections_to_notify:
            return

        # Broadcast to all connections (handle failures gracefully)
        disconnected = []

        for websocket in connections_to_notify:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send WebSocket message: {e}")
                disconnected.append(websocket)

        # Clean up any failed connections
        for websocket in disconnected:
            await self.disconnect(websocket)

    async def broadcast_evaluation_event(
        self,
        workspace_id: UUID,
        agent_id: UUID,
        event_data: dict,
    ) -> None:
        """
        Broadcast an agent evaluation event.

        Parameters:
            workspace_id: Workspace ID
            agent_id: Agent ID
            event_data: Evaluation event data (AgentEvaluationEventOut dict)

        WHAT: Specialized broadcast for evaluation events
        WHY: Most common event type, deserves dedicated method
        """
        await self.broadcast_event(
            workspace_id=workspace_id,
            agent_id=agent_id,
            event_type="evaluation",
            data=event_data,
        )

    async def broadcast_status_change(
        self,
        workspace_id: UUID,
        agent_id: UUID,
        old_status: str,
        new_status: str,
        reason: Optional[str] = None,
    ) -> None:
        """
        Broadcast agent status change.

        Parameters:
            workspace_id: Workspace ID
            agent_id: Agent ID
            old_status: Previous agent status
            new_status: New agent status
            reason: Optional reason for status change

        WHAT: Notify when agent transitions between states
        WHY: Dashboard shows live agent status badges
        """
        await self.broadcast_event(
            workspace_id=workspace_id,
            agent_id=agent_id,
            event_type="status_change",
            data={
                "old_status": old_status,
                "new_status": new_status,
                "reason": reason,
            },
        )

    async def broadcast_trigger(
        self,
        workspace_id: UUID,
        agent_id: UUID,
        entity_id: UUID,
        entity_name: str,
        actions_executed: List[dict],
    ) -> None:
        """
        Broadcast agent trigger event.

        Parameters:
            workspace_id: Workspace ID
            agent_id: Agent ID
            entity_id: Entity that triggered
            entity_name: Entity name for display
            actions_executed: List of action results

        WHAT: Notify when agent takes action
        WHY: High-visibility event for users
        """
        await self.broadcast_event(
            workspace_id=workspace_id,
            agent_id=agent_id,
            event_type="trigger",
            data={
                "entity_id": str(entity_id),
                "entity_name": entity_name,
                "actions_executed": actions_executed,
            },
        )

    def get_connection_count(self, agent_id: Optional[UUID] = None) -> int:
        """
        Get number of active connections.

        Parameters:
            agent_id: Optional agent to filter by

        Returns:
            Number of active WebSocket connections

        WHAT: Count active connections for monitoring
        WHY: Useful for debugging and metrics
        """
        if agent_id:
            return len(self._agent_connections.get(agent_id, set()))
        return len(self._connection_metadata)


# Singleton instance
# WHAT: Global manager accessible from evaluation engine
# WHY: Evaluation engine needs to broadcast events from worker context
agent_ws_manager = AgentWebSocketManager()
