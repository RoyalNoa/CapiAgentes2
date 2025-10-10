"""
LLM-powered semantic intent classification service.

The previous implementation relied on cascaded keyword heuristics that were
hard to maintain and brittle. This rewrite delegates intent detection and
entity extraction to OpenAI while keeping a deterministic fall-back path for
unit tests and offline environments.
"""

from __future__ import annotations

import asyncio
import json
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

from src.application.reasoning.llm_reasoner import LLMReasoner, LLMReasoningResult
from src.core.logging import get_logger
from src.domain.contracts.intent import Intent
from src.core.semantics.context_manager import get_global_context_manager

logger = get_logger(__name__)


_ALLOWED_INTENTS = {
    intent.value: intent for intent in Intent
}

_ALLOWED_AGENTS = {
    "capi_datab",
    "capi_desktop",
    "summary",
    "branch",
    "anomaly",
    "capi_gus",
    "capi_noticias",
    "agente_g",
    "assemble",
}

_DEFAULT_AGENT_BY_INTENT = {
    Intent.DB_OPERATION: "capi_datab",
    Intent.FILE_OPERATION: "capi_desktop",
    Intent.SUMMARY: "summary",
    Intent.SUMMARY_REQUEST: "summary",
    Intent.BRANCH: "branch",
    Intent.BRANCH_QUERY: "branch",
    Intent.ANOMALY: "anomaly",
    Intent.ANOMALY_QUERY: "anomaly",
    Intent.SMALL_TALK: "capi_gus",
    Intent.GREETING: "capi_gus",
    Intent.NEWS_MONITORING: "capi_noticias",
    Intent.GOOGLE_WORKSPACE: "agente_g",
    Intent.GOOGLE_GMAIL: "agente_g",
    Intent.GOOGLE_DRIVE: "agente_g",
    Intent.GOOGLE_CALENDAR: "agente_g",
}


_LLM_ROUTER_SYSTEM_PROMPT = """
Eres un orquestador experto que enruta consultas de usuarios a agentes especializados. Recibiras un JSON con la consulta del usuario y contexto.
Devuelve siempre un JSON con exactamente los siguientes campos:
{{
  "intent": "...",                // string (usa los intents permitidos)
  "target_agent": "...",          // string (usa los agentes permitidos)
  "confidence": 0.0-1.0,           // numero entre 0 y 1
  "entities": {{ ... }},           // objeto opcional con entidades relevantes
  "requires_clarification": bool,  // true si falta informacion
  "reasoning": "..."              // explicacion breve
}}

Intents permitidos: {{intents}}
Agentes permitidos: {{agents}}

Reglas importantes:
- Elige el intent y agente mas adecuado segun la consulta y el contexto.
- Para operaciones con Gmail, Google Drive o Calendar asigna el agente "agente_g" e incluye en entities los parametros relevantes (por ejemplo `gmail_operation`, `email_recipients`, `drive_query`, `calendar_window`).
- Para consultas sobre dinero o efectivo en una sucursal, usa intent "db_operation" y agent "capi_datab" e incluye en entities la sucursal (nombre, numero o identificador).
- Si la consulta es amigable o un saludo, utiliza intent "small_talk" o "greeting" con agent "capi_gus".
- Si no estas seguro, usa intent "unknown", agent "assemble" y marca requires_clarification=true.
- Manten el JSON estricto; no agregues texto extra ni comentarios.
""".strip()




class ConfidenceLevel(Enum):
    LOW = 0.25
    MEDIUM = 0.55
    HIGH = 0.8
    VERY_HIGH = 0.92


@dataclass
class IntentResult:
    intent: Intent
    confidence: float
    target_agent: str
    entities: Dict[str, Any]
    context_resolved: bool = False
    reasoning: str = ""
    requires_clarification: bool = False
    provider: str = "openai"
    model: str = ""

    @property
    def confidence_level(self) -> ConfidenceLevel:
        if self.confidence >= ConfidenceLevel.VERY_HIGH.value:
            return ConfidenceLevel.VERY_HIGH
        if self.confidence >= ConfidenceLevel.HIGH.value:
            return ConfidenceLevel.HIGH
        if self.confidence >= ConfidenceLevel.MEDIUM.value:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.LOW


class SemanticIntentService:
    """LLM-first intent classifier with deterministic fallbacks."""

    def __init__(
        self,
        *,
        reasoner: Optional[LLMReasoner] = None,
        fallback_enabled: bool = True,
    ) -> None:
        self.reasoner = reasoner or LLMReasoner(temperature=0.2, max_tokens=400)
        self.fallback_enabled = fallback_enabled
        self.context_manager = get_global_context_manager()
        logger.info({"event": "semantic_intent_service_initialized", "fallback_enabled": fallback_enabled})

    def classify_intent(self, query: str, context: Optional[Dict[str, Any]] = None) -> IntentResult:
        if not query or not query.strip():
            return self._fallback_result(
                query=query,
                reason="empty_query",
                message="Consulta vacÃƒÆ’Ã‚Â­a",
            )

        payload = {
            "query": query.strip(),
            "context": context or {},
            "intents": sorted(_ALLOWED_INTENTS.keys()),
            "agents": sorted(_ALLOWED_AGENTS),
        }

        result = self._run_sync(
            self.reasoner.reason(
                query=json.dumps(payload, ensure_ascii=False),
                system_prompt=_LLM_ROUTER_SYSTEM_PROMPT.format(
                    intents=", ".join(sorted(_ALLOWED_INTENTS.keys())),
                    agents=", ".join(sorted(_ALLOWED_AGENTS)),
                ),
                response_format="json_object",
                trace_id=payload["context"].get("trace_id") if isinstance(payload["context"], dict) else None,
            )
        )

        if result.success and result.response:
            parsed = self._parse_llm_response(result.response)
            if parsed:
                intent_enum = self._intent_from_string(parsed.get("intent"))
                target_agent = self._select_agent(intent_enum, parsed.get("target_agent"))
                entities = parsed.get("entities") or {}
                if isinstance(entities, dict):
                    self._maybe_track_context(payload.get("context"), entities)
                confidence = self._sanitize_confidence(parsed.get("confidence"))
                requires_clarification = bool(parsed.get("requires_clarification"))
                reasoning = parsed.get("reasoning") or ""
                logger.info(
                    {
                        "event": "semantic_intent_llm_success",
                        "intent": intent_enum.value,
                        "agent": target_agent,
                        "confidence": confidence,
                        "requires_clarification": requires_clarification,
                    }
                )
                return IntentResult(
                    intent=intent_enum,
                    confidence=confidence,
                    target_agent=target_agent,
                    entities=entities,
                    context_resolved=bool(entities),
                    reasoning=reasoning,
                    requires_clarification=requires_clarification,
                    provider=result.provider,
                    model=result.model,
                )

        logger.warning(
            {
                "event": "semantic_intent_llm_failed",
                "error": result.error or "parse_error",
                "response_preview": (result.response[:120] if getattr(result, 'response', None) else None),
            }
        )
        return self._fallback_result(query=query, reason=result.error or "llm_failure")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _select_agent(self, intent: Intent, suggested: Optional[str]) -> str:
        candidate = (suggested or "").strip().lower()
        if candidate in _ALLOWED_AGENTS:
            return candidate
        default_agent = _DEFAULT_AGENT_BY_INTENT.get(intent)
        if default_agent:
            return default_agent
        return "assemble"

    def _intent_from_string(self, value: Optional[str]) -> Intent:
        if not value:
            return Intent.UNKNOWN
        normalized = value.strip().lower()
        return _ALLOWED_INTENTS.get(normalized, Intent.UNKNOWN)

    def _sanitize_confidence(self, value: Any) -> float:
        try:
            confidence = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(confidence, 1.0))

    def _parse_llm_response(self, response: str) -> Optional[Dict[str, Any]]:
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            logger.error({"event": "semantic_intent_invalid_json", "response": response})
            return None

    def _fallback_result(self, *, query: str, reason: str, message: str = "") -> IntentResult:
        if not self.fallback_enabled:
            raise RuntimeError(f"Semantic classification failed without fallback: {reason}")

        logger.info({"event": "semantic_intent_fallback", "reason": reason})
        entities: Dict[str, Any] = {}
        intent = Intent.UNKNOWN

        lower_query = (query or "").lower()
        google_tokens = ("google", "workspace", "gmail", "correo", "correos", "mail", "drive", "calendar", "calendario", "agenda", "evento", "reunion")
        email_tokens = ("correo", "correos", "mail", "gmail", "email")
        drive_tokens = ("drive", "documento", "documentos", "archivo en drive", "gdrive")
        calendar_tokens = ("calendar", "calendario", "evento", "eventos", "reunion", "reunión", "agendar", "agenda")
        send_tokens = ("enviar", "mandar", "remitir", "responder")
        list_tokens = ("listar", "ver", "mostrar", "consultar")
        google_present = any(token in lower_query for token in google_tokens)
        if google_present:
            target_agent = "agente_g"
            intent = Intent.GOOGLE_WORKSPACE
            confidence = 0.55
            if any(token in lower_query for token in email_tokens):
                operation = "list"
                if any(token in lower_query for token in send_tokens):
                    operation = "send"
                elif "habilitar" in lower_query or "activar" in lower_query:
                    operation = "enable_push"
                elif "deshabilitar" in lower_query or "desactivar" in lower_query:
                    operation = "disable_push"
                intent = Intent.GOOGLE_GMAIL
                entities["gmail_operation"] = operation
                if operation == "send":
                    recipients = self._extract_emails(query)
                    if recipients:
                        entities["email_recipients"] = recipients
                if any(token in lower_query for token in list_tokens) and "no leido" in lower_query:
                    entities["gmail_query"] = "is:unread"
            elif any(token in lower_query for token in drive_tokens):
                intent = Intent.GOOGLE_DRIVE
                if any(token in lower_query for token in list_tokens):
                    entities["drive_operation"] = "list"
                elif "crear" in lower_query or "generar" in lower_query:
                    entities["drive_operation"] = "create"
                else:
                    entities["drive_operation"] = "list"
            elif any(token in lower_query for token in calendar_tokens):
                intent = Intent.GOOGLE_CALENDAR
                if "crear" in lower_query or "agendar" in lower_query:
                    entities["calendar_operation"] = "create_event"
                else:
                    entities["calendar_operation"] = "list_events"
            return IntentResult(
                intent=intent,
                confidence=confidence,
                target_agent=target_agent,
                entities=entities,
                context_resolved=bool(entities),
                reasoning=message or f"Fallback classification executed ({reason})",
                requires_clarification=False,
                provider="fallback",
                model=""
            )

        branch_tokens = ("sucursal", "branch", "agencia", "oficina")
        money_tokens = ("saldo", "saldos", "balance", "efectivo", "dinero", "caja", "movimiento")
        branch_present = any(token in lower_query for token in branch_tokens)
        money_present = any(token in lower_query for token in money_tokens)
        greeting_tokens = ("hola", "hello", "buenas", "saludos", "gracias", "buenos dias", "buenas tardes", "buenas noches")
        if any(token in lower_query for token in greeting_tokens):
            intent = Intent.GREETING
            target_agent = "capi_gus"
            confidence = 0.4
        elif branch_present and money_present:
            intent = Intent.DB_OPERATION
            entities["branch_hint"] = query
            target_agent = "capi_datab"
            confidence = 0.5
        elif "resumen" in lower_query:
            intent = Intent.SUMMARY_REQUEST
            target_agent = "summary"
            confidence = 0.4
        elif "outlier" in lower_query or "anom" in lower_query:
            intent = Intent.ANOMALY_QUERY
            target_agent = "anomaly"
            confidence = 0.4
        else:
            target_agent = "assemble"
            confidence = 0.2

        return IntentResult(
            intent=intent,
            confidence=confidence,
            target_agent=target_agent,
            entities=entities,
            context_resolved=False,
            reasoning=message or f"Fallback classification executed ({reason})",
            requires_clarification=intent == Intent.UNKNOWN,
            provider="fallback",
            model=""
        )

    def _maybe_track_context(self, ctx: Optional[Dict[str, Any]], entities: Dict[str, Any]) -> None:
        if not isinstance(ctx, dict):
            return
        session_id = ctx.get("session_id") or ctx.get("thread_id")
        if not session_id:
            return
        branch_name = entities.get("branch_name")
        if branch_name:
            try:
                self.context_manager.track_branch_reference(session_id, branch_name)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning({"event": "context_tracking_failed", "error": str(exc)})

    @staticmethod
    def _extract_emails(text: Optional[str]) -> list[str]:
        if not text:
            return []
        matches = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}", text)
        seen = set()
        emails: list[str] = []
        for match in matches:
            normalized = match.lower()
            if normalized not in seen:
                seen.add(normalized)
                emails.append(normalized)
        if emails:
            return emails
        tokens = [token.strip("()[]{}<>'\".,;") for token in text.split()]
        for token in tokens:
            lowered = token.lower()
            if "@" in lowered and "." in lowered and lowered not in seen:
                seen.add(lowered)
                emails.append(lowered)
        return emails

    def _run_sync(self, coro):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)

        if loop.is_running():
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        return loop.run_until_complete(coro)


__all__ = [
    "SemanticIntentService",
    "IntentResult",
    "ConfidenceLevel",
]
