#!/usr/bin/env python3
"""
Base Streaming Node - Nodo base con capacidad de streaming token-by-token
========================================================================
Reemplaza GraphNode para nodos que necesitan emitir eventos en tiempo real.
"""

from typing import AsyncGenerator, Optional, Any, Dict
import asyncio
from abc import abstractmethod

from src.infrastructure.langgraph.nodes.base import GraphNode
from src.infrastructure.langgraph.state import GraphState
from src.infrastructure.langgraph.utils.timing import workflow_sleep
from src.infrastructure.streaming.token_streamer import get_token_streamer
from src.core.logging import get_logger

logger = get_logger(__name__)


class StreamingNode(GraphNode):
    """
    Nodo con capacidad de streaming token-by-token.

    En lugar de ejecutar todo y luego emitir eventos,
    emite tokens incrementales mientras procesa.
    """

    def __init__(self, name: str = None):
        super().__init__(name)
        self.streamer = get_token_streamer()
        self._is_agent_node = True  # Siempre es un nodo de agente

    def run(self, state: GraphState) -> GraphState:
        """
        Ejecuta el nodo con streaming.

        NOTA: Este método es síncrono porque LangGraph lo requiere,
        pero internamente ejecuta streaming asíncrono.
        """
        # Ejecutar streaming en el event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # No hay loop, crear uno temporal
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self._run_streaming(state))
            finally:
                loop.close()
        else:
            # Hay un loop activo
            if loop.is_running():
                # Ejecutar en thread separado para no bloquear
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._run_streaming(state)
                    )
                    return future.result()
            else:
                return loop.run_until_complete(self._run_streaming(state))

    async def _run_streaming(self, state: GraphState) -> GraphState:
        """
        Ejecuta el nodo con streaming asíncrono.
        """
        session_id = state.session_id or "unknown"

        # Stream de tokens
        async for token in self.streamer.stream_agent_execution(
            agent_name=self.name,
            session_id=session_id,
            process_func=lambda: self.process_incrementally(state)
        ):
            # Los tokens se emiten automáticamente por WebSocket
            # Aquí podríamos procesar o loguear si necesario
            if token.type == 'progress':
                logger.debug(f"Streaming token: {token.content}")

        # Actualizar estado con resultado final
        return self.finalize_state(state)

    @abstractmethod
    async def process_incrementally(self, state: GraphState) -> AsyncGenerator[str, None]:
        """
        Procesa el estado y genera resultados incrementales.

        Este método debe ser implementado por cada nodo concreto.
        Debe hacer yield de strings que representan progreso parcial.

        Args:
            state: Estado del grafo

        Yields:
            str: Mensajes de progreso parcial
        """
        pass

    @abstractmethod
    def finalize_state(self, state: GraphState) -> GraphState:
        """
        Finaliza y actualiza el estado después del streaming.

        Args:
            state: Estado del grafo

        Returns:
            GraphState: Estado actualizado
        """
        pass


<<<<<<< HEAD
class StreamingSummaryNode(StreamingNode):
=======
class StreamingCapiGusNode(StreamingNode):
>>>>>>> origin/develop
    """
    Ejemplo: Nodo de resumen con streaming token-by-token.
    """

    def __init__(self):
<<<<<<< HEAD
        super().__init__(name="summary_streaming")
=======
        super().__init__(name="capi_gus_streaming")
>>>>>>> origin/develop

    async def process_incrementally(self, state: GraphState) -> AsyncGenerator[str, None]:
        """
        Genera resumen financiero incrementalmente.
        """
        # Simular análisis incremental
        steps = [
            "Iniciando análisis de datos financieros...",
            "Procesando transacciones del último periodo...",
            "Calculando métricas de rendimiento...",
            "Analizando tendencias y patrones...",
            "Evaluando KPIs principales...",
            "Comparando con periodos anteriores...",
            "Identificando áreas de mejora...",
            "Generando conclusiones ejecutivas...",
            "Finalizando resumen financiero..."
        ]

        for step in steps:
            # Simular procesamiento
            await workflow_sleep(0.2)  # En producción, aquí iría el procesamiento real

            # Emitir token de progreso
            yield step

        # En producción, aquí procesarías datos reales
        # Por ejemplo:
        # async for result in self.analyze_financial_data(state):
        #     yield result

    def finalize_state(self, state: GraphState) -> GraphState:
        """
        Actualiza el estado con el resumen final.
        """
        from src.infrastructure.langgraph.state import StateMutator

        # Aquí irían los resultados reales del análisis
        summary = {
            "total_ingresos": 1500000,
            "total_egresos": 950000,
            "utilidad_neta": 550000,
            "margen": 36.67
        }

        # Actualizar estado
        state = StateMutator.update_field(
            state,
            "response_metadata",
            {"summary": summary, "streaming_completed": True}
        )

        state = StateMutator.update_field(
            state,
            "response_message",
            f"Resumen completado. Utilidad neta: ${summary['utilidad_neta']:,.2f}"
        )

        return state


class StreamingBranchNode(StreamingNode):
    """
    Nodo de análisis de sucursal con streaming.
    """

    def __init__(self):
        super().__init__(name="branch_streaming")

    async def process_incrementally(self, state: GraphState) -> AsyncGenerator[str, None]:
        """
        Analiza sucursales incrementalmente.
        """
        branches = ["SUC-001", "SUC-002", "SUC-003", "SUC-404", "SUC-005"]

        for branch in branches:
            yield f"Analizando sucursal {branch}..."
            await workflow_sleep(0.3)

            yield f"Calculando métricas para {branch}..."
            await workflow_sleep(0.2)

            yield f"Evaluando rendimiento de {branch}..."
            await workflow_sleep(0.2)

    def finalize_state(self, state: GraphState) -> GraphState:
        """
        Actualiza estado con análisis de sucursales.
        """
        from src.infrastructure.langgraph.state import StateMutator

        branch_data = {
            "SUC-404": {
                "rendimiento": "Excelente",
                "ingresos": 450000,
                "crecimiento": "+15%"
            }
        }

        state = StateMutator.update_field(
            state,
            "response_metadata",
            {"branches": branch_data}
        )

        return state


# Función helper para convertir nodos existentes a streaming
def convert_to_streaming(node_class):
    """
    Decorator para convertir un GraphNode en StreamingNode.
    """
    class StreamingWrapper(StreamingNode):
        def __init__(self):
            super().__init__(name=f"{node_class.__name__}_streaming")
            self.original_node = node_class()

        async def process_incrementally(self, state: GraphState) -> AsyncGenerator[str, None]:
            # Simular streaming del nodo original
            yield f"Iniciando {self.original_node.name}..."
            await workflow_sleep(0.1)

            yield f"Procesando con {self.original_node.name}..."
            await workflow_sleep(0.5)

            yield f"Finalizando {self.original_node.name}..."

        def finalize_state(self, state: GraphState) -> GraphState:
            # Ejecutar el nodo original
            return self.original_node.run(state)

<<<<<<< HEAD
    return StreamingWrapper
=======
    return StreamingWrapper
>>>>>>> origin/develop
