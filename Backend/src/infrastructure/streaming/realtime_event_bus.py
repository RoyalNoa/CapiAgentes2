#!/usr/bin/env python3
"""
Event Bus Paralelo para Streaming en Tiempo Real con LangGraph
===============================================================
Solución pragmática: Thread paralelo que envía eventos mientras LangGraph ejecuta.
No modifica LangGraph, solo agrega capacidad de streaming.
"""

import asyncio
import threading
import queue
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import json

from src.infrastructure.websocket.event_broadcaster import get_event_broadcaster
from src.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class EventMessage:
    """Mensaje de evento para enviar por WebSocket."""
    type: str  # 'agent_start', 'agent_progress', 'agent_end'
    agent: str
    session_id: str
    content: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class RealtimeEventBus:
    """
    Event Bus que ejecuta en thread paralelo para enviar eventos en tiempo real
    mientras LangGraph ejecuta síncronamente.

    SOLUCIÓN PRAGMÁTICA: No es elegante, pero funciona.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern para instancia única."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Inicializa el event bus si no está inicializado."""
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._queue = queue.Queue()
            self._running = False
            self._worker_thread = None
            self._broadcaster = get_event_broadcaster()
            self._event_loop = None

            # Estadísticas
            self._events_sent = 0
            self._events_failed = 0

            # Iniciar worker thread
            self.start()

    def start(self):
        """Inicia el thread worker para procesar eventos."""
        if not self._running:
            self._running = True
            self._worker_thread = threading.Thread(
                target=self._worker_loop,
                daemon=True,
                name="EventBusWorker"
            )
            self._worker_thread.start()
            logger.info("RealtimeEventBus worker started")

    def stop(self):
        """Detiene el thread worker."""
        self._running = False
        # Enviar evento poison pill para despertar el worker
        self._queue.put(None)
        if self._worker_thread:
            self._worker_thread.join(timeout=2)
        logger.info(f"RealtimeEventBus stopped. Events sent: {self._events_sent}, failed: {self._events_failed}")

    def emit_agent_start(self, agent: str, session_id: str, metadata: Optional[Dict] = None):
        """
        Emite evento de inicio de agente INMEDIATAMENTE.
        No bloquea, no espera.
        """
        event = EventMessage(
            type='agent_start',
            agent=agent,
            session_id=session_id,
            metadata=metadata or {}
        )
        self._queue.put(event)
        logger.debug(f"Queued agent_start for {agent}")

    def emit_agent_progress(self, agent: str, session_id: str, content: str, metadata: Optional[Dict] = None):
        """
        Emite evento de progreso de agente.
        """
        event = EventMessage(
            type='agent_progress',
            agent=agent,
            session_id=session_id,
            content=content,
            metadata=metadata or {}
        )
        self._queue.put(event)

    def emit_agent_end(self, agent: str, session_id: str, success: bool = True, metadata: Optional[Dict] = None):
        """
        Emite evento de fin de agente.
        """
        event = EventMessage(
            type='agent_end',
            agent=agent,
            session_id=session_id,
            metadata={**(metadata or {}), 'success': success}
        )
        self._queue.put(event)
        logger.debug(f"Queued agent_end for {agent}")

    def _worker_loop(self):
        """
        Loop del worker thread que procesa eventos de la cola.
        Ejecuta en thread separado para no bloquear LangGraph.
        """
        logger.info("EventBus worker loop started")

        # Crear event loop para este thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._event_loop = loop

        while self._running:
            try:
                # Obtener evento de la cola (bloquea hasta que haya uno)
                event = self._queue.get(timeout=1)

                if event is None:  # Poison pill
                    break

                # Enviar evento por WebSocket
                try:
                    loop.run_until_complete(self._send_event(event))
                    self._events_sent += 1
                except Exception as e:
                    logger.error(f"Failed to send event: {e}")
                    self._events_failed += 1

            except queue.Empty:
                continue  # Timeout normal, continuar
            except Exception as e:
                logger.error(f"Worker loop error: {e}")

        loop.close()
        logger.info("EventBus worker loop ended")

    async def _send_event(self, event: EventMessage):
        """
        Envía un evento por WebSocket.
        """
        broadcaster = self._broadcaster

        # Mapear tipo de evento a método del broadcaster
        if event.type == 'agent_start':
            await broadcaster.broadcast_agent_start(
                agent_name=event.agent,
                session_id=event.session_id,
                action=self._get_action_for_agent(event.agent),
                meta={
                    **event.metadata,
                    'timestamp': event.timestamp,
                    'realtime': True  # Indicador de que es en tiempo real
                }
            )

        elif event.type == 'agent_progress':
            # Usar node_transition para progreso
            await broadcaster.broadcast_node_transition(
                from_node=event.agent,
                to_node='processing',
                session_id=event.session_id,
                action='progress',
                meta={
                    'content': event.content,
                    **event.metadata,
                    'timestamp': event.timestamp,
                    'realtime': True
                }
            )

        elif event.type == 'agent_end':
            success = event.metadata.get('success', True)
            await broadcaster.broadcast_agent_end(
                agent_name=event.agent,
                session_id=event.session_id,
                success=success,
                action=self._get_action_for_agent(event.agent),
                meta={
                    **event.metadata,
                    'timestamp': event.timestamp,
                    'realtime': True
                }
            )

        # Forzar flush inmediato
        await asyncio.sleep(0)

    def _get_action_for_agent(self, agent: str) -> str:
        """Mapea nombre de agente a tipo de acción semántica."""
        agent_lower = agent.lower()

        action_map = {
            'summary': 'financial_summary',
            'branch': 'branch_analysis',
            'anomaly': 'anomaly_detection',
            'capi_gus': 'conversation',
            'capi_datab': 'database_query',
            'capi_elcajas': 'branch_operations',
            'capi_desktop': 'desktop_operation',
        }

        for key, action in action_map.items():
            if key in agent_lower:
                return action

        return 'agent_action'

    def get_stats(self) -> Dict[str, int]:
        """Obtiene estadísticas del event bus."""
        return {
            'events_sent': self._events_sent,
            'events_failed': self._events_failed,
            'queue_size': self._queue.qsize(),
            'is_running': self._running
        }


# Instancia global singleton
_event_bus = None

def get_event_bus() -> RealtimeEventBus:
    """Obtiene la instancia global del event bus."""
    global _event_bus
    if _event_bus is None:
        _event_bus = RealtimeEventBus()
    return _event_bus


# Funciones helper para uso rápido
def emit_start(agent: str, session_id: str):
    """Helper rápido para emitir inicio de agente."""
    get_event_bus().emit_agent_start(agent, session_id)

def emit_progress(agent: str, session_id: str, content: str):
    """Helper rápido para emitir progreso."""
    get_event_bus().emit_agent_progress(agent, session_id, content)

def emit_end(agent: str, session_id: str, success: bool = True):
    """Helper rápido para emitir fin de agente."""
    get_event_bus().emit_agent_end(agent, session_id, success)
