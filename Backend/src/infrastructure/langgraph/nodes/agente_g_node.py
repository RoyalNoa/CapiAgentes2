"""LangGraph node for Agente G (Google Workspace assistant)."""
from __future__ import annotations

import time
from typing import Any, Dict, Optional

from src.domain.agents.agent_models import AgentResult, IntentType, TaskStatus
from src.domain.agents.agent_protocol import AgentTask
from src.infrastructure.langgraph.nodes.base import GraphNode
from src.infrastructure.langgraph.state_schema import GraphState, StateMutator
from src.infrastructure.external.google import (
    GoogleOAuthSettings,
    GoogleCredentialsManager,
    GoogleServiceFactory,
    GmailClient,
    DriveClient,
    CalendarClient,
)
from importlib import import_module

from src.core.logging import get_logger

logger = get_logger(__name__)


class AgenteGNode(GraphNode):
    """Executes operations in Gmail, Drive and Calendar via Agente G handler."""

    def __init__(self, name: str = "agente_g") -> None:
        super().__init__(name=name)
        self._is_agent_node = True
        self._agent, self._agent_error = self._initialize_agent()

    def run(self, state: GraphState) -> GraphState:
        self._emit_agent_start(state)
        updated = StateMutator.update_field(state, "current_node", self.name)

        if self._agent is None:
            error_message = "Agente G no esta configurado: {}".format(self._agent_error or "credenciales faltantes")
            updated = StateMutator.add_error(updated, "agente_g_not_configured", error_message)
            updated = StateMutator.update_field(updated, "response_message", error_message)
            updated = StateMutator.append_to_list(updated, "completed_nodes", self.name)
            self._emit_agent_end(updated, success=False)
            return updated

        instruction = self._extract_instruction(state)
        if not instruction:
            message = (
                "Necesito una instruccion para Agente G (ej. listar correos, enviar correo, listar drive, crear evento)."
            )
            updated = StateMutator.update_field(updated, "response_message", message)
            updated = StateMutator.add_error(updated, "agente_g_missing_instruction", message)
            updated = StateMutator.append_to_list(updated, "completed_nodes", self.name)
            self._emit_agent_end(updated, success=False)
            return updated

        try:
            result = self._execute_agent(state, instruction)
        except Exception as exc:
            logger.exception("agente_g_node_execution_failed", extra={"session_id": state.session_id})
            message = f"Agente G fallo al ejecutar la accion: {exc}"
            updated = StateMutator.update_field(updated, "response_message", message)
            updated = StateMutator.add_error(updated, "agente_g_failure", message)
            updated = StateMutator.append_to_list(updated, "completed_nodes", self.name)
            self._emit_agent_end(updated, success=False)
            return updated

        updated = StateMutator.update_field(updated, "response_message", result.message)
        updated = StateMutator.merge_dict(updated, "response_data", result.data)

        meta_update = {
            "agente_g_operation": instruction.get("operation"),
            "agente_g_parameters": instruction.get("parameters"),
            "google_identity": getattr(self._agent, "agent_email", None),
        }
        if instruction.get("operation") in {
            "send_gmail",
            "create_drive_text",
            "create_calendar_event",
            "enable_gmail_push",
            "disable_gmail_push",
        }:
            meta_update.setdefault("requires_human_approval", True)
            meta_update.setdefault("approval_reason", "Agente G requiere confirmacion para acciones sensibles")
        metrics = result.data.get("metrics")
        if metrics:
            meta_update.setdefault("google_metrics", metrics)

        updated = StateMutator.merge_dict(updated, "response_metadata", meta_update)

        artifact = result.data.get("artifact")
        if artifact:
            shared = dict(updated.shared_artifacts or {})
            artifacts = list(shared.get(self.name, []))
            artifacts.append(artifact)
            shared[self.name] = artifacts
            updated = StateMutator.update_field(updated, "shared_artifacts", shared)

        updated = StateMutator.append_to_list(updated, "completed_nodes", self.name)
        self._emit_agent_end(updated, success=True)
        return updated

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _initialize_agent(self):
        try:
            module = import_module('agentes.agente_g.handler')
            AgenteGAgent = getattr(module, 'AgenteGAgent')
            settings = GoogleOAuthSettings.load_from_env()
            manager = GoogleCredentialsManager(settings)
            factory = GoogleServiceFactory(manager)
            gmail_client = GmailClient(factory, user_id=settings.agent_email or "me")
            drive_client = DriveClient(factory)
            calendar_client = CalendarClient(factory, calendar_id="primary")
            agent = AgenteGAgent(
                gmail_client=gmail_client,
                drive_client=drive_client,
                calendar_client=calendar_client,
            )
            return agent, None
        except Exception as exc:
            logger.error({"event": "agente_g_init_failed", "error": str(exc)})
            return None, exc

    def _extract_instruction(self, state: GraphState) -> Optional[Dict[str, Any]]:
        metadata = state.response_metadata or {}
        instruction = metadata.get("agente_g_instruction")
        if isinstance(instruction, dict) and instruction.get("operation"):
            return instruction

        # Fallback heuristics from original query
        query = (state.original_query or "").lower()
        if "listar" in query and ("correo" in query or "email" in query):
            return {"operation": "list_gmail", "parameters": {"query": "is:unread"}}
        if "listar" in query and "drive" in query:
            return {"operation": "list_drive", "parameters": {}}
        if "crear" in query and "evento" in query:
            return {
                "operation": "create_calendar_event",
                "parameters": {"summary": "Evento Agente G", "start": "", "end": ""},
            }
        return None

    def _execute_agent(self, state: GraphState, instruction: Dict[str, Any]) -> AgentResult:
        operation = instruction.get("operation")
        parameters = instruction.get("parameters") or {}
        intent = instruction.get("intent") or IntentType.QUERY.value
        task = AgentTask(
            task_id=f"{state.session_id}_{self.name}_{int(time.time()*1000)}",
            intent=intent,
            query=state.original_query or "",
            user_id=state.user_id,
            session_id=state.session_id,
            context={
                "trace_id": state.trace_id,
                "metadata": state.response_metadata,
            },
            metadata={
                "operation": operation,
                "parameters": parameters,
            },
        )
        result = self._agent.process(task)
        if result.status != TaskStatus.COMPLETED:
            raise RuntimeError(result.message or "Agente G devolvio un estado fallido")
        return result


__all__ = ["AgenteGNode"]
