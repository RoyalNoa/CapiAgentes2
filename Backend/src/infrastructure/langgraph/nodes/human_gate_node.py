"""
HumanGateNode: Pausa el flujo hasta obtener aprobacion humana cuando una operaciÃƒÂ³n sensible lo requiere.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from langgraph.types import Command, interrupt

from src.infrastructure.langgraph.nodes.base import GraphNode
from src.infrastructure.langgraph.state_schema import GraphState, StateMutator, WorkflowStatus
from src.core.logging import get_logger

logger = get_logger(__name__)


class HumanGateNode(GraphNode):
    def __init__(self, name: str = "human_gate") -> None:
        super().__init__(name=name)
        self._is_agent_node = False

    def run(self, state: GraphState) -> GraphState:
        logger.debug({"event": "human_gate_start", "session_id": state.session_id})
        requires_review, context = self._needs_human_review(state)
        updated = StateMutator.update_field(state, "current_node", self.name)

        if not requires_review:
            return StateMutator.append_to_list(updated, "completed_nodes", self.name)

        decision: Optional[Dict[str, Any]] = self._extract_decision(state)
        if decision is None:
            updated = self._prepare_pending_response(updated, context)
            logger.info({
                "event": "human_gate_interrupt",
                "session_id": state.session_id,
                "trace_id": state.trace_id,
                "reason": context.get("reason"),
            })
            decision = interrupt(
                {
                    "node": self.name,
                    "session_id": state.session_id,
                    "trace_id": state.trace_id,
                    "context": context,
                }
            )

        approved = bool(decision.get("approved", False))
        metadata_updates = {
            "human_decision": decision,
            "human_approved": approved,
            "human_gate_pending": False,
        }
        updated = StateMutator.merge_dict(updated, "response_metadata", metadata_updates)
        updated = StateMutator.append_to_list(updated, "completed_nodes", self.name)

        if approved:
            logger.info({
                "event": "human_gate_approved",
                "session_id": state.session_id,
                "trace_id": state.trace_id,
            })
            return updated

        logger.info({
            "event": "human_gate_rejected",
            "session_id": state.session_id,
            "trace_id": state.trace_id,
        })
        updated = StateMutator.update_field(
            updated,
            "status",
            WorkflowStatus.PAUSED,
        )
        rejection_message = self._build_rejection_message(decision, context)
        updated = StateMutator.update_field(updated, "response_message", rejection_message)
        updated = StateMutator.merge_dict(
            updated,
            "response_metadata",
            {"human_blocked": True},
        )
        return updated

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _needs_human_review(self, state: GraphState) -> tuple[bool, Dict[str, Any]]:
        metadata = state.response_metadata or {}
        semantic_action = metadata.get("semantic_action")
        requires_flag = metadata.get("requires_human_approval")
        sensitive = semantic_action in {"WRITE_FILE", "MODIFY_FILE", "DELETE"}
        requires_review = bool(requires_flag or sensitive)
        context = {
            "reason": metadata.get("approval_reason")
            or "Se requiere aprobacion antes de ejecutar operaciones de escritura.",
            "semantic_action": semantic_action,
            "metadata": {k: v for k, v in metadata.items() if k not in {"human_decision"}},
        }
        return requires_review, context

    def _extract_decision(self, state: GraphState) -> Optional[Dict[str, Any]]:
        metadata = state.response_metadata or {}
        decision = metadata.get("human_decision")
        if isinstance(decision, dict):
            return decision
        return None

    def _prepare_pending_response(self, state: GraphState, context: Dict[str, Any]) -> GraphState:
        metadata = context.get("metadata") or {}
        message = self._build_pending_message(metadata, context)
        updated = StateMutator.update_field(state, "response_message", message)
        pending_metadata = {
            "human_gate_pending": True,
            "human_gate_reason": context.get("reason"),
            "human_gate_context": metadata,
        }
        updated = StateMutator.merge_dict(updated, "response_metadata", pending_metadata)
        return updated

    def _build_pending_message(self, metadata: Dict[str, Any], context: Dict[str, Any]) -> str:
        # Try to tailor the message according to the agent/operation involved.
        agente_g_operation = metadata.get("agente_g_operation")
        if agente_g_operation == "send_gmail":
            recipient_hint = ""
            recipients = metadata.get("agente_g_parameters") or metadata.get("parameters") or {}
            to = recipients.get("to")
            if isinstance(to, list) and to:
                recipient_hint = f" para {', '.join(to)}"
            return (
                "Capi Gus te avisa: necesito tu aprobación antes de enviar el correo"
                f"{recipient_hint}. ¿Confirmás que lo envíe?"
            )
        if agente_g_operation == "create_drive_text":
            return (
                "Capi Gus te recuerda que esta acción creará un archivo en tu Drive. "
                "¿Querés continuar?"
            )
        if agente_g_operation == "create_calendar_event":
            return (
                "Capi Gus detectó que voy a agendar un evento en tu calendario. "
                "Confirmame si debo programarlo."
            )
        semantic_action = context.get("semantic_action")
        if semantic_action == "WRITE_FILE":
            return (
                "Capi Gus espera tu confirmación para modificar archivos. "
                "¿Seguimos adelante?"
            )
        if semantic_action == "DELETE":
            return (
                "Antes de borrar nada, necesito tu aprobación explícita. "
                "¿Deseás continuar?"
            )
        reason = context.get("reason") or "La acción solicitada requiere revisión humana."
        return f"Capi Gus te pide confirmación: {reason}"

    def _build_rejection_message(self, decision: Dict[str, Any], context: Dict[str, Any]) -> str:
        if isinstance(decision, dict):
            custom = decision.get("message")
            if custom:
                return custom
        metadata = context.get("metadata") or {}
        agente_g_operation = metadata.get("agente_g_operation")
        if agente_g_operation == "send_gmail":
            return "Capi Gus canceló el envío del correo hasta que lo vuelvas a solicitar."
        if agente_g_operation == "create_drive_text":
            return "Capi Gus detuvo la creación del archivo en Drive. Podés intentarlo cuando quieras."
        if agente_g_operation == "create_calendar_event":
            return "Capi Gus no agendó el evento. Avisame si querés que lo programe más tarde."
        semantic_action = context.get("semantic_action")
        if semantic_action == "WRITE_FILE":
            return "Capi Gus dejó en pausa la escritura del archivo. Confirmame cuando quieras continuar."
        if semantic_action == "DELETE":
            return "Capi Gus detuvo el borrado solicitado. Avisame si preferís eliminarlo luego."
        reason = context.get("reason") or "la acción requiere tu aprobación."
        return f"Capi Gus pausó la acción porque {reason}"
