#!/usr/bin/env python3
"""
CAPI - WebSocket Event Broadcaster
=================================
Ruta: /Backend/src/infrastructure/websocket/event_broadcaster.py
Descripción: Broadcaster ligero de eventos WebSocket para visualización del ciclo
de vida de agentes en PantallaAgentes. Emite eventos según esquema EVENTS.schema.json
Estado: ✅ EN USO ACTIVO - PantallaAgentes feature core
Dependencias: WebSocket, JSON, UUID, datetime
Eventos: node_transition, agent_start, agent_end
Propósito: Comunicación en tiempo real UI ↔ Backend para visualización de agentes
Esquema: AI/Tablero/PantallaAgentes/EVENTS.schema.json
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Dict, Any, Set, Optional, List
from fastapi import WebSocket
import asyncio

from src.core.logging import get_logger

logger = get_logger(__name__)


class AgentEventBroadcaster:
    """
    Lightweight event broadcaster for agent lifecycle events.

    Manages WebSocket connections and broadcasts events according to the
    PantallaAgentes event schema.
    """

    def __init__(self):
        # Store active connections
        self._connections: Set[WebSocket] = set()
        # Event history for debugging
        self._event_history: list = []
        self._max_history = 50
        self._session_states: Dict[str, Dict[str, Any]] = {}

    async def add_connection(self, websocket: WebSocket):
        """Add WebSocket connection for event broadcasting."""
        self._connections.add(websocket)
        logger.info(f"WebSocket connection added for agent events. Total: {len(self._connections)}")

    async def remove_connection(self, websocket: WebSocket):
        """Remove WebSocket connection."""
        self._connections.discard(websocket)
        logger.info(f"WebSocket connection removed. Total: {len(self._connections)}")

    def update_session_state(self, session_id: str, state: Dict[str, Any]):
        """Store latest state snapshot per session."""
        if not session_id:
            return
        self._session_states[session_id] = state

    def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Return last known state snapshot for a session."""
        if not session_id:
            return None
        return self._session_states.get(session_id)

    async def broadcast_node_transition(
        self,
        from_node: str,
        to_node: str,
        session_id: str,
        meta: Optional[Dict[str, Any]] = None
    ):
        """
        Broadcast node transition event.

        Args:
            from_node: Source node ID
            to_node: Target node ID
            session_id: Session identifier
            meta: Additional metadata
        """
        payload = {
            "from": from_node,
            "to": to_node,
            **(meta or {})
        }
        event = {
            "type": "node_transition",
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "from": from_node,
            "to": to_node,
            "session_id": session_id,
            "meta": meta or {},
            "data": payload
        }

        await self._broadcast_event(event)

    async def broadcast_agent_start(
        self,
        agent_name: str,
        session_id: str,
        meta: Optional[Dict[str, Any]] = None
    ):
        """
        Broadcast agent start event.

        Args:
            agent_name: Name of the agent starting execution
            session_id: Session identifier
            meta: Additional metadata (e.g., input_tokens)
        """
        payload = {
            "agent": agent_name,
            **(meta or {})
        }
        event = {
            "type": "agent_start",
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "agent": agent_name,
            "session_id": session_id,
            "meta": meta or {},
            "data": payload
        }

        await self._broadcast_event(event)

    async def broadcast_agent_end(
        self,
        agent_name: str,
        session_id: str,
        success: bool = True,
        duration_ms: Optional[float] = None,
        meta: Optional[Dict[str, Any]] = None
    ):
        """
        Broadcast agent end event.

        Args:
            agent_name: Name of the agent that finished
            session_id: Session identifier
            success: Whether execution was successful
            duration_ms: Execution duration in milliseconds
            meta: Additional metadata (e.g., output_tokens)
        """
        payload = {
            "agent": agent_name,
            "success": success,
            **(meta or {})
        }
        event = {
            "type": "agent_end",
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "agent": agent_name,
            "session_id": session_id,
            "ok": success,
            "meta": meta or {},
            "data": payload
        }

        if duration_ms is not None:
            event["duration_ms"] = duration_ms
            payload["duration_ms"] = duration_ms

        await self._broadcast_event(event)

    async def _broadcast_event(self, event: Dict[str, Any]):
        """
        Internal method to broadcast event to all connections.

        Args:
            event: Event data to broadcast
        """
        # Persist regardless of active connections
        self._add_to_history(event)

        if not self._connections:
            return

        # Broadcast to all connections
        message = json.dumps(event)
        disconnected = set()

        for connection in self._connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send WebSocket message: {e}")
                disconnected.add(connection)

        # Remove disconnected connections
        for conn in disconnected:
            self._connections.discard(conn)

        logger.debug(f"Broadcasted {event['type']} event to {len(self._connections)} connections")

    def _add_to_history(self, event: Dict[str, Any]):
        """Add event to internal history for debugging."""
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]

    def get_event_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent event history."""
        return self._event_history[-limit:]

    def clear_history(self):
        """Clear event history."""
        self._event_history.clear()


# Global singleton instance
_event_broadcaster = AgentEventBroadcaster()


def get_event_broadcaster() -> AgentEventBroadcaster:
    """Get the global event broadcaster instance."""
    return _event_broadcaster