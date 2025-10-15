"""LangGraph node for Agente G (Google Workspace assistant)."""
from __future__ import annotations

import os
import re
import sys
import time
from typing import Any, Dict, Iterable, Optional

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


def _ensure_paths() -> None:
    """Make sure Backend/src and Backend/ia_workspace are importable."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_src_path = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
    backend_root = os.path.abspath(os.path.join(backend_src_path, ".."))
    ia_workspace_path = os.path.join(backend_root, "ia_workspace")

    for path in (backend_src_path, ia_workspace_path):
        if path not in sys.path:
            sys.path.insert(0, path)


_ensure_paths()


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
        if instruction:
            logger.info(
                {
                    "event": "email_trace",
                    "stage": "agente_g_instruction_extracted",
                    "operation": instruction.get("operation"),
                    "parameters": instruction.get("parameters"),
                }
            )
        if not instruction:
            message = (
                "Necesito una instruccion para Agente G (ej. listar correos, enviar correo, listar drive, crear evento)."
            )
            updated = StateMutator.update_field(updated, "response_message", message)
            updated = StateMutator.add_error(updated, "agente_g_missing_instruction", message)
            updated = StateMutator.append_to_list(updated, "completed_nodes", self.name)
            self._emit_agent_end(updated, success=False)
            return updated

        validation_ok, validation_message, validation_meta = self._validate_instruction(instruction)
        if not validation_ok:
            validation_meta = validation_meta or {}
            validation_meta.setdefault("agente_g_operation", instruction.get("operation"))
            validation_meta.setdefault("agente_g_parameters", instruction.get("parameters"))
            validation_meta.setdefault("requires_clarification", True)
            logger.info(
                {
                    "event": "email_trace",
                    "stage": "agente_g_validation_failed",
                    "message": validation_message,
                    "metadata": validation_meta,
                }
            )
            updated = StateMutator.update_field(updated, "response_message", validation_message)
            updated = StateMutator.merge_dict(updated, "response_metadata", validation_meta)
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

        send_parameters = instruction.get("parameters") or {}
        operation = instruction.get("operation")
        meta_update = {
            "agente_g_operation": operation,
            "agente_g_parameters": send_parameters,
            "google_identity": getattr(self._agent, "agent_email", None),
            "loop_fallback": "assemble",
            "react_follow_up": False,
            "reasoning_needs_react": False,
            "needs_retry": None,
        }
        sensitive_ops = {
            "create_drive_text",
            "create_calendar_event",
            "enable_gmail_push",
            "disable_gmail_push",
        }
        if operation in sensitive_ops:
            meta_update["requires_human_approval"] = True
            meta_update.setdefault("approval_reason", "Agente G requiere confirmacion para acciones sensibles")
        else:
            meta_update["requires_human_approval"] = False

        response_payload = dict(result.data or {})

        def _ensure_response_fields(payload: Dict[str, Any], message_value: str) -> None:
            if payload.get("response"):
                return
            nested = payload.get("result")
            candidate = None
            if isinstance(nested, dict):
                candidate = nested.get("response") or nested.get("message") or nested.get("summary")
                if candidate:
                    payload.setdefault("summary_message", nested.get("summary_message") or nested.get("summary"))
                    if nested.get("shared_artifacts") and not payload.get("shared_artifacts"):
                        payload["shared_artifacts"] = nested["shared_artifacts"]
            payload["response"] = candidate or message_value

        metrics = response_payload.get("metrics")
        if metrics:
            meta_update.setdefault("google_metrics", metrics)

        if operation == "send_gmail":
            final_message = self._format_capi_gus_confirmation(send_parameters)
            updated = StateMutator.update_field(updated, "response_message", final_message)
            updated = StateMutator.update_field(updated, "active_agent", "capi_gus")
            meta_update["active_agent"] = "capi_gus"
            meta_update["workflow_stage"] = "capi_gus_followup"
            meta_update["capi_gus_confirmation_message"] = final_message
            _ensure_response_fields(response_payload, final_message)
        else:
            updated = StateMutator.update_field(updated, "response_message", result.message)
            _ensure_response_fields(response_payload, result.message)

        response_payload.setdefault("operation", operation)
        response_payload.setdefault("parameters", send_parameters)

        updated = StateMutator.merge_dict(updated, "response_data", response_payload)
        updated = StateMutator.merge_dict(updated, "response_metadata", meta_update)

        artifact = response_payload.get("artifact")
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
        if self._is_valid_instruction(instruction):
            return instruction

        semantic_result = metadata.get("semantic_result") or {}
        semantic_instruction = self._instruction_from_semantic(semantic_result, state.original_query or "")
        if semantic_instruction:
            return semantic_instruction

        query = state.original_query or ""
        query_instruction = self._instruction_from_query(query)
        if query_instruction:
            return query_instruction

        return None

    @staticmethod
    def _is_valid_instruction(candidate: Any) -> bool:
        return isinstance(candidate, dict) and bool(candidate.get("operation"))

    def _instruction_from_semantic(self, semantic: Dict[str, Any], query: str) -> Optional[Dict[str, Any]]:
        if not isinstance(semantic, dict):
            return None
        entities = semantic.get("entities") or {}
        if not isinstance(entities, dict):
            entities = {}

        gmail_operation = entities.get("gmail_operation")
        drive_operation = entities.get("drive_operation")
        calendar_operation = entities.get("calendar_operation")

        if gmail_operation:
            return self._build_gmail_instruction(gmail_operation, entities, query)
        if drive_operation:
            return self._build_drive_instruction(drive_operation, entities)
        if calendar_operation:
            return self._build_calendar_instruction(calendar_operation, entities)
        if semantic.get("intent") in {"google_workspace", "google_gmail", "google_drive", "google_calendar"}:
            # Default to Gmail listing if no explicit entity is present.
            return {
                "operation": "list_gmail",
                "parameters": {"query": entities.get("gmail_query") or "is:unread"},
            }
        return None

    def _instruction_from_query(self, query: str) -> Optional[Dict[str, Any]]:
        query_lower = (query or "").lower()
        if not query_lower:
            return None

        email_tokens = ("correo", "correos", "mail", "mails", "gmail", "email")
        if ("enviar" in query_lower or "envia" in query_lower or "enviá" in query_lower or "mandar" in query_lower or "responder" in query_lower) and any(
            token in query_lower for token in email_tokens
        ):
            recipients = self._extract_emails(query)
            subject = self._extract_slot(query, ("asunto", "subject"))
            body = self._extract_slot(query, ("mensaje", "cuerpo", "body"))
            parameters: Dict[str, Any] = {"compose_context": query}
            if recipients:
                parameters["to"] = recipients
            else:
                parameters["to"] = []
            if subject:
                parameters["subject"] = subject
            if body:
                parameters["body"] = body
            elif query.strip():
                parameters["body"] = query.strip()
            return {"operation": "send_gmail", "parameters": parameters}

        if any(token in query_lower for token in email_tokens):
            list_keywords = ("listar", "ver", "mostrar", "consultar", "revisar", "chequear", "saber")
            unread_markers = ("no leido", "no leído", "sin leer", "nuev", "lleg", "recient")
            wants_list = any(keyword in query_lower for keyword in list_keywords) or "cuanto" in query_lower
            wants_unread = any(marker in query_lower for marker in unread_markers)
            if wants_list or wants_unread:
                params: Dict[str, Any] = {}
                if wants_unread or "nuevo" in query_lower or "nueva" in query_lower or "nuevos" in query_lower or "nuevas" in query_lower:
                    params["query"] = "is:unread"
                return {"operation": "list_gmail", "parameters": params}

        if "listar" in query_lower and "drive" in query_lower:
            drive_query = self._extract_slot(query, ("filtro", "query", "busca"))
            params: Dict[str, Any] = {}
            if drive_query:
                params["query"] = drive_query
            return {"operation": "list_drive", "parameters": params}

        if ("crear" in query_lower or "generar" in query_lower) and "drive" in query_lower:
            name = self._extract_slot(query, ("archivo", "documento", "nombre"))
            content = self._extract_slot(query, ("contenido", "texto", "body"))
            params = {"name": name or "agente-g-nota.txt"}
            if content:
                params["content"] = content
            else:
                params["content"] = ""
            return {"operation": "create_drive_text", "parameters": params}

        if ("evento" in query_lower or "reunion" in query_lower or "reunión" in query_lower) and (
            "crear" in query_lower or "agendar" in query_lower
        ):
            summary = self._extract_slot(query, ("evento", "reunion", "titulo", "title")) or "Evento Agente G"
            params = {"summary": summary, "start": "", "end": ""}
            return {"operation": "create_calendar_event", "parameters": params}

        if "estado" in query_lower and "push" in query_lower and "gmail" in query_lower:
            return {"operation": "get_gmail_push_status", "parameters": {}}

        return None

    def _build_gmail_instruction(self, operation_key: Any, entities: Dict[str, Any], query: str) -> Optional[Dict[str, Any]]:
        op = str(operation_key or "").lower()
        mapping = {
            "send": "send_gmail",
            "enviar": "send_gmail",
            "list": "list_gmail",
            "listar": "list_gmail",
            "enable_push": "enable_gmail_push",
            "disable_push": "disable_gmail_push",
            "status": "get_gmail_push_status",
        }
        operation = mapping.get(op)
        if not operation:
            return None
        params: Dict[str, Any] = {}
        if operation == "send_gmail":
            recipients = entities.get("email_recipients")
            if isinstance(recipients, str):
                recipients = [recipients]
            if not recipients:
                recipients = self._extract_emails(query)
            if recipients:
                params["to"] = recipients
            if entities.get("email_subject"):
                params["subject"] = entities["email_subject"]
            if entities.get("email_body"):
                params["body"] = entities["email_body"]
            elif entities.get("email_content"):
                params["body"] = entities["email_content"]
            params.setdefault("compose_context", query)
        if operation == "list_gmail":
            if entities.get("gmail_query"):
                params["query"] = entities["gmail_query"]
        if operation in {"enable_gmail_push"}:
            if entities.get("gmail_label_ids"):
                params["label_ids"] = entities["gmail_label_ids"]
            if entities.get("gmail_topic"):
                params["topic_name"] = entities["gmail_topic"]
        return {"operation": operation, "parameters": params}

    def _build_drive_instruction(self, operation_key: Any, entities: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        op = str(operation_key or "").lower()
        if op in {"create", "crear"}:
            params = {
                "name": entities.get("drive_name") or "agente-g-nota.txt",
                "content": entities.get("drive_content") or "",
            }
            if entities.get("drive_folder_id"):
                params["folder_id"] = entities["drive_folder_id"]
            return {"operation": "create_drive_text", "parameters": params}
        params: Dict[str, Any] = {}
        if entities.get("drive_query"):
            params["query"] = entities["drive_query"]
        return {"operation": "list_drive", "parameters": params}

    def _build_calendar_instruction(self, operation_key: Any, entities: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        op = str(operation_key or "").lower()
        if op in {"create_event", "crear_evento", "agendar"}:
            params = {
                "summary": entities.get("calendar_summary") or "Evento Agente G",
                "start": entities.get("calendar_start") or "",
                "end": entities.get("calendar_end") or "",
            }
            if entities.get("calendar_timezone"):
                params["timeZone"] = entities["calendar_timezone"]
            if entities.get("calendar_attendees"):
                params["attendees"] = entities["calendar_attendees"]
            return {"operation": "create_calendar_event", "parameters": params}
        return None

    @staticmethod
    def _extract_emails(text: str) -> list[str]:
        if not text:
            return []
        matches = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
        seen = set()
        result: list[str] = []
        for match in matches:
            email = match.lower()
            if email not in seen:
                seen.add(email)
                result.append(email)
        if result:
            return result
        tokens = [token.strip("()[]{}<>'\".,;") for token in text.split()]
        for token in tokens:
            lowered = token.lower()
            if "@" in lowered and "." in lowered and lowered not in seen:
                seen.add(lowered)
                result.append(lowered)
        return result

    @staticmethod
    def _extract_slot(text: str, markers: tuple[str, ...]) -> Optional[str]:
        if not text:
            return None
        lowered = text.lower()
        for marker in markers:
            marker_lower = marker.lower()
            if marker_lower in lowered:
                start = lowered.find(marker_lower) + len(marker_lower)
                remainder = text[start:].strip(" :,-")
                if remainder:
                    parts = remainder.split("\n", 1)
                    value = parts[0].strip()
                    if value:
                        return value
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

    _EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

    def _validate_instruction(self, instruction: Dict[str, Any]) -> tuple[bool, Optional[str], Dict[str, Any]]:
        operation = (instruction or {}).get("operation")
        if operation == "send_gmail":
            parameters = instruction.get("parameters") or {}
            raw_recipients = parameters.get("to")
            recipients = self._coerce_recipients(raw_recipients)
            valid_recipients = [email for email in recipients if self._is_valid_email(email)]
            if not valid_recipients:
                message = (
                    "Necesito un correo electronico valido (formato nombre@dominio) antes de poder enviar el mail."
                )
                metadata = {"validation_error": "invalid_email_recipients"}
                return False, message, metadata
            parameters["to"] = valid_recipients
            instruction["parameters"] = parameters
            logger.info(
                {
                    "event": "email_trace",
                    "stage": "agente_g_validation_passed",
                    "recipients": valid_recipients,
                }
            )
        return True, None, {}

    def _format_capi_gus_confirmation(self, params: Dict[str, Any]) -> str:
        raw_recipients = params.get("to") or []
        if isinstance(raw_recipients, str):
            recipients = [raw_recipients]
        else:
            recipients = [str(item) for item in raw_recipients if item]
        recipients = [r.strip() for r in recipients if r]
        subject = str(params.get("subject") or "").strip() or "(sin asunto)"
        if recipients:
            joined = ", ".join(recipients)
            return f"Capi Gus te confirma: envie el correo a {joined} con asunto \"{subject}\". Necesitas algo mas?"
        return "Capi Gus te confirma que el correo fue gestionado correctamente."


    def _coerce_recipients(self, recipients: Any) -> list[str]:
        if not recipients:
            return []
        values: list[str] = []
        queue: list[str] = []
        if isinstance(recipients, str):
            queue.append(recipients)
        elif isinstance(recipients, Iterable):
            for item in recipients:
                if isinstance(item, str):
                    queue.append(item)
        else:
            return []

        for candidate in queue:
            stripped = candidate.strip()
            if not stripped:
                continue
            extracted = self._extract_emails(stripped)
            if extracted:
                values.extend(extracted)
            else:
                # Keep raw value for validation; will be filtered later
                values.append(stripped)
        seen: set[str] = set()
        unique: list[str] = []
        for email in values:
            lowered = email.lower()
            if lowered not in seen:
                seen.add(lowered)
                unique.append(lowered)
        return unique

    def _is_valid_email(self, email: str) -> bool:
        if not email or not isinstance(email, str):
            return False
        return bool(self._EMAIL_REGEX.match(email.strip()))


__all__ = ["AgenteGNode"]
