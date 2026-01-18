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

from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional

from src.infrastructure.langgraph.nodes.base import GraphNode
from src.infrastructure.langgraph.state_schema import GraphState, StateMutator, WorkflowStatus
from src.core.logging import get_logger

logger = get_logger(__name__)


class AssembleNode(GraphNode):
    def __init__(self, name: str = "assemble") -> None:
        super().__init__(name=name)

    def run(self, state: GraphState) -> GraphState:
        logger.info({"event": "assemble_node_start", "node": self.name})

        # Try to build an aggregate message for global branch summaries if needed
        response_message = None
        global_summary_message = self._maybe_build_global_summary(state)
        if global_summary_message:
            response_message = global_summary_message

        # Ensure we have a response message
        response_message = state.response_message
        fallback_used = False
        if global_summary_message:
            response_message = global_summary_message

        if not response_message:
            response_message = self._generate_fallback_response(state)
            fallback_used = True

        # Finalize response data and metadata
        response_data = dict(state.response_data) if state.response_data else {}
        if global_summary_message:
            response_data["response"] = global_summary_message
            response_data["summary_message"] = global_summary_message
        response_metadata = dict(state.response_metadata) if state.response_metadata else {}
        if global_summary_message:
            response_metadata.update(
                {
                    "summary_message": global_summary_message,
                    "result_summary": global_summary_message,
                    "agent_raw_message": global_summary_message,
                    "agent": "capi_gus",
                }
            )

        # Add assembly metadata
        response_metadata.update({
            "assembled_at": "assemble",
            "workflow_completed": True,
            "total_nodes": len(state.completed_nodes) + 1,  # +1 for current node
        })
        if fallback_used:
            response_metadata.setdefault("active_agent", "capi_gus")
            response_metadata.setdefault("workflow_stage", "capi_gus_fallback")
            response_metadata.setdefault("capi_gus_fallback", True)

        # Update state
        s = StateMutator.update_field(state, "current_node", self.name)
        s = StateMutator.update_field(s, "response_message", response_message)
        s = StateMutator.update_field(s, "response_data", response_data)
        s = StateMutator.update_field(s, "response_metadata", response_metadata)
        if fallback_used:
            s = StateMutator.update_field(s, "active_agent", "capi_gus")
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

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _maybe_build_global_summary(self, state: GraphState) -> Optional[str]:
        """
        Detects if the workflow produced a global branch summary and formats it
        into an executive response message.
        """
        shared = getattr(state, "shared_artifacts", {}) or {}
        if not isinstance(shared, dict):
            return None

        elcajas_bucket = shared.get("capi_elcajas")
        if not isinstance(elcajas_bucket, dict):
            return None

        global_summary = elcajas_bucket.get("global_summary")
        if not isinstance(global_summary, dict):
            return None

        analysis_scope = (
            elcajas_bucket.get("analysis_scope")
            or shared.get("capi_datab", {}).get("analysis_scope")
            or (getattr(state, "response_metadata", {}) or {}).get("analysis_scope")
        )
        if str(analysis_scope or "").lower() != "all_branches":
            return None

        return self._format_global_summary_message(global_summary)

    def _format_global_summary_message(self, summary: Dict[str, Any]) -> str:
        total_branches = int(summary.get("total_branches") or 0)
        policy = summary.get("policy") or {}

        tolerance_pct: Optional[Decimal] = None
        for key in ("max_surplus_pct", "max_deficit_pct"):
            value = policy.get(key)
            if value is None:
                continue
            try:
                numeric = abs(Decimal(str(value)))
            except (InvalidOperation, TypeError, ValueError):
                continue
            tolerance_pct = max(tolerance_pct or Decimal("0"), numeric)

        if total_branches > 0:
            if tolerance_pct and tolerance_pct > 0:
                tolerance_value = tolerance_pct * Decimal("100")
                tolerance_str = (
                    f"{int(tolerance_value)}%"
                    if tolerance_value == tolerance_value.to_integral()
                    else f"{tolerance_value.quantize(Decimal('0.1'))}%"
                )
                first_sentence = (
                    f"Analicé {total_branches} sucursales contra la franja tolerable del canal Saldo Total ({tolerance_str})."
                )
            else:
                first_sentence = f"Analicé {total_branches} sucursales."
        else:
            first_sentence = "Analicé las sucursales disponibles."

        surplus_info = summary.get("surplus") or {}
        deficit_info = summary.get("deficit") or {}

        surplus_count = int(surplus_info.get("branches") or 0)
        deficit_count = int(deficit_info.get("branches") or 0)

        if surplus_count > 0:
            surplus_sentence = f"{surplus_count} muestran excedentes fuera de tolerancia"
        else:
            surplus_sentence = "Ninguna muestra excedentes fuera de tolerancia"

        if deficit_count > 0:
            deficit_sentence = f"{deficit_count} registran faltantes"
        else:
            deficit_sentence = "ninguna registra faltantes"

        second_sentence = f"{surplus_sentence} y {deficit_sentence}."

        action_phrases = []
        surplus_amount = self._to_decimal(surplus_info.get("amount"))
        deficit_amount = self._to_decimal(deficit_info.get("amount"))

        if deficit_amount and deficit_amount > 0:
            action_phrases.append(f"depositar un total de {self._format_currency(deficit_amount)}")
        if surplus_amount and surplus_amount > 0:
            action_phrases.append(f"retirar un total de {self._format_currency(surplus_amount)}")

        if action_phrases:
            if len(action_phrases) == 2:
                action_sentence = f"Para equilibrarlas se necesita {action_phrases[0]} y {action_phrases[1]}."
            else:
                action_sentence = f"Para equilibrarlas se necesita {action_phrases[0]}."
        else:
            action_sentence = "Por ahora no se requieren movimientos adicionales."

        closing_question = "¿Querés la información más detallada en un Excel?"

        message = " ".join(
            sentence.strip()
            for sentence in (first_sentence, second_sentence, action_sentence, closing_question)
            if sentence
        ).strip()
        return message

    def _to_decimal(self, value: Any) -> Optional[Decimal]:
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return None

    def _format_currency(self, amount: Decimal) -> str:
        quantized = amount.quantize(Decimal("0.01"))
        formatted = f"{quantized:,.2f}"
        # Convert to Spanish locale style: thousands '.' and decimals ','
        formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"${formatted}"

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
        brand_voice = "Capi Gus"
        if state.detected_intent:
            intent_name = getattr(state.detected_intent, "value", str(state.detected_intent))
            confidence = state.intent_confidence or 0.0

            if confidence < 0.3:
                return (
                    f"{brand_voice} todavía no está del todo seguro de cómo ayudarte con '{query}'. "
                    "¿Podés darme un poco más de contexto? Tengo a mano resúmenes financieros, análisis de sucursales "
                    "y detección de anomalías."
                )
            else:
                return (
                    f"{brand_voice} revisó tu consulta sobre '{query}' (intención: {intent_name}), "
                    "pero no encontré una respuesta puntual en mis tableros. "
                    "¿Querés reformular la pregunta o darme algún dato extra?"
                )

        # Generic fallback
        return (
            f"Capi Gus recibió tu consulta: '{query}'. "
            "Estoy listo para ayudarte con análisis financieros, resúmenes, detección de anomalías o métricas de sucursales. "
            "Contame un poco más así avanzamos."
        )
