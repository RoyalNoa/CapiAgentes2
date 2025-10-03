"""
Ruta: Backend/src/infrastructure/langgraph/nodes/smalltalk_node.py
Descripción: Nodo para manejar saludos y conversación casual sin LLM
Estado: Activo
Autor/Responsable: migration-bot
Última actualización: 2025-01-14
Tareas relacionadas: T-003
Referencias: AI/Tablero/LangGraph/InfoAdicional.md#registro-de-avances
"""
from __future__ import annotations

import random
from src.infrastructure.langgraph.nodes.base import GraphNode
from src.infrastructure.langgraph.state_schema import GraphState, StateMutator
from src.core.logging import get_logger

logger = get_logger(__name__)


class SmalltalkNode(GraphNode):
    def __init__(self, name: str = "smalltalk") -> None:
        super().__init__(name=name)
        # EXPERT INTEGRATION: Mark this as an agent node for WebSocket events
        self._is_agent_node = True

        # Predefined courteous responses in Spanish
        self.greeting_responses = [
            "¡Hola! Soy tu asistente de análisis financiero. ¿En qué puedo ayudarte hoy?",
            "¡Buen día! Estoy aquí para ayudarte con análisis de datos financieros.",
            "¡Hola! ¿Necesitas algún análisis financiero, resumen de datos o detección de anomalías?",
            "¡Saludos! Puedo ayudarte con resúmenes financieros, análisis por sucursal y detección de irregularidades.",
        ]

        self.smalltalk_responses = [
            "Gracias por preguntar. Mi especialidad es el análisis financiero. ¿Te gustaría que prepare un resumen de tus datos?",
            "¡De nada! Estoy aquí para ayudar con análisis financieros. ¿Qué tipo de información necesitas?",
            "Me alegra poder ayudarte. ¿Prefieres un resumen general o análisis específico por sucursales?",
            "Perfecto, ¿en qué análisis financiero te puedo asistir? Puedo hacer resúmenes, detectar anomalías o analizar sucursales.",
        ]

    def run(self, state: GraphState) -> GraphState:
        import time
        start_time = time.time()

        logger.info({"event": "smalltalk_node_start", "node": self.name})

        # EXPERT INTEGRATION: Emit WebSocket agent start event
        self._emit_agent_start(state)

        # Determine response based on intent or query content
        response = self._generate_response(state)

        # Update state with response
        s = StateMutator.update_field(state, "current_node", self.name)
        s = StateMutator.update_field(s, "response_message", response)
        s = StateMutator.append_to_list(s, "completed_nodes", self.name)
        s = StateMutator.merge_dict(
            s,
            "response_metadata",
            {
                "agent_type": "smalltalk",
                "response_source": "predefined_templates",
                "requires_llm": False,
            },
        )

        # Calculate execution time
        duration_ms = (time.time() - start_time) * 1000

        logger.info(
            {
                "event": "smalltalk_node_end",
                "response_length": len(response),
                "response_preview": response[:50] + "..." if len(response) > 50 else response,
                "duration_ms": duration_ms
            }
        )

        # EXPERT INTEGRATION: Emit WebSocket agent end event
        self._emit_agent_end(state, success=True, duration_ms=duration_ms)

        return s

    def _generate_response(self, state: GraphState) -> str:
        """
        Generate appropriate smalltalk response based on state.

        Args:
            state: Current graph state

        Returns:
            Appropriate courteous response in Spanish
        """
        query = (state.original_query or "").lower()

        # Check for greeting patterns
        greeting_words = ["hola", "hello", "buenas", "saludos", "buenos días", "buenas tardes"]
        if any(word in query for word in greeting_words):
            return random.choice(self.greeting_responses)

        # Check for thanks/smalltalk patterns
        thanks_words = ["gracias", "thank", "bien", "ok", "perfecto", "excelente"]
        if any(word in query for word in thanks_words):
            return random.choice(self.smalltalk_responses)

        # Default friendly response
        return random.choice(self.greeting_responses)