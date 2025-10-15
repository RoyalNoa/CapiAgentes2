#!/usr/bin/env python3
"""
Token-by-Token Streaming para Eventos en Tiempo Real
=====================================================
Implementación de streaming incremental tipo Claude para eventos de agentes.
En lugar de esperar a que termine todo el procesamiento, emitimos tokens/eventos
mientras se generan.
"""

import asyncio
import time
from typing import AsyncGenerator, Dict, Any, Optional
from dataclasses import dataclass
from src.infrastructure.langgraph.utils.timing import workflow_sleep
from src.infrastructure.websocket.event_broadcaster import get_event_broadcaster
from src.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class StreamToken:
    """Representa un token/evento individual en el stream."""
    type: str  # 'start', 'progress', 'data', 'end'
    agent: str
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class TokenStreamer:
    """
    Streaming token-by-token estilo Claude.
    Emite eventos incrementales en tiempo real sin esperar a completar.
    """

    def __init__(self):
        self.broadcaster = get_event_broadcaster()
        self._active_streams: Dict[str, bool] = {}

    async def stream_agent_execution(
        self,
        agent_name: str,
        session_id: str,
        process_func: callable
    ) -> AsyncGenerator[StreamToken, None]:
        """
        Ejecuta un agente con streaming token-by-token.

        Args:
            agent_name: Nombre del agente
            session_id: ID de sesión
            process_func: Función async que genera resultados parciales

        Yields:
            StreamToken: Eventos incrementales en tiempo real
        """
        stream_id = f"{session_id}:{agent_name}"
        self._active_streams[stream_id] = True

        try:
            # 1. EMITIR TOKEN DE INICIO INMEDIATAMENTE
            start_token = StreamToken(
                type='start',
                agent=agent_name,
                metadata={'session_id': session_id}
            )

            # Enviar por WebSocket INMEDIATAMENTE
            await self._emit_token(start_token, session_id)
            yield start_token

            # 2. PROCESAR Y EMITIR TOKENS INCREMENTALES
            token_count = 0
            async for partial_result in process_func():
                if not self._active_streams.get(stream_id, False):
                    break  # Stream cancelado

                # Crear token de progreso
                progress_token = StreamToken(
                    type='progress',
                    agent=agent_name,
                    content=partial_result,
                    metadata={
                        'session_id': session_id,
                        'token_index': token_count
                    }
                )

                # Emitir INMEDIATAMENTE sin esperar
                await self._emit_token(progress_token, session_id)
                yield progress_token

                token_count += 1

                # Micro-yield para garantizar evento se envíe
                await asyncio.sleep(0)

            # 3. EMITIR TOKEN DE FIN
            end_token = StreamToken(
                type='end',
                agent=agent_name,
                metadata={
                    'session_id': session_id,
                    'total_tokens': token_count
                }
            )

            await self._emit_token(end_token, session_id)
            yield end_token

        except Exception as e:
            # Emitir token de error
            error_token = StreamToken(
                type='error',
                agent=agent_name,
                content=str(e),
                metadata={'session_id': session_id}
            )
            await self._emit_token(error_token, session_id)
            yield error_token

        finally:
            # Limpiar stream activo
            self._active_streams.pop(stream_id, None)

    async def _emit_token(self, token: StreamToken, session_id: str):
        """Emite un token por WebSocket INMEDIATAMENTE."""

        # Mapear tipo de token a evento WebSocket
        if token.type == 'start':
            await self.broadcaster.broadcast_agent_start(
                agent_name=token.agent,
                session_id=session_id,
                action='streaming_start',
                meta={'streaming': True, 'timestamp': token.timestamp}
            )

        elif token.type == 'progress':
            # Evento personalizado para progreso incremental
            await self.broadcaster.broadcast_node_transition(
                from_node=token.agent,
                to_node='streaming',
                session_id=session_id,
                action='streaming_progress',
                meta={
                    'content': token.content,
                    'token_index': token.metadata.get('token_index', 0),
                    'timestamp': token.timestamp
                }
            )

        elif token.type == 'end':
            await self.broadcaster.broadcast_agent_end(
                agent_name=token.agent,
                session_id=session_id,
                success=True,
                action='streaming_end',
                meta={
                    'total_tokens': token.metadata.get('total_tokens', 0),
                    'timestamp': token.timestamp
                }
            )

        elif token.type == 'error':
            await self.broadcaster.broadcast_agent_end(
                agent_name=token.agent,
                session_id=session_id,
                success=False,
                action='streaming_error',
                meta={
                    'error': token.content,
                    'timestamp': token.timestamp
                }
            )

        # CRÍTICO: Forzar flush inmediato del WebSocket
        await asyncio.sleep(0)

    def cancel_stream(self, session_id: str, agent_name: str):
        """Cancela un stream activo."""
        stream_id = f"{session_id}:{agent_name}"
        self._active_streams[stream_id] = False

    def is_streaming(self, session_id: str, agent_name: str) -> bool:
        """Verifica si hay un stream activo."""
        stream_id = f"{session_id}:{agent_name}"
        return self._active_streams.get(stream_id, False)


# Singleton global
_token_streamer = TokenStreamer()

def get_token_streamer() -> TokenStreamer:
    """Obtiene la instancia global del token streamer."""
    return _token_streamer


# Ejemplo de uso con un agente
async def example_streaming_agent():
    """
    Ejemplo de cómo usar el token streamer con un agente.
    """
    streamer = get_token_streamer()

    # Función que genera resultados parciales
    async def process_incrementally():
        """Simula procesamiento incremental."""
        messages = [
            "Analizando datos financieros",
            "Calculando métricas de rendimiento",
            "Evaluando tendencias históricas",
            "Generando resumen ejecutivo",
            "Compilando recomendaciones"
        ]

        for msg in messages:
            # Simular trabajo
            await workflow_sleep(0.5)
            # Yield resultado parcial
            yield msg

    # Ejecutar con streaming
    async for token in streamer.stream_agent_execution(
        agent_name="summary",
        session_id="test_session",
        process_func=process_incrementally
    ):
        print(f"Token emitido: {token.type} - {token.content}")


if __name__ == "__main__":
    asyncio.run(example_streaming_agent())
