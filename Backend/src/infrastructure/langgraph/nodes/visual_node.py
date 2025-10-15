#!/usr/bin/env python3
"""
Visual-First Node Implementation for Innovation Competition
===========================================================
Optimizado para MÁXIMO IMPACTO VISUAL en competencia de innovación.
Performance < Experiencia Visual
"""

import asyncio
import time
from typing import Optional, Dict, Any
from langgraph.checkpoint import interrupt

from src.infrastructure.langgraph.nodes.base import GraphNode
from src.infrastructure.langgraph.state import GraphState, StateMutator
from src.infrastructure.websocket.event_broadcaster import get_event_broadcaster
from src.infrastructure.langgraph.utils.timing import scale_duration, workflow_sleep_sync
from src.core.logging import get_logger

logger = get_logger(__name__)


class VisualOptimizedNode(GraphNode):
    """
    Nodo optimizado para experiencia visual en competencia de innovación.

    Prioridades:
    1. Animaciones completas y visibles
    2. Transiciones suaves
    3. Feedback constante
    4. Sensación "premium"
    """

    # Timing optimizado para UX
    MIN_PROCESSING_TIME = 1.5  # Mínimo para que shimmer se vea bien
    MAX_PROCESSING_TIME = 3.0  # Máximo para no aburrir
    OPTIMAL_SHIMMER_TIME = 2.0  # Tiempo óptimo para animación

    def __init__(self, name: str = None):
        super().__init__(name)
        self._is_agent_node = True
        self.broadcaster = get_event_broadcaster()

    def run(self, state: GraphState) -> GraphState:
        """
        Ejecuta el nodo con timing optimizado para máximo impacto visual.
        """
        start_time = time.time()
        session_id = state.session_id or "demo"

        try:
            # 1. EMITIR INICIO con efecto dramático
            self._emit_visual_start(state)

            # 2. CHECKPOINT INICIAL (para posible interrupción)
            if self._should_checkpoint():
                # Interrupción visual para mostrar progreso
                interrupt({
                    "type": "visual_checkpoint",
                    "agent": self.name,
                    "status": "processing",
                    "message": self._get_processing_message(),
                    "progress": 0.3
                })

            # 3. PROCESAMIENTO con timing visual
            result = self._process_with_visual_timing(state)

            # 4. CHECKPOINT INTERMEDIO (más drama visual)
            if self._needs_intermediate_checkpoint():
                interrupt({
                    "type": "visual_checkpoint",
                    "agent": self.name,
                    "status": "analyzing",
                    "message": self._get_analyzing_message(),
                    "progress": 0.7
                })

            # 5. GARANTIZAR TIEMPO MÍNIMO para animación
            elapsed = time.time() - start_time
            if elapsed < self.MIN_PROCESSING_TIME:
                # Esperar para que la animación se vea completa
                remaining = self.MIN_PROCESSING_TIME - elapsed
                workflow_sleep_sync(remaining)
                logger.debug(f"Visual delay added: {remaining:.2f}s for better UX")

            # 6. EMITIR FINALIZACIÓN con transición suave
            self._emit_visual_end(state, success=True, duration_ms=(time.time() - start_time) * 1000)

            # 7. ACTUALIZAR ESTADO con resultado
            return self._update_state_with_result(state, result)

        except Exception as e:
            logger.error(f"Error in visual node {self.name}: {e}")
            self._emit_visual_end(state, success=False)
            return StateMutator.update_field(state, "error", str(e))

    def _emit_visual_start(self, state: GraphState):
        """Emite evento de inicio con metadata para efectos visuales."""
        asyncio.run(self.broadcaster.broadcast_agent_start(
            agent_name=self.name,
            session_id=state.session_id or "demo",
            action=self._get_visual_action(),
            meta={
                "visual_effect": "shimmer",
                "expected_duration": scale_duration(self.OPTIMAL_SHIMMER_TIME),
                "animation": "pulse",
                "color_transition": "orange_to_processing"
            }
        ))

    def _emit_visual_end(self, state: GraphState, success: bool, duration_ms: float):
        """Emite evento de fin con transición visual suave."""
        asyncio.run(self.broadcaster.broadcast_agent_end(
            agent_name=self.name,
            session_id=state.session_id or "demo",
            success=success,
            duration_ms=duration_ms,
            action=self._get_visual_action(),
            meta={
                "visual_effect": "fade_to_success" if success else "fade_to_error",
                "color_transition": "processing_to_cyan" if success else "processing_to_red",
                "animation": "complete"
            }
        ))

    def _process_with_visual_timing(self, state: GraphState) -> Dict[str, Any]:
        """
        Procesa con timing optimizado para impacto visual.
        Override este método en subclases.
        """
        # Simulación - Override en subclases reales
        workflow_sleep_sync(self.OPTIMAL_SHIMMER_TIME)
        return {"processed": True}

    def _get_visual_action(self) -> str:
        """Obtiene el tipo de acción con contexto visual."""
        action_map = {
<<<<<<< HEAD
            "summary": "analyzing_financials",
            "branch": "evaluating_performance",
            "anomaly": "detecting_patterns",
            "smalltalk": "conversing",
=======
            "capi_gus": "analyzing_financials",
            "branch": "evaluating_performance",
            "anomaly": "detecting_patterns",
            "capi_gus": "conversing",
>>>>>>> origin/develop
            "capi_datab": "querying_database",
            "capi_elcajas": "processing_transactions",
            "capi_desktop": "accessing_files"
        }

        for key, action in action_map.items():
            if key in self.name.lower():
                return action

        return "processing"

    def _get_processing_message(self) -> str:
        """Mensaje dramático durante procesamiento."""
        messages = {
<<<<<<< HEAD
            "summary": "Analizando métricas financieras complejas...",
=======
            "capi_gus": "Analizando métricas financieras complejas...",
>>>>>>> origin/develop
            "branch": "Evaluando rendimiento multi-dimensional...",
            "anomaly": "Aplicando algoritmos de detección avanzados...",
            "datab": "Consultando bases de datos distribuidas...",
            "elcajas": "Procesando transacciones en tiempo real...",
            "desktop": "Accediendo a recursos del sistema..."
        }

        for key, msg in messages.items():
            if key in self.name.lower():
                return msg

        return "Procesando información..."

    def _get_analyzing_message(self) -> str:
        """Mensaje dramático durante análisis."""
        messages = {
<<<<<<< HEAD
            "summary": "Generando insights ejecutivos...",
=======
            "capi_gus": "Generando insights amigables...",
>>>>>>> origin/develop
            "branch": "Calculando KPIs críticos...",
            "anomaly": "Identificando patrones ocultos...",
            "datab": "Optimizando consultas complejas...",
            "elcajas": "Validando integridad transaccional...",
            "desktop": "Compilando recursos encontrados..."
        }

        for key, msg in messages.items():
            if key in self.name.lower():
                return msg

        return "Finalizando análisis..."

    def _should_checkpoint(self) -> bool:
        """Decide si hacer checkpoint para efecto visual."""
        # Para competencia: SIEMPRE checkpoint para más drama
        return True

    def _needs_intermediate_checkpoint(self) -> bool:
        """Decide si necesita checkpoint intermedio."""
        # Para nodos que tardan más, agregar checkpoint intermedio
<<<<<<< HEAD
        heavy_nodes = ["summary", "anomaly", "datab"]
=======
        heavy_nodes = ["capi_gus", "anomaly", "datab"]
>>>>>>> origin/develop
        return any(node in self.name.lower() for node in heavy_nodes)

    def _update_state_with_result(self, state: GraphState, result: Dict[str, Any]) -> GraphState:
        """Actualiza el estado con el resultado del procesamiento."""
        state = StateMutator.update_field(state, "last_result", result)
        state = StateMutator.append_to_list(state, "completed_nodes", self.name)
        return state


<<<<<<< HEAD
class VisualSummaryNode(VisualOptimizedNode):
    """Nodo de resumen con máximo impacto visual."""

    def __init__(self):
        super().__init__(name="summary_visual")
=======
class VisualCapiGusNode(VisualOptimizedNode):
    """Nodo de respuesta conversacional con máximo impacto visual."""

    def __init__(self):
        super().__init__(name="capi_gus_visual")
>>>>>>> origin/develop
        self.MIN_PROCESSING_TIME = 2.5  # Más tiempo para este nodo importante

    def _process_with_visual_timing(self, state: GraphState) -> Dict[str, Any]:
        """Procesa resumen con timing visual óptimo."""
        # Simular procesamiento por pasos para efecto visual
        steps = [
            ("Accediendo a datos históricos", 0.5),
            ("Calculando métricas principales", 0.7),
            ("Analizando tendencias", 0.6),
            ("Generando visualizaciones", 0.7)
        ]

        for step_name, duration in steps:
            logger.info(f"Visual step: {step_name}")
            workflow_sleep_sync(duration)

        return {
<<<<<<< HEAD
            "summary": {
=======
            "capi_gus": {
>>>>>>> origin/develop
                "total_revenue": 1500000,
                "growth": "+15.3%",
                "top_branch": "SUC-404",
                "visual_impact": "maximum"
            }
        }


class VisualBranchNode(VisualOptimizedNode):
    """Nodo de análisis de sucursal con impacto visual."""

    def __init__(self):
        super().__init__(name="branch_visual")
        self.MIN_PROCESSING_TIME = 2.0

    def _process_with_visual_timing(self, state: GraphState) -> Dict[str, Any]:
        """Procesa análisis de sucursal con timing visual."""
        # Timing optimizado para shimmer perfecto
        workflow_sleep_sync(self.OPTIMAL_SHIMMER_TIME)

        return {
            "branch_analysis": {
                "performance": "Excepcional",
                "ranking": "#1",
                "metrics": {
                    "efficiency": 94.5,
                    "satisfaction": 98.2,
                    "growth": 15.3
                }
            }
        }


class VisualAnomalyNode(VisualOptimizedNode):
    """Nodo de detección de anomalías con drama visual."""

    def __init__(self):
        super().__init__(name="anomaly_visual")
        self.MIN_PROCESSING_TIME = 3.0  # Más tiempo para crear suspenso

    def _process_with_visual_timing(self, state: GraphState) -> Dict[str, Any]:
        """Detecta anomalías con máximo drama visual."""
        # Crear suspenso con pasos dramáticos
        dramatic_steps = [
            ("Escaneando transacciones", 0.8),
            ("Aplicando machine learning", 1.0),
            ("Analizando patrones", 0.7),
            ("Validando resultados", 0.5)
        ]

        for step, duration in dramatic_steps:
            logger.info(f"Dramatic step: {step}")
            workflow_sleep_sync(duration)

        return {
            "anomalies": {
                "detected": 0,
                "status": "Sistema seguro",
                "confidence": 99.8,
                "visual_effect": "success_pulse"
            }
<<<<<<< HEAD
        }
=======
        }
>>>>>>> origin/develop
