"""
Ruta: Backend/src/infrastructure/langgraph/nodes/assemble_node.py
Descripción: Nodo de ensamblaje final para preparar respuestas coherentes
Estado: Activo
Autor/Responsable: migration-bot
Última actualización: 2025-01-14
Tareas relacionadas: T-007
Referencias: AI/Tablero/LangGraph/InfoAdicional.md#registro-de-avances
"""
from __future__ import annotations

from src.infrastructure.langgraph.nodes.base import GraphNode
from src.infrastructure.langgraph.state_schema import GraphState, StateMutator, WorkflowStatus
from src.core.logging import get_logger

logger = get_logger(__name__)


class AssembleNode(GraphNode):
    def __init__(self, name: str = "assemble") -> None:
        super().__init__(name=name)

    def run(self, state: GraphState) -> GraphState:
        logger.info({"event": "assemble_node_start", "node": self.name})

        # Ensure we have a response message
        response_message = state.response_message
        if not response_message:
            response_message = self._generate_fallback_response(state)

        # Finalize response data and metadata
        response_data = dict(state.response_data) if state.response_data else {}
        response_metadata = dict(state.response_metadata) if state.response_metadata else {}

        # Add assembly metadata
        response_metadata.update({
            "assembled_at": "assemble",
            "workflow_completed": True,
            "total_nodes": len(state.completed_nodes) + 1,  # +1 for current node
        })

        # Update state
        s = StateMutator.update_field(state, "current_node", self.name)
        s = StateMutator.update_field(s, "response_message", response_message)
        s = StateMutator.update_field(s, "response_data", response_data)
        s = StateMutator.update_field(s, "response_metadata", response_metadata)
        s = StateMutator.append_to_list(s, "completed_nodes", self.name)

        logger.info(
            {
                "event": "assemble_node_end",
                "response_length": len(response_message),
                "data_keys": list(response_data.keys()),
                "metadata_keys": list(response_metadata.keys()),
            }
        )

        return s

    def _generate_fallback_response(self, state: GraphState) -> str:
        """
        Generate fallback response when no other node provided one.

        Args:
            state: Current graph state

        Returns:
            Fallback response message
        """
        query = state.original_query or "consulta"

        # Check if we detected an intent
        if state.detected_intent:
            intent_name = getattr(state.detected_intent, "value", str(state.detected_intent))
            confidence = state.intent_confidence or 0.0

            if confidence < 0.3:
                return f"🤔 No estoy seguro de cómo ayudarte con '{query}'. ¿Podrías ser más específico? Puedo ayudarte con resúmenes financieros, análisis de sucursales o detección de anomalías."
            else:
                return f"📋 He procesado tu consulta sobre '{query}' (intención: {intent_name}), pero no pude generar una respuesta específica. ¿Podrías reformular la pregunta?"

        # Generic fallback
        return f"🤖 He recibido tu consulta: '{query}'. Puedo ayudarte con análisis financieros, resúmenes de datos, detección de anomalías y análisis por sucursales. ¿Qué te gustaría hacer?"