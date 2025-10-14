<<<<<<< HEAD
"""Agente G handler: integra Gmail, Drive y Calendar."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from src.domain.agents.agent_models import AgentResult, IntentType, TaskStatus
from src.domain.agents.agent_protocol import AgentTask, BaseAgent

from src.infrastructure.external.google import (
    GoogleOAuthSettings,
    GoogleCredentialsManager,
    GoogleServiceFactory,
    GmailClient,
    DriveClient,
    CalendarClient,
    GMAIL_READ_SCOPE,
    GMAIL_MODIFY_SCOPE,
    DRIVE_SCOPE,
    CALENDAR_SCOPE,
)

from .push_service import AgenteGPushService

logger = logging.getLogger(__name__)

SUPPORTED_INTENTS = [
    IntentType.FILE_OPERATION,
    IntentType.QUERY,
    getattr(IntentType, "GOOGLE_DRIVE", IntentType.QUERY),
    getattr(IntentType, "GOOGLE_GMAIL", IntentType.QUERY),
    getattr(IntentType, "GOOGLE_CALENDAR", IntentType.QUERY),
]


OPERATION_SCOPES = {
    "list_gmail": [GMAIL_READ_SCOPE],
    "send_gmail": [GMAIL_MODIFY_SCOPE],
    "list_drive": [DRIVE_SCOPE],
    "create_drive_text": [DRIVE_SCOPE],
    "create_calendar_event": [CALENDAR_SCOPE],
    "enable_gmail_push": [GMAIL_READ_SCOPE],
    "disable_gmail_push": [GMAIL_READ_SCOPE],
    "get_gmail_push_status": [],
}


@dataclass
class OperationResult:
    message: str
    data: Dict[str, Any]
    artifact: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None


class AgenteGAgent(BaseAgent):
    AGENT_NAME = "agente_g"

    def __init__(
        self,
        *,
        gmail_client: GmailClient | None = None,
        drive_client: DriveClient | None = None,
        calendar_client: CalendarClient | None = None,
        push_service: AgenteGPushService | None = None,
    ) -> None:
        super().__init__(self.AGENT_NAME)
        if gmail_client and drive_client and calendar_client:
            self.gmail = gmail_client
            self.drive = drive_client
            self.calendar = calendar_client
            self._settings = None
        else:
            settings = GoogleOAuthSettings.load_from_env()
            manager = GoogleCredentialsManager(settings)
            factory = GoogleServiceFactory(manager)
            self.gmail = gmail_client or GmailClient(factory, user_id=settings.agent_email or "me")
            self.drive = drive_client or DriveClient(factory)
            self.calendar = calendar_client or CalendarClient(factory, calendar_id="primary")
            self._settings = settings
        self.push_service = push_service or AgenteGPushService(gmail_client=self.gmail)

    @property
    def agent_email(self) -> str | None:
        if self._settings:
            return self._settings.agent_email
        return None

    @property
    def supported_intents(self) -> list[IntentType]:
        return SUPPORTED_INTENTS

    def process(self, task: AgentTask) -> AgentResult:
        metadata = task.metadata or {}
        operation = str(metadata.get("operation") or "").strip().lower()
        params = metadata.get("parameters") or {}

        agent_progress.start(
            self.AGENT_NAME,
            task.session_id,
            query=task.query,
            extra={'operation': operation or metadata.get('operation')}
        )

        if not operation:
            operation, params = self._infer_operation(task)
            if not operation:
                message = (
                    "No pude determinar la accion para Agente G."
                    " Proporciona una instruccion clara (listar correos, enviar correo, listar drive, crear evento)."
                )
                agent_progress.error(
                    self.AGENT_NAME,
                    task.session_id,
                    detail=message,
                    extra={'operation': None}
                )
                return AgentResult(
                    task_id=task.task_id,
                    agent_name=self.agent_name,
                    status=TaskStatus.FAILED,
                    message=message,
                    data={"hint": "set agente_g operation via metadata"},
                )

        try:
            result = self._execute_operation(operation, params)
            payload = {
                "operation": operation,
                "parameters": params,
                "result": result.data,
            }
            if result.artifact:
                payload["artifact"] = result.artifact
            if result.metrics:
                payload["metrics"] = result.metrics

            agent_progress.success(
                self.AGENT_NAME,
                task.session_id,
                detail=result.message,
                extra={'operation': operation}
            )

            return AgentResult(
                task_id=task.task_id,
                agent_name=self.agent_name,
                status=TaskStatus.COMPLETED,
                message=result.message,
                data=payload,
            )
        except Exception as exc:
            logger.exception("agente_g_operation_failed", extra={"operation": operation})
            agent_progress.error(
                self.AGENT_NAME,
                task.session_id,
                detail=str(exc),
                extra={'operation': operation}
            )
            return AgentResult(
                task_id=task.task_id,
                agent_name=self.agent_name,
                status=TaskStatus.FAILED,
                message=f"No pude completar la accion '{operation}': {exc}",
                data={"operation": operation, "parameters": params},
            )

    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _infer_operation(self, task: AgentTask) -> tuple[str | None, Dict[str, Any]]:
        query = task.query.lower()
        if "listar" in query and ("correo" in query or "email" in query):
            return "list_gmail", {"query": "is:unread"}
        if "listar" in query and "drive" in query:
            return "list_drive", {}
        if "crear" in query and "evento" in query:
            return "create_calendar_event", {}
        return None, {}

    def _execute_operation(self, operation: str, params: Dict[str, Any]) -> OperationResult:
        start = time.perf_counter()
        if operation == "list_gmail":
            result = self._op_list_gmail(params)
        elif operation == "send_gmail":
            result = self._op_send_gmail(params)
        elif operation == "list_drive":
            result = self._op_list_drive(params)
        elif operation == "create_drive_text":
            result = self._op_create_drive_text(params)
        elif operation == "create_calendar_event":
            result = self._op_create_calendar_event(params)
        elif operation == "enable_gmail_push":
            result = self._op_enable_gmail_push(params)
        elif operation == "disable_gmail_push":
            result = self._op_disable_gmail_push()
        elif operation == "get_gmail_push_status":
            result = self._op_get_gmail_push_status()
        else:
            raise ValueError(f"Operacion no soportada por Agente G: {operation}")

        scopes = OPERATION_SCOPES.get(operation, [])
        metrics = result.metrics or {}
        metrics.setdefault("google_api_calls", metrics.get("google_api_calls", 1))
        metrics.setdefault("google_scopes_used", scopes)
        metrics["operation"] = operation
        metrics["duration_ms"] = int((time.perf_counter() - start) * 1000)
        result.metrics = metrics
        return result

    def _ensure_push_service(self) -> AgenteGPushService:
        if not self.push_service:
            raise RuntimeError("Agente G no tiene configurado el servicio de push")
        return self.push_service

    def _op_enable_gmail_push(self, params: Dict[str, Any]) -> OperationResult:
        service = self._ensure_push_service()
        topic_name = params.get("topic_name")
        label_ids = params.get("label_ids")
        label_filter_action = params.get("label_filter_action")
        if label_ids is not None and isinstance(label_ids, str):
            label_ids = [value.strip() for value in label_ids.split(",") if value.strip()]
        status = service.enable_push(
            topic_name=topic_name,
            label_ids=label_ids,
            label_filter_action=label_filter_action,
        )
        artifact = {
            "type": "gmail_push_status",
            "active": status.get("active"),
            "topic_name": status.get("topic_name"),
            "label_ids": status.get("label_ids"),
            "expiration": status.get("expiration"),
        }
        message = "Push de Gmail habilitado correctamente."
        metrics = {
            "google_api_calls": 1,
        }
        return OperationResult(message=message, data={"status": status}, artifact=artifact, metrics=metrics)

    def _op_disable_gmail_push(self) -> OperationResult:
        service = self._ensure_push_service()
        status = service.disable_push()
        artifact = {
            "type": "gmail_push_status",
            "active": status.get("active"),
            "updated_at": status.get("updated_at"),
        }
        message = "Push de Gmail deshabilitado."
        metrics = {
            "google_api_calls": 1,
        }
        return OperationResult(message=message, data={"status": status}, artifact=artifact, metrics=metrics)

    def _op_get_gmail_push_status(self) -> OperationResult:
        service = self._ensure_push_service()
        status = service.get_status()
        artifact = {
            "type": "gmail_push_status",
            "active": status.get("active"),
            "topic_name": status.get("topic_name"),
            "last_history_id": status.get("last_history_id"),
            "last_error": status.get("last_error"),
        }
        message = "Estado del push de Gmail consultado."
        metrics = {
            "google_api_calls": 0,
        }
        return OperationResult(message=message, data={"status": status}, artifact=artifact, metrics=metrics)

    def _op_list_gmail(self, params: Dict[str, Any]) -> OperationResult:
        query = params.get("query")
        label_ids = params.get("label_ids")
        response = self.gmail.list_messages(query=query, label_ids=label_ids, max_results=int(params.get("max_results", 10)))
        message_summaries = []
        for item in response.get("messages", [])[:10]:
            msg = self.gmail.get_message(item["id"], format="metadata")
            headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
            message_summaries.append(
                {
                    "id": msg.get("id"),
                    "thread_id": msg.get("threadId"),
                    "snippet": msg.get("snippet"),
                    "from": headers.get("from"),
                    "subject": headers.get("subject"),
                    "date": headers.get("date"),
                }
            )
        artifact = {
            "type": "email",
            "items": message_summaries,
            "query": query,
        }
        message = f"Se recuperaron {len(message_summaries)} correos (query={query or 'todos'})."
        metrics = {
            "google_api_calls": 1 + len(message_summaries),
            "items": len(message_summaries),
        }
        return OperationResult(message=message, data=response, artifact=artifact, metrics=metrics)

    def _op_send_gmail(self, params: Dict[str, Any]) -> OperationResult:
        to = params.get("to") or []
        if isinstance(to, str):
            to = [address.strip() for address in to.split(",") if address.strip()]
        subject = params.get("subject") or "(sin asunto)"
        body = params.get("body") or ""
        cc = params.get("cc")
        bcc = params.get("bcc")
        sent = self.gmail.send_plain_text(
            to=list(to),
            subject=str(subject),
            body=str(body),
            cc=[c.strip() for c in cc] if isinstance(cc, list) else None,
            bcc=[b.strip() for b in bcc] if isinstance(bcc, list) else None,
            sender=self.agent_email,
        )
        artifact = {
            "type": "email_sent",
            "message_id": sent.get("id"),
            "thread_id": sent.get("threadId"),
            "recipients": to,
            "subject": subject,
        }
        message = f"Correo enviado a {', '.join(to)}."
        metrics = {
            "google_api_calls": 1,
            "recipients": len(to),
        }
        return OperationResult(message=message, data=sent, artifact=artifact, metrics=metrics)

    def _op_list_drive(self, params: Dict[str, Any]) -> OperationResult:
        query = params.get("query")
        response = self.drive.list_files(query=query, page_size=int(params.get("page_size", 20)))
        artifact = {
            "type": "drive_list",
            "items": response.get("files", []),
            "query": query,
        }
        message = f"Se encontraron {len(response.get('files', []))} archivos en Drive."
        metrics = {
            "google_api_calls": 1,
            "items": len(response.get("files", [])),
        }
        return OperationResult(message=message, data=response, artifact=artifact, metrics=metrics)

    def _op_create_drive_text(self, params: Dict[str, Any]) -> OperationResult:
        name = params.get("name") or "agente-g-nota.txt"
        content = params.get("content") or ""
        folder_id = params.get("folder_id")
        result = self.drive.create_text_file(name=name, content=content, folder_id=folder_id)
        artifact = {
            "type": "drive_file",
            "id": result.get("id"),
            "name": result.get("name"),
            "link": result.get("webViewLink"),
        }
        message = f"Archivo '{result.get('name')}' creado en Drive."
        metrics = {
            "google_api_calls": 1,
        }
        return OperationResult(message=message, data=result, artifact=artifact, metrics=metrics)

    def _op_create_calendar_event(self, params: Dict[str, Any]) -> OperationResult:
        summary = params.get("summary") or "Evento sin titulo"
        start = params.get("start")
        end = params.get("end")
        if not start or not end:
            raise ValueError("Los parametros 'start' y 'end' son obligatorios para crear un evento")
        attendees = params.get("attendees") or []
        description = params.get("description")
        timezone = params.get("timeZone") or params.get("timezone")
        attendees_list = attendees
        if isinstance(attendees, str):
            attendees_list = [email.strip() for email in attendees.split(",") if email.strip()]
        result = self.calendar.create_event(
            summary=summary,
            start_iso=start,
            end_iso=end,
            description=description,
            attendees=list(attendees_list) if attendees_list else None,
            timezone=timezone,
        )
        artifact = {
            "type": "calendar_event",
            "id": result.get("id"),
            "summary": result.get("summary"),
            "link": result.get("htmlLink"),
        }
        message = f"Evento '{result.get('summary')}' creado."
        metrics = {
            "google_api_calls": 1,
            "attendees": len(list(attendees_list) if attendees_list else []),
        }
        return OperationResult(message=message, data=result, artifact=artifact, metrics=metrics)


__all__ = ["AgenteGAgent", "SUPPORTED_INTENTS"]
=======
"""Agente G handler: integra Gmail, Drive y Calendar."""

from __future__ import annotations



import asyncio

import json

import logging

import re

import textwrap

import time
from concurrent.futures import ThreadPoolExecutor

from dataclasses import dataclass

from typing import Any, Dict, Optional



from src.application.reasoning.llm_reasoner import LLMReasoner, LLMReasoningResult
from src.domain.agents.agent_models import AgentResult, IntentType, TaskStatus

from src.domain.agents.agent_protocol import AgentTask, BaseAgent



from src.infrastructure.external.google import (

    GoogleOAuthSettings,

    GoogleCredentialsManager,

    GoogleServiceFactory,

    GmailClient,

    DriveClient,

    CalendarClient,

    GMAIL_READ_SCOPE,

    GMAIL_MODIFY_SCOPE,

    DRIVE_SCOPE,

    CALENDAR_SCOPE,

)



from src.infrastructure.agents.progress_emitter import agent_progress

from .push_service import AgenteGPushService



logger = logging.getLogger(__name__)



SUPPORTED_INTENTS = [

    IntentType.FILE_OPERATION,

    IntentType.QUERY,

    getattr(IntentType, "GOOGLE_DRIVE", IntentType.QUERY),

    getattr(IntentType, "GOOGLE_GMAIL", IntentType.QUERY),

    getattr(IntentType, "GOOGLE_CALENDAR", IntentType.QUERY),

]





OPERATION_SCOPES = {

    "list_gmail": [GMAIL_READ_SCOPE],

    "send_gmail": [GMAIL_MODIFY_SCOPE],

    "list_drive": [DRIVE_SCOPE],

    "create_drive_text": [DRIVE_SCOPE],

    "create_calendar_event": [CALENDAR_SCOPE],

    "enable_gmail_push": [GMAIL_READ_SCOPE],

    "disable_gmail_push": [GMAIL_READ_SCOPE],

    "get_gmail_push_status": [],

}





@dataclass

class OperationResult:

    message: str

    data: Dict[str, Any]

    artifact: Optional[Dict[str, Any]] = None

    metrics: Optional[Dict[str, Any]] = None





class AgenteGAgent(BaseAgent):

    AGENT_NAME = "agente_g"



    def __init__(

        self,

        *,

        gmail_client: GmailClient | None = None,

        drive_client: DriveClient | None = None,

        calendar_client: CalendarClient | None = None,

        push_service: AgenteGPushService | None = None,

        llm_reasoner: LLMReasoner | None = None,

        compose_with_llm: bool = True,

    ) -> None:

        super().__init__(self.AGENT_NAME)

        if gmail_client and drive_client and calendar_client:

            self.gmail = gmail_client

            self.drive = drive_client

            self.calendar = calendar_client

            self._settings = None

        else:

            settings = GoogleOAuthSettings.load_from_env()

            manager = GoogleCredentialsManager(settings)

            factory = GoogleServiceFactory(manager)

            self.gmail = gmail_client or GmailClient(factory, user_id=settings.agent_email or "me")

            self.drive = drive_client or DriveClient(factory)

            self.calendar = calendar_client or CalendarClient(factory, calendar_id="primary")

            self._settings = settings

        self.push_service = push_service or AgenteGPushService(gmail_client=self.gmail)

        self._llm_reasoner = llm_reasoner

        self._compose_with_llm = compose_with_llm
        self._llm_executor: ThreadPoolExecutor | None = ThreadPoolExecutor(max_workers=1)



    @property

    def agent_email(self) -> str | None:

        if self._settings:

            return self._settings.agent_email

        return None



    @property

    def supported_intents(self) -> list[IntentType]:

        return SUPPORTED_INTENTS



    def process(self, task: AgentTask) -> AgentResult:

        metadata = task.metadata or {}

        operation = str(metadata.get("operation") or "").strip().lower()

        params = dict(metadata.get("parameters") or {})



        agent_progress.start(

            self.AGENT_NAME,

            task.session_id,

            query=task.query,

            extra={'operation': operation or metadata.get('operation')}

        )



        if not operation:

            operation, inferred_params = self._infer_operation(task)

            params = dict(inferred_params or {})

            if not operation:

                message = (

                    "No pude determinar la accion para Agente G."

                    " Proporciona una instruccion clara (listar correos, enviar correo, listar drive, crear evento)."

                )

                agent_progress.error(

                    self.AGENT_NAME,

                    task.session_id,

                    detail=message,

                    extra={'operation': None}

                )

                return AgentResult(

                    task_id=task.task_id,

                    agent_name=self.agent_name,

                    status=TaskStatus.FAILED,

                    message=message,

                    data={"hint": "set agente_g operation via metadata"},

                )



        if operation == "send_gmail":

            params.setdefault("compose_context", task.query)

            params.setdefault("compose_with_llm", self._compose_with_llm)

            if "to" not in params or not params.get("to"):

                params["to"] = self._extract_emails(task.query)

        try:

            result = self._execute_operation(operation, params)

            payload = {

                "operation": operation,

                "parameters": params,

                "result": result.data,

            }

            if result.artifact:

                payload["artifact"] = result.artifact

            if result.metrics:

                payload["metrics"] = result.metrics



            agent_progress.success(

                self.AGENT_NAME,

                task.session_id,

                detail=result.message,

                extra={'operation': operation}

            )



            return AgentResult(

                task_id=task.task_id,

                agent_name=self.agent_name,

                status=TaskStatus.COMPLETED,

                message=result.message,

                data=payload,

            )

        except Exception as exc:

            logger.exception("agente_g_operation_failed", extra={"operation": operation})

            agent_progress.error(

                self.AGENT_NAME,

                task.session_id,

                detail=str(exc),

                extra={'operation': operation}

            )

            return AgentResult(

                task_id=task.task_id,

                agent_name=self.agent_name,

                status=TaskStatus.FAILED,

                message=f"No pude completar la accion '{operation}': {exc}",

                data={"operation": operation, "parameters": params},

            )



    # ------------------------------------------------------------------

    # ------------------------------------------------------------------

    # Internal helpers

    # ------------------------------------------------------------------



    def _infer_operation(self, task: AgentTask) -> tuple[str | None, Dict[str, Any]]:

        query = task.query.lower()

        if "listar" in query and ("correo" in query or "email" in query):

            return "list_gmail", {"query": "is:unread"}

        if "listar" in query and "drive" in query:

            return "list_drive", {}

        if "crear" in query and "evento" in query:

            return "create_calendar_event", {}

        if ("enviar" in query or "envia" in query or "enviá" in query or "mandar" in query or "responder" in query) and ("correo" in query or "mail" in query or "gmail" in query or "email" in query):

            return "send_gmail", {"compose_context": task.query}

        if ("crear" in query or "generar" in query) and "drive" in query:

            return "create_drive_text", {}

        if "estado" in query and "push" in query and "gmail" in query:

            return "get_gmail_push_status", {}

        return None, {}



    def _execute_operation(self, operation: str, params: Dict[str, Any]) -> OperationResult:

        start = time.perf_counter()

        if operation == "list_gmail":

            result = self._op_list_gmail(params)

        elif operation == "send_gmail":

            result = self._op_send_gmail(params)

        elif operation == "list_drive":

            result = self._op_list_drive(params)

        elif operation == "create_drive_text":

            result = self._op_create_drive_text(params)

        elif operation == "create_calendar_event":

            result = self._op_create_calendar_event(params)

        elif operation == "enable_gmail_push":

            result = self._op_enable_gmail_push(params)

        elif operation == "disable_gmail_push":

            result = self._op_disable_gmail_push()

        elif operation == "get_gmail_push_status":

            result = self._op_get_gmail_push_status()

        else:

            raise ValueError(f"Operacion no soportada por Agente G: {operation}")



        scopes = OPERATION_SCOPES.get(operation, [])

        metrics = result.metrics or {}

        metrics.setdefault("google_api_calls", metrics.get("google_api_calls", 1))

        metrics.setdefault("google_scopes_used", scopes)

        metrics["operation"] = operation

        metrics["duration_ms"] = int((time.perf_counter() - start) * 1000)

        result.metrics = metrics

        return result



    def _ensure_push_service(self) -> AgenteGPushService:

        if not self.push_service:

            raise RuntimeError("Agente G no tiene configurado el servicio de push")

        return self.push_service



    def _op_enable_gmail_push(self, params: Dict[str, Any]) -> OperationResult:

        service = self._ensure_push_service()

        topic_name = params.get("topic_name")

        label_ids = params.get("label_ids")

        label_filter_action = params.get("label_filter_action")

        if label_ids is not None and isinstance(label_ids, str):

            label_ids = [value.strip() for value in label_ids.split(",") if value.strip()]

        status = service.enable_push(

            topic_name=topic_name,

            label_ids=label_ids,

            label_filter_action=label_filter_action,

        )

        artifact = {

            "type": "gmail_push_status",

            "active": status.get("active"),

            "topic_name": status.get("topic_name"),

            "label_ids": status.get("label_ids"),

            "expiration": status.get("expiration"),

        }

        message = "Push de Gmail habilitado correctamente."

        metrics = {

            "google_api_calls": 1,

        }

        return OperationResult(message=message, data={"status": status}, artifact=artifact, metrics=metrics)



    def _op_disable_gmail_push(self) -> OperationResult:

        service = self._ensure_push_service()

        status = service.disable_push()

        artifact = {

            "type": "gmail_push_status",

            "active": status.get("active"),

            "updated_at": status.get("updated_at"),

        }

        message = "Push de Gmail deshabilitado."

        metrics = {

            "google_api_calls": 1,

        }

        return OperationResult(message=message, data={"status": status}, artifact=artifact, metrics=metrics)



    def _op_get_gmail_push_status(self) -> OperationResult:

        service = self._ensure_push_service()

        status = service.get_status()

        artifact = {

            "type": "gmail_push_status",

            "active": status.get("active"),

            "topic_name": status.get("topic_name"),

            "last_history_id": status.get("last_history_id"),

            "last_error": status.get("last_error"),

        }

        message = "Estado del push de Gmail consultado."

        metrics = {

            "google_api_calls": 0,

        }

        return OperationResult(message=message, data={"status": status}, artifact=artifact, metrics=metrics)



    def _op_list_gmail(self, params: Dict[str, Any]) -> OperationResult:

        query = params.get("query")

        label_ids = params.get("label_ids")

        response = self.gmail.list_messages(query=query, label_ids=label_ids, max_results=int(params.get("max_results", 10)))

        message_summaries = []

        for item in response.get("messages", [])[:10]:

            msg = self.gmail.get_message(item["id"], format="metadata")

            headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}

            message_summaries.append(

                {

                    "id": msg.get("id"),

                    "thread_id": msg.get("threadId"),

                    "snippet": msg.get("snippet"),

                    "from": headers.get("from"),

                    "subject": headers.get("subject"),

                    "date": headers.get("date"),

                }

            )

        artifact = {

            "type": "email",

            "items": message_summaries,

            "query": query,

        }

        message = f"Se recuperaron {len(message_summaries)} correos (query={query or 'todos'})."

        metrics = {

            "google_api_calls": 1 + len(message_summaries),

            "items": len(message_summaries),

        }

        return OperationResult(message=message, data=response, artifact=artifact, metrics=metrics)






    def _op_send_gmail(self, params: Dict[str, Any]) -> OperationResult:
        to_raw = params.get("to") or []
        if isinstance(to_raw, str):
            to_raw = [address.strip() for address in to_raw.split(",") if address.strip()]
        compose_context = params.get("compose_context")
        normalized_to = self._normalize_recipients(to_raw)
        if not normalized_to and compose_context:
            inferred = self._extract_emails(compose_context)
            normalized_to = self._normalize_recipients(inferred)
        params["to"] = list(normalized_to)

        subject = params.get("subject")
        body = params.get("body")
        llm_metrics: Dict[str, Any] = {}
        if params.get("compose_with_llm", True):
            subject, body, llm_metrics = self._ensure_email_content(
                subject=subject,
                body=body,
                compose_context=compose_context,
                recipients=list(normalized_to),
                cc=params.get("cc"),
                bcc=params.get("bcc"),
            )
        subject = subject or "(sin asunto)"
        body = body or (compose_context or "")
        cc = params.get("cc")
        bcc = params.get("bcc")

        sent = self.gmail.send_plain_text(
            to=list(normalized_to),
            subject=str(subject),
            body=str(body),
            cc=[c.strip() for c in cc] if isinstance(cc, list) else None,
            bcc=[b.strip() for b in bcc] if isinstance(bcc, list) else None,
            sender=self.agent_email,
        )

        artifact = {
            "type": "email_sent",
            "message_id": sent.get("id"),
            "thread_id": sent.get("threadId"),
            "recipients": list(normalized_to),
            "subject": subject,
        }

        message = f"Correo enviado a {', '.join(normalized_to)}."
        metrics = {
            "google_api_calls": 1,
            "recipients": len(normalized_to),
        }
        if llm_metrics:
            metrics.update(llm_metrics)

        return OperationResult(message=message, data=sent, artifact=artifact, metrics=metrics)


    def _normalize_recipients(self, items: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for raw in items or []:
            if not raw:
                continue
            for candidate in self._extract_emails(raw):
                if candidate not in seen:
                    seen.add(candidate)
                    normalized.append(candidate)
            cleaned = raw.strip().lower()
            if "@" not in cleaned and "gmail.com" in cleaned:
                local = cleaned.replace(" ", "").split("gmail.com", 1)[0].rstrip("@.")
                if local:
                    candidate = f"{local}@gmail.com"
                    if candidate not in seen:
                        seen.add(candidate)
                        normalized.append(candidate)
        return normalized

    def _ensure_email_content(
        self,
        *,
        subject: Optional[str],
        body: Optional[str],
        compose_context: Optional[str],
        recipients: list[str],
        cc: Optional[Any],
        bcc: Optional[Any],
    ) -> tuple[str, str, Dict[str, Any]]:
        recipients = self._normalize_recipients(recipients)
        normalized_subject = (subject or "").strip()
        normalized_body = (body or "").strip()
        metrics: Dict[str, Any] = {}
        if (not normalized_subject or not normalized_body) and compose_context:
            llm_result = self._compose_email_with_llm(
                compose_context=compose_context,
                recipients=recipients,
                cc=cc,
                bcc=bcc,
                subject_hint=normalized_subject,
                body_hint=normalized_body,
            )
            if llm_result:
                normalized_subject = llm_result.get("subject", normalized_subject)
                normalized_body = llm_result.get("body", normalized_body)
                metrics.update(llm_result.get("metrics", {}))
        if not normalized_body and compose_context:
            normalized_body = compose_context.strip()
        if not normalized_subject:
            normalized_subject = "(sin asunto)"
        return normalized_subject, normalized_body, metrics

    def _compose_email_with_llm(
        self,
        *,
        compose_context: str,
        recipients: list[str],
        cc: Optional[Any],
        bcc: Optional[Any],
        subject_hint: str,
        body_hint: str,
    ) -> Optional[Dict[str, Any]]:
        reasoner = self._get_llm_reasoner()
        if not reasoner or not compose_context:
            return None
        audience = ", ".join(recipients) if recipients else "no especificados"
        cc_line = ", ".join(cc) if isinstance(cc, list) else ""
        bcc_line = ", ".join(bcc) if isinstance(bcc, list) else ""
        prompt = textwrap.dedent(
            f"""
            Genera un borrador breve de correo en español neutro.
            Devuelve un JSON con las claves obligatorias `subject` y `body`.
            Contexto entregado por el usuario:
            {compose_context}

            Destinatarios principales: {audience or 'no especificados'}
            Copia (CC): {cc_line or 'sin cc'}
            Copia oculta (BCC): {bcc_line or 'sin bcc'}

            Ajusta el tono profesional y directo. El body debe tener maximo 6 lineas.
            """
        ).strip()
        system_prompt = (
            "Eres un asistente que redacta correos ejecutivos en español."
            " Responde unicamente con JSON valida que contenga las claves subject y body."
        )
        llm_result = self._run_reasoner(reasoner, prompt, system_prompt)
        if not llm_result or not llm_result.success or not llm_result.response:
            return {"subject": subject_hint or "(sin asunto)", "body": body_hint or compose_context, "metrics": {}}
        try:
            payload = json.loads(llm_result.response)
        except json.JSONDecodeError:
            payload = {}
        composed_subject = str(payload.get("subject") or subject_hint or "(sin asunto)").strip()
        composed_body = str(payload.get("body") or body_hint or compose_context).strip()
        metrics = {
            "llm_prompt_tokens": llm_result.prompt_tokens,
            "llm_completion_tokens": llm_result.completion_tokens,
            "llm_total_tokens": llm_result.total_tokens,
            "llm_model": llm_result.model,
        }
        return {"subject": composed_subject, "body": composed_body, "metrics": metrics}

    def _run_reasoner(self, reasoner: LLMReasoner, prompt: str, system_prompt: str) -> Optional[LLMReasoningResult]:
        async def _invoke() -> LLMReasoningResult:
            return await reasoner.reason(
                query=prompt,
                system_prompt=system_prompt,
                response_format="json_object",
                max_output_tokens=600,
            )

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(_invoke())

        if self._llm_executor is None:
            self._llm_executor = ThreadPoolExecutor(max_workers=1)

        def _run_sync() -> LLMReasoningResult:
            return asyncio.run(_invoke())

        future = self._llm_executor.submit(_run_sync)
        return future.result()

    def _get_llm_reasoner(self) -> Optional[LLMReasoner]:
        if not self._compose_with_llm:
            return None
        if self._llm_reasoner is None:
            try:
                self._llm_reasoner = LLMReasoner(temperature=0.35, max_tokens=600)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning({"event": "agente_g_llm_init_failed", "error": str(exc)})
                self._compose_with_llm = False
                return None
        return self._llm_reasoner

    @staticmethod
    def _extract_emails(text: str) -> list[str]:
        if not text:
            return []
        matches = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
        seen = set()
        results: list[str] = []
        for match in matches:
            lowered = match.lower()
            if lowered not in seen:
                seen.add(lowered)
                results.append(lowered)
        return results

    def _op_list_drive(self, params: Dict[str, Any]) -> OperationResult:

        query = params.get("query")

        response = self.drive.list_files(query=query, page_size=int(params.get("page_size", 20)))

        artifact = {

            "type": "drive_list",

            "items": response.get("files", []),

            "query": query,

        }

        message = f"Se encontraron {len(response.get('files', []))} archivos en Drive."

        metrics = {

            "google_api_calls": 1,

            "items": len(response.get("files", [])),

        }

        return OperationResult(message=message, data=response, artifact=artifact, metrics=metrics)



    def _op_create_drive_text(self, params: Dict[str, Any]) -> OperationResult:

        name = params.get("name") or "agente-g-nota.txt"

        content = params.get("content") or ""

        folder_id = params.get("folder_id")

        result = self.drive.create_text_file(name=name, content=content, folder_id=folder_id)

        artifact = {

            "type": "drive_file",

            "id": result.get("id"),

            "name": result.get("name"),

            "link": result.get("webViewLink"),

        }

        message = f"Archivo '{result.get('name')}' creado en Drive."

        metrics = {

            "google_api_calls": 1,

        }

        return OperationResult(message=message, data=result, artifact=artifact, metrics=metrics)



    def _op_create_calendar_event(self, params: Dict[str, Any]) -> OperationResult:

        summary = params.get("summary") or "Evento sin titulo"

        start = params.get("start")

        end = params.get("end")

        if not start or not end:

            raise ValueError("Los parametros 'start' y 'end' son obligatorios para crear un evento")

        attendees = params.get("attendees") or []

        description = params.get("description")

        timezone = params.get("timeZone") or params.get("timezone")

        attendees_list = attendees

        if isinstance(attendees, str):

            attendees_list = [email.strip() for email in attendees.split(",") if email.strip()]

        result = self.calendar.create_event(

            summary=summary,

            start_iso=start,

            end_iso=end,

            description=description,

            attendees=list(attendees_list) if attendees_list else None,

            timezone=timezone,

        )

        artifact = {

            "type": "calendar_event",

            "id": result.get("id"),

            "summary": result.get("summary"),

            "link": result.get("htmlLink"),

        }

        message = f"Evento '{result.get('summary')}' creado."

        metrics = {

            "google_api_calls": 1,

            "attendees": len(list(attendees_list) if attendees_list else []),

        }

        return OperationResult(message=message, data=result, artifact=artifact, metrics=metrics)





__all__ = ["AgenteGAgent", "SUPPORTED_INTENTS"]



>>>>>>> origin/develop
