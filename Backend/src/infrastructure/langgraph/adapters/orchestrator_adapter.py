"""
Async adapter that wraps LangGraphRuntime to match the LangGraph orchestrator interface
expected by the API: process_query(query=..., user_id=..., session_id=...).
"""
from __future__ import annotations

import time
import requests
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from contextlib import suppress
from pathlib import Path

from src.observability.agent_metrics import record_turn_event, record_error_event
from src.infrastructure.langgraph.graph_runtime import LangGraphRuntime
from src.application.services.token_usage_service import TokenUsageService
from src.application.reasoning.llm_reasoner import LLMReasoner
from src.domain.agents.agent_models import ResponseEnvelope, IntentType, ResponseType
from src.core.logging import get_logger
from src.core.file_config import get_available_data_files, get_default_data_file

logger = get_logger(__name__)
token_usage_service = TokenUsageService()


class LangGraphOrchestratorAdapter:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.runtime = LangGraphRuntime(config=config or {})
        self.agent_name = "langgraph_orchestrator"
        self._turn_counters: dict[str, int] = {}
        self.llm_reasoner = LLMReasoner(model=(config or {}).get('llm_model') or "gpt-5")
        # Get port from config, environment, or default to 8000
        import os
        self.api_port = (config or {}).get('api_port',
                                         os.getenv('API_PORT', '8000'))
        logger.info({"event": "adapter_initialized", "agent": self.agent_name, "api_port": self.api_port})
        self._gmail_confirmations: dict[str, str] = {}
        self._gmail_last_responses: dict[str, str] = {}

    def _record_token_usage(self, agent_name: str, usage: Dict[str, Any]) -> None:
        """Persiste el uso de tokens del agente sin recurrir a llamadas HTTP."""
        total_tokens = int(usage.get("total_tokens", 0))
        if total_tokens <= 0:
            return
        cost_usd = float(usage.get("cost_usd", 0.0))
        try:
            result = token_usage_service.record_usage(
                agent_name,
                total_tokens,
                cost_usd,
                prompt_tokens=int(usage.get("prompt_tokens") or 0),
                completion_tokens=int(usage.get("completion_tokens") or 0),
                model=usage.get("model"),
                provider=usage.get("provider", "openai"),
                usage_timestamp=usage.get("timestamp"),
            )
            logger.info({
                "event": "token_usage_recorded",
                "agent": result["agent"],
                "tokens": result["tokens_recorded"],
                "prompt_tokens": result["prompt_tokens_recorded"],
                "completion_tokens": result["completion_tokens_recorded"],
                "total_tokens": result["total_tokens"],
                "cost_usd": result["cost_recorded"],
                "total_cost_usd": result["total_cost"],
            })
        except ValueError as exc:
            logger.warning({"event": "token_usage_skipped", "reason": str(exc), "agent": agent_name, "tokens": total_tokens})
        except Exception as exc:
            logger.error({"event": "token_recording_error", "error": str(exc)})
    def _estimate_tokens_and_cost(self, text: str, response_text: str = "") -> Dict[str, Any]:
        """Estimate input/output tokens and approximate cost as fallback."""
        input_tokens = max(len(text) // 4, 0)
        output_tokens = max(len(response_text) // 4, 0)
        total_tokens = input_tokens + output_tokens
        input_cost = (input_tokens / 1000) * 0.03
        output_cost = (output_tokens / 1000) * 0.06
        total_cost = input_cost + output_cost
        return {
            "prompt_tokens": input_tokens,
            "completion_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cost_usd": round(total_cost, 6),
            "provider": "heuristic",
            "timestamp": datetime.utcnow().isoformat(),
        }
    def _extract_usage_details(self, envelope: ResponseEnvelope, query: str, response_text: str) -> Dict[str, Any]:
        """Resolve real LLM usage from envelope metadata or fall back to heuristic."""
        meta_dict = envelope.meta if isinstance(getattr(envelope, "meta", None), dict) else {}
        candidates = []
        if isinstance(meta_dict.get("llm_usage"), dict):
            candidates.append(meta_dict.get("llm_usage"))
        processing_metrics = meta_dict.get("processing_metrics")
        if isinstance(processing_metrics, dict):
            for key in ("llm_usage", "usage"):
                candidate = processing_metrics.get(key)
                if isinstance(candidate, dict):
                    candidates.append(candidate)
        usage_metadata = getattr(envelope, "usage_metadata", None)
        if isinstance(usage_metadata, dict):
            candidates.append(usage_metadata)
        if isinstance(getattr(envelope, "data", None), dict):
            data_usage = envelope.data.get("llm_usage") or envelope.data.get("usage")
            if isinstance(data_usage, dict):
                candidates.append(data_usage)

        for raw_usage in candidates:
            usage = dict(raw_usage)
            prompt_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
            completion_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
            total_tokens = int(usage.get("total_tokens") or (prompt_tokens + completion_tokens))
            if total_tokens <= 0:
                continue
            model = usage.get("model") or usage.get("llm_model")
            cost = usage.get("cost_usd")
            if cost is None:
                cost = LLMReasoner._estimate_cost(model or "", prompt_tokens, completion_tokens)
            usage.update({
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "cost_usd": float(cost or 0.0),
                "model": model,
                "provider": usage.get("provider", "openai"),
                "timestamp": usage.get("timestamp") or datetime.utcnow().isoformat(),
            })
            return usage

        fallback = self._estimate_tokens_and_cost(query, response_text)
        fallback.setdefault("model", meta_dict.get("llm_model") or meta_dict.get("model"))
        if not fallback.get("provider"):
            fallback["provider"] = "heuristic"
        return fallback

    def _extract_response_text(self, envelope: ResponseEnvelope, session_id: Optional[str] = None) -> str:
        def maybe_override(text: str) -> str:
            if not session_id:
                return text
            stored = self._gmail_confirmations.get(session_id)
            if stored and ("Revisé tu consulta" in text or not text.strip()):
                self._gmail_confirmations.pop(session_id, None)
                return stored
            if stored and stored == text:
                self._gmail_confirmations.pop(session_id, None)
            return text

        data_attr = getattr(envelope, "data", None)
        if isinstance(data_attr, dict):
            gus_payload = data_attr.get("capi_gus")
            if isinstance(gus_payload, dict):
                gus_message = gus_payload.get("message")
                if gus_message:
                    return maybe_override(str(gus_message))

            reasoning_plan = data_attr.get("reasoning_plan")
            if isinstance(reasoning_plan, dict):
                supporting = reasoning_plan.get("supporting_evidence") or {}
                entities = supporting.get("entities") if isinstance(supporting, dict) else {}
                if isinstance(entities, dict):
                    operation_hint = entities.get("gmail_operation")
                    if isinstance(operation_hint, str) and operation_hint.startswith("send"):
                        recipients_entity = entities.get("email_recipients")
                        subject_hint = str(entities.get("email_subject") or "(sin asunto)")
                        if isinstance(recipients_entity, list):
                            recipients = [str(item).strip() for item in recipients_entity if item]
                        elif isinstance(recipients_entity, str):
                            recipients = [recipients_entity]
                        else:
                            recipients = []
                        joined_recipients = ", ".join(recipients) if recipients else "el destinatario indicado"
                        confirmation_message = (
                            f'Te confirmo que envié el correo a {joined_recipients} con asunto "{subject_hint}". ¿Necesitás algo más?'
                        )
                        if session_id:
                            self._gmail_confirmations[session_id] = confirmation_message
                        return confirmation_message

            operation_payload = data_attr.get("operation") or data_attr.get("agente_g_operation")
            parameters_payload = data_attr.get("parameters") or data_attr.get("agente_g_parameters")
            artifact_payload = data_attr.get("artifact") or data_attr.get("agente_g_artifact")
            if isinstance(operation_payload, str) and operation_payload == "send_gmail":
                recipients: list[str] = []
                subject: str = "(sin asunto)"
                if isinstance(parameters_payload, dict):
                    maybe_to = parameters_payload.get("to")
                    if isinstance(maybe_to, list):
                        recipients = [str(item) for item in maybe_to if item]
                    elif isinstance(maybe_to, str):
                        recipients = [maybe_to]
                    if parameters_payload.get("subject"):
                        subject = str(parameters_payload["subject"])
                if not recipients and isinstance(artifact_payload, dict):
                    maybe_recipients = artifact_payload.get("recipients")
                    if isinstance(maybe_recipients, list):
                        recipients = [str(item) for item in maybe_recipients if item]
                    if artifact_payload.get("subject"):
                        subject = str(artifact_payload["subject"])
                joined_recipients = ", ".join(recipients) if recipients else "el destinatario indicado"
                confirmation_message = (
                    f'Te confirmo que envié el correo a {joined_recipients} con asunto "{subject}". ¿Necesitás algo más?'
                )
                if session_id:
                    self._gmail_confirmations[session_id] = confirmation_message
                return confirmation_message

            friendly_fallback = self._compose_friendly_fallback(data_attr, envelope)
            if friendly_fallback:
                confirmation = self._gmail_confirmations.pop(session_id, None) if session_id else None
                if confirmation:
                    return confirmation
                return maybe_override(friendly_fallback)
            response_field = data_attr.get("response")
            if response_field:
                message = maybe_override(str(response_field))
                if session_id and self._is_gmail_response_payload(data_attr):
                    self._gmail_last_responses[session_id] = message
                return message
            message_attr = getattr(envelope, "message", None)
            if message_attr:
                message = maybe_override(str(message_attr))
                if session_id and self._is_gmail_response_payload(data_attr):
                    self._gmail_last_responses[session_id] = message
                return message
            if session_id:
                stored_message = self._gmail_last_responses.get(session_id)
                if stored_message:
                    return stored_message
            return maybe_override(str(data_attr))

        message_attr = getattr(envelope, "message", None)
        if message_attr:
            message = maybe_override(str(message_attr))
            if session_id and self._is_gmail_response_payload(getattr(envelope, "data", {}) or {}):
                self._gmail_last_responses[session_id] = message
            return message

        response_attr = getattr(envelope, "response", None)
        if response_attr:
            return maybe_override(str(response_attr))

        stored = self._gmail_confirmations.pop(session_id, None) if session_id else None
        if stored:
            return stored
        if session_id:
            stored_message = self._gmail_last_responses.get(session_id)
            if stored_message:
                return stored_message
        return ""

    def _compose_friendly_fallback(self, data: Dict[str, Any], envelope: ResponseEnvelope) -> Optional[str]:
        response_field = data.get("response")
        summary_message = data.get("summary_message")
        if response_field and response_field != summary_message:
            return None

        rows = data.get("rows")
        if not isinstance(rows, list) or not rows:
            return None
        first_row = rows[0]
        if not isinstance(first_row, dict):
            return None

        branch = first_row.get("sucursal_nombre") or first_row.get("branch_name") or "la sucursal consultada"
        balance = first_row.get("saldo_total_sucursal")
        theoretical = first_row.get("caja_teorica_sucursal")

        delta_value: Optional[float]
        try:
            delta_value = (float(theoretical) - float(balance)) if balance is not None and theoretical is not None else None
        except (TypeError, ValueError):
            delta_value = None

        balance_text = self._format_currency(balance)
        theoretical_text = self._format_currency(theoretical)
        delta_text = self._format_currency(delta_value) if delta_value is not None else None

        parts: List[str] = []
        if balance_text:
            parts.append(f"El saldo actual de la sucursal '{branch}' es {balance_text}.")
        if theoretical_text:
            if delta_value is not None:
                if delta_value > 0:
                    parts.append(f"La caja teórica proyecta {theoretical_text} y detecto un faltante de {delta_text}.")
                elif delta_value < 0:
                    parts.append(f"La caja teórica proyecta {theoretical_text} y observo un excedente de {delta_text}.")
                else:
                    parts.append(f"La caja teórica coincide con {theoretical_text}.")
            else:
                parts.append(f"La caja teórica proyecta {theoretical_text}.")

        meta = envelope.meta if isinstance(getattr(envelope, "meta", None), dict) else {}
        response_meta = meta.get("response_metadata")
        if isinstance(response_meta, dict):
            alert_msg = response_meta.get("alert_notification")
            if alert_msg:
                normalized = str(alert_msg).strip().rstrip(".")
                if normalized:
                    parts.append(f"{normalized}.")

        file_path = data.get("file_path")
        closing_question: str
        if isinstance(file_path, str) and file_path:
            try:
                file_name = Path(file_path).name
            except Exception:
                file_name = None
            if file_name:
                closing_question = f"¿Querés que guarde este análisis en el escritorio como {file_name}?"
            else:
                closing_question = "¿Querés que guarde este análisis en el escritorio o seguimos con otra consulta?"
        else:
            closing_question = "¿Querés que guarde este análisis en el escritorio o seguimos con otra consulta?"

        if not parts:
            return None

        parts.append(closing_question)
        return " ".join(part.strip() for part in parts if part)

    @staticmethod
    @staticmethod
    def _parse_bool(value: Any, default: bool = False) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        text = str(value).strip().lower()
        if text in {'1', 'true', 'yes', 'y', 'on'}:
            return True
        if text in {'0', 'false', 'no', 'n', 'off'}:
            return False
        return default

    def _offline_mode_enabled(self) -> bool:
        return self._parse_bool(os.getenv('AGENTE_G_OFFLINE_MODE'), False)

    @staticmethod
    def _is_gmail_response_payload(data: Dict[str, Any]) -> bool:
        if not isinstance(data, dict):
            return False
        operation = data.get("operation") or data.get("agente_g_operation")
        if isinstance(operation, str) and operation.startswith("list_gmail"):
            return True
        messages = data.get("messages")
        if isinstance(messages, list) and messages:
            return True
        artifact = data.get("artifact") or data.get("agente_g_artifact")
        if isinstance(artifact, dict) and artifact.get("type") == "email" and isinstance(artifact.get("items"), list):
            return True
        return False

    def _load_offline_mailbox(self) -> List[Dict[str, Any]]:
        cache_attr = '_offline_mailbox_cache'
        if hasattr(self, cache_attr):
            return getattr(self, cache_attr)

        default_path = Path('/app/ia_workspace/data/fallback/gmail_mailbox_sample.json')
        configured = os.getenv('AGENTE_G_FALLBACK_PATH')
        path = Path(configured).resolve() if configured else default_path
        try:
            raw = json.loads(path.read_text(encoding='utf-8'))
            messages = raw.get('messages') if isinstance(raw, dict) else raw
            if not isinstance(messages, list):
                raise ValueError('Fallback mailbox must be a list of messages')
        except Exception as exc:
            logger.warning(
                {
                    'event': 'offline_mailbox_load_failed',
                    'path': str(path),
                    'error': repr(exc),
                }
            )
            messages = [
                {
                    'id': 'offline-1',
                    'thread_id': 'offline-thread-1',
                    'snippet': 'Lucas confirmó que necesita trasladar 150.000 desde la bóveda hacia la sucursal.',
                    'from': 'lucasnoa94@gmail.com',
                    'subject': 'Re: Solicitud de distribución de efectivo hacia la sucursal',
                    'date': 'Mon, 13 Oct 2025 21:34:25 -0300',
                    'received_at': '2025-10-13T00:34:25',
                    'unread': False,
                    'amount_total': 150000.0,
                    'amounts': [{'raw': '$150.000', 'value': 150000.0, 'currency': 'ARS'}],
                }
            ]

        setattr(self, cache_attr, messages)
        return messages

    @staticmethod
    def _format_currency(amount: Optional[float]) -> str:
        if amount is None:
            return ''
        sign = '-' if amount < 0 else ''
        absolute = abs(amount)
        integer_part, decimal_part = f"{absolute:,.2f}".split('.')
        integer_part = integer_part.replace(',', '.')
        return f"{sign}{integer_part},{decimal_part}"
    def _detects_gmail_intent(self, query: str) -> bool:
        lowered = (query or '').lower()
        keywords = ('gmail', 'correo', 'mail', 'inbox', 'mensaje')
        return any(keyword in lowered for keyword in keywords)
    def _build_offline_gmail_response(self, *, query: str, user_id: str, session_id: str, max_results: int = 5) -> ResponseEnvelope:
        mailbox = self._load_offline_mailbox()[:max_results]

        total_amount = 0.0
        has_amount = False
        unread_count = 0
        summarized_messages: List[Dict[str, Any]] = []
        for message in mailbox:
            amount = message.get('amount_total')
            if amount:
                total_amount += float(amount)
                has_amount = True
            if message.get('unread'):
                unread_count += 1
            summarized_messages.append(message)

        descriptor = 'correos recibidos'
        summary_line = f"Revisé {len(summarized_messages)} {descriptor} (no leídos: {unread_count})."
        amount_line = (
            f"Monto total detectado: {self._format_currency(total_amount)}."
            if has_amount
            else 'No se detectaron montos válidos en los correos recibidos.'
        )
        detail_lines = []
        for message in summarized_messages[:3]:
            subject = message.get('subject') or '(sin asunto)'
            monto = message.get('amount_total')
            monto_txt = self._format_currency(monto) if monto is not None else 'sin monto detectado'
            unread_tag = ' (sin leer)' if message.get('unread') else ''
            detail_lines.append(f"- {subject}{unread_tag}: {monto_txt}")

        response_text = ' '.join(part.strip() for part in [summary_line, amount_line, ' '.join(detail_lines)] if part).strip()

        data = {
            'messages': summarized_messages,
            'query': query,
            'label_ids': None,
            'total_amount': total_amount if has_amount else None,
            'unread_count': unread_count,
            'max_results': max_results,
            'response': response_text,
            'branch_totals': {},
            'applied_filters': {
                'include_unread': True,
                'include_read': True,
                'after': None,
                'before': None,
            },
        }

        meta = {
            'status': 'completed',
            'completed_nodes': ['offline', 'finalize'],
            'intent': 'google_gmail',
            'intent_confidence': 1.0,
            'response_metadata': {
                'offline_mode': True,
                'agente_g_operation': 'list_gmail',
                'agente_g_parameters': {},
            },
        }

        intent_enum = getattr(IntentType, 'GOOGLE_GMAIL', IntentType.QUERY)
        response_type = getattr(ResponseType, 'SUCCESS', ResponseType.SUCCESS)

        return ResponseEnvelope(
            trace_id=f'offline-{session_id}',
            response_type=response_type,
            intent=intent_enum,
            message=response_text,
            data=data,
            meta=meta,
        )

    def _resolve_active_agent(self, envelope: ResponseEnvelope, response_text: str) -> str:
        meta = envelope.meta if isinstance(getattr(envelope, "meta", None), dict) else {}
        completed_nodes = meta.get("completed_nodes")
        if isinstance(completed_nodes, (list, tuple)):
            for agent_node in ("capi_gus", "branch", "anomaly"):
                if agent_node in completed_nodes:
                    return agent_node
        if hasattr(envelope, "data") and isinstance(envelope.data, dict):
            if envelope.data.get("agent"):
                return str(envelope.data["agent"])
            stage = envelope.data.get("workflow_stage")
            if isinstance(stage, str):
                lowered = stage.lower()
                if "capi_gus" in lowered or "gus" in lowered or "summary" in lowered:
                    return "capi_gus"
                if "branch" in lowered:
                    return "branch"
                if "anomaly" in lowered:
                    return "anomaly"
                if "capi_gus" in lowered or "gus" in lowered:
                    return "capi_gus"
        return "unknown"

    async def _maybe_enhance_with_llm(
        self,
        *,
        envelope: ResponseEnvelope,
        query: str,
        response_text: str,
        active_agent: str,
        usage_details: Dict[str, Any],
        trace_id: Optional[str],
    ) -> Dict[str, Any]:
        client = getattr(self.llm_reasoner, "_client", None)
        if not client or usage_details.get("provider") != "heuristic":
            return usage_details

        try:
            prompt = self._build_llm_prompt(query, response_text, active_agent)
            context_data = {"agent": active_agent or "unknown", "response_preview": response_text[:600]}
            llm_result = await self.llm_reasoner.reason(
                query=prompt,
                context_data=context_data,
                trace_id=trace_id,
                max_output_tokens=512,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning({"event": "llm_enhancement_failed", "error": str(exc), "trace_id": trace_id})
            return usage_details

        if not llm_result.success:
            logger.info({"event": "llm_enhancement_skipped", "reason": llm_result.error, "trace_id": trace_id})
            return usage_details

        if llm_result.response:
            setattr(envelope, "message", llm_result.response)
        meta_dict = envelope.meta if isinstance(getattr(envelope, "meta", None), dict) else {}
        processing_metrics = meta_dict.setdefault("processing_metrics", {})
        processing_metrics["llm_model"] = llm_result.model
        processing_metrics["llm_latency_ms"] = int(llm_result.processing_time * 1000)
        processing_metrics["llm_confidence"] = llm_result.confidence_score
        meta_dict["llm_usage"] = llm_result.usage_metadata
        setattr(envelope, "meta", meta_dict)
        if isinstance(envelope.data, dict):
            envelope.data.setdefault("llm_usage", llm_result.usage_metadata)

        usage = dict(llm_result.usage_metadata)
        usage.setdefault("model", llm_result.model)
        usage.setdefault("provider", llm_result.provider)
        usage.setdefault("timestamp", usage_details.get("timestamp") or datetime.utcnow().isoformat())
        usage["cost_usd"] = llm_result.cost_usd
        usage["prompt_tokens"] = llm_result.prompt_tokens
        usage["completion_tokens"] = llm_result.completion_tokens
        usage["total_tokens"] = llm_result.total_tokens
        logger.info({
            "event": "llm_enhancement_completed",
            "trace_id": trace_id,
            "model": llm_result.model,
            "prompt_tokens": llm_result.prompt_tokens,
            "completion_tokens": llm_result.completion_tokens,
            "total_tokens": llm_result.total_tokens,
            "cost_usd": llm_result.cost_usd,
        })
        return usage

    @staticmethod
    def _build_llm_prompt(user_query: str, current_response: str, agent_name: str) -> str:
        query_excerpt = (user_query or "").strip()[:600]
        response_excerpt = (current_response or "").strip()[:1200]
        agent_label = agent_name or "general"
        return (
            "Eres un asistente financiero profesional.\n"
            f"Consulta original: {query_excerpt}\n"
            f"Borrador de respuesta del agente {agent_label}: {response_excerpt}\n"
            "Reescribe la mejor respuesta posible, céntrate en hechos y evita inventar datos."
        )

    def _next_turn_id(self, session_id: str) -> int:
        current = self._turn_counters.get(session_id, 0) + 1
        if current > 1_000_000:
            current = 1
        self._turn_counters[session_id] = current
        return current

    async def process_query(
        self,
        *,
        query: str,
        user_id: str,
        session_id: str,
        channel: str | None = None,
        trace_id: str | None = None,
    ) -> ResponseEnvelope:
        offline_mode = self._offline_mode_enabled()
        if offline_mode and self._detects_gmail_intent(query):
            envelope = self._build_offline_gmail_response(query=query, user_id=user_id, session_id=session_id)
            setattr(envelope, "processing_time_ms", 0)
            setattr(envelope, "agent_name", self.agent_name)
            setattr(envelope, "tokens_used", 0)
            setattr(envelope, "cost_estimate", 0.0)
            return envelope

        start = time.time()
        if session_id:
            self._gmail_last_responses.pop(session_id, None)
        if self._offline_mode_enabled() and self._detects_gmail_intent(query):

            envelope = self._build_offline_gmail_response(

                query=query,

                user_id=user_id,

                session_id=session_id,

            )

            setattr(envelope, 'processing_time_ms', 0)

            setattr(envelope, 'agent_name', self.agent_name)

            setattr(envelope, 'tokens_used', 0)

            setattr(envelope, 'cost_estimate', 0.0)

            return envelope



        turn_id = self._next_turn_id(session_id)
        logger.info({
            "event": "adapter_process_query_start",
            "user_id": user_id,
            "session_id": session_id,
            "turn_id": turn_id,
            "trace_id": trace_id,
        })

        try:
            envelope = self.runtime.process_query(session_id=session_id, user_id=user_id, text=query)
        except Exception as exc:
            elapsed_ms = int((time.time() - start) * 1000)
            record_error_event(
                agent_name="unknown",
                session_id=session_id,
                turn_id=turn_id,
                error_code=exc.__class__.__name__,
                error_message=str(exc),
                latency_ms=elapsed_ms,
                user_id=user_id,
                channel=channel or "api",
                metadata={"query_preview": query[:120]},
                trace_id=trace_id,
            )
            logger.exception(
                "adapter_process_query_failed",
                extra={"session_id": session_id, "user_id": user_id, "turn_id": turn_id, "trace_id": trace_id},
            )
            raise

        if trace_id and not getattr(envelope, "trace_id", None):
            with suppress(Exception):
                setattr(envelope, "trace_id", trace_id)

        response_text = self._extract_response_text(envelope, session_id)
        if response_text:
            with suppress(Exception):
                setattr(envelope, "message", response_text)
                if isinstance(envelope.data, dict):
                    envelope.data.setdefault("response", response_text)
        active_agent = self._resolve_active_agent(envelope, response_text)

        effective_trace_id = getattr(envelope, "trace_id", None) or trace_id
        usage_details = self._extract_usage_details(envelope, query, response_text)
        usage_details = await self._maybe_enhance_with_llm(
            envelope=envelope,
            query=query,
            response_text=response_text,
            active_agent=active_agent,
            usage_details=usage_details,
            trace_id=effective_trace_id,
        )
        response_text = self._extract_response_text(envelope)
        if response_text:
            with suppress(Exception):
                setattr(envelope, "message", response_text)
                if isinstance(envelope.data, dict):
                    envelope.data.setdefault("response", response_text)
        input_tokens = int(usage_details.get("prompt_tokens", 0))
        output_tokens = int(usage_details.get("completion_tokens", 0))
        tokens_used = int(usage_details.get("total_tokens", input_tokens + output_tokens))
        cost_estimate = float(usage_details.get("cost_usd", 0.0))

        elapsed_ms = int((time.time() - start) * 1000)
        try:
            setattr(envelope, "agent_name", self.agent_name)
            setattr(envelope, "processing_time_ms", elapsed_ms)
            setattr(envelope, "tokens_used", tokens_used)
            setattr(envelope, "cost_estimate", cost_estimate)
        except Exception:
            pass

        meta_dict = envelope.meta if isinstance(envelope.meta, dict) else {}
        response_type_value = (
            envelope.response_type.value
            if hasattr(envelope.response_type, "value")
            else str(envelope.response_type)
        )
        intent_value = (
            envelope.intent.value if hasattr(envelope.intent, "value") else str(envelope.intent)
        )
        success = envelope.is_success() if hasattr(envelope, "is_success") else None
        channel_value = channel or "api"
        processing_metrics = meta_dict.get("processing_metrics")
        model_name = (
            meta_dict.get("model")
            or meta_dict.get("llm_model")
            or (processing_metrics or {}).get("llm_model")
            or usage_details.get("model")
        )

        if model_name and not usage_details.get("model"):
            usage_details["model"] = model_name
        self._record_token_usage(active_agent or self.agent_name, usage_details)

        metadata_payload: Dict[str, Any] = {}
        if active_agent:
            metadata_payload["active_agent"] = active_agent
        completed_nodes = meta_dict.get("completed_nodes")
        if completed_nodes:
            metadata_payload["completed_nodes"] = completed_nodes
        if isinstance(processing_metrics, dict) and processing_metrics:
            metadata_payload["processing_metrics"] = processing_metrics
        if usage_details:
            metadata_payload["llm_usage"] = usage_details
        intent_confidence = meta_dict.get("intent_confidence")
        if intent_confidence is not None:
            metadata_payload["intent_confidence"] = intent_confidence
        if query:
            metadata_payload["query_preview"] = query[:120]
        if response_text:
            metadata_payload["response_preview"] = response_text[:120]
        if envelope.errors:
            metadata_payload["errors"] = envelope.errors

        record_turn_event(
            agent_name=active_agent,
            session_id=session_id,
            turn_id=turn_id,
            latency_ms=elapsed_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_estimate,
            user_id=user_id,
            channel=channel_value,
            model=model_name,
            trace_id=effective_trace_id,
            intent=intent_value,
            response_type=response_type_value,
            success=success,
            metadata=metadata_payload or None,
        )

        if success is False:
            error_message = envelope.message if getattr(envelope, "message", None) else "Agent returned error"
            if envelope.errors:
                error_message = str(envelope.errors[0])
            failure_metadata = {
                "errors": envelope.errors if envelope.errors else None,
                "response_type": response_type_value,
            }
            failure_metadata = {key: value for key, value in failure_metadata.items() if value}
            record_error_event(
                agent_name=active_agent or "unknown",
                session_id=session_id,
                turn_id=turn_id,
                error_code="agent_response_error",
                error_message=error_message,
                latency_ms=elapsed_ms,
                user_id=user_id,
                channel=channel_value,
                trace_id=effective_trace_id,
                intent=intent_value,
                metadata=failure_metadata or None,
            )

        logger.info(
            {
                "event": "adapter_process_query_end",
                "elapsed_ms": elapsed_ms,
                "active_agent": active_agent,
                "tokens_used": tokens_used,
                "cost_estimate": round(cost_estimate, 6),
                "turn_id": turn_id,
                "trace_id": effective_trace_id,
            }
        )
        return envelope

    # ------------------------------------------------------------------
    # Session helpers for REST API compatibility
    # ------------------------------------------------------------------

    def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        return self.runtime.get_session_history(session_id)

    def get_active_sessions(self) -> List[str]:
        return self.runtime.get_active_sessions()

    def clear_session_history(self, session_id: str) -> None:
        self.runtime.clear_session_history(session_id)

    async def resume_human_gate(self, *, session_id: str, decision: Dict[str, Any]) -> ResponseEnvelope:
        """Resume a paused workflow after human approval."""
        return self.runtime.resume_human_gate(session_id=session_id, resume_payload=decision)

    async def load_data_use_case(self, file_path: str) -> Dict[str, Any]:
        """
        Load data from specified file for backwards compatibility with API.

        Args:
            file_path: Path to the data file to load

        Returns:
            Dictionary with success flag and data information
        """
        start = time.time()
        logger.info({"event": "load_data_start", "file_path": file_path})

        try:
            # Verify file exists and get file info
            available_files = get_available_data_files()
            if not available_files:
                logger.warning({"event": "load_data_no_files"})
                return {
                    "success": False,
                    "message": "No data files available in Backend/ia_workspace/data/",
                    "data": {}
                }

            # Find the specific file or use default
            target_file = None
            for file_info in available_files:
                if file_info["path"] == file_path or file_info["name"] in file_path:
                    target_file = file_info
                    break

            if not target_file:
                target_file = available_files[0]  # Use first available file
                logger.info({"event": "load_data_fallback", "using_file": target_file["name"]})

            # CRITICAL FIX: Load REAL data using existing repository infrastructure
            from src.infrastructure.repositories.repository_provider import RepositoryProvider
            from src.domain.services.financial_service import FinancialAnalysisService

            # Use existing repository to load real data
            repo_provider = RepositoryProvider()
            financial_repo = repo_provider.get_financial_repository()
            data_repo = repo_provider.get_data_file_repository()

            # Load real financial records from CSV file
            real_records = await data_repo.load_from_file(file_path)
            logger.info({"event": "real_data_loaded", "record_count": len(real_records)})

            # Save to financial repository for further processing
            if real_records:
                await financial_repo.save_many(real_records)

            # Use domain service to calculate real metrics
            financial_metrics = FinancialAnalysisService.calculate_financial_metrics(real_records)
            branch_summaries = FinancialAnalysisService.calculate_branch_summary(real_records)

            # Convert records to dict format for JSON serialization
            records_data = [record.to_dict() if hasattr(record, 'to_dict') else record.__dict__ for record in real_records]

            # Calculate real aggregates
            total_amount = sum(float(getattr(record, 'monto', 0) or 0) for record in real_records)
            income_records = [r for r in real_records if getattr(r, 'monto', 0) and float(getattr(r, 'monto')) > 0]
            expense_records = [r for r in real_records if getattr(r, 'monto', 0) and float(getattr(r, 'monto')) < 0]

            result = {
                "success": True,
                "message": f"Real data loaded from {target_file['name']} - {len(real_records)} records",
                "data": {
                    "json_data": records_data,  # REAL data from CSV
                    "financial_records": real_records,  # Domain objects
                    "financial_metrics": financial_metrics,  # Real calculated metrics
                    "branch_summaries": branch_summaries,  # Real branch analysis
                    "anomalies": [],  # Will be calculated by domain service
                    "summary": {
                        "total_records": len(real_records),  # REAL count
                        "file_name": target_file["name"],
                        "file_type": target_file["type"],
                        "file_size": target_file["size"],
                        "total_amount": total_amount,  # REAL amount
                        "income_count": len(income_records),  # REAL income count
                        "expense_count": len(expense_records)  # REAL expense count
                    },
                    "dashboard": {
                        "files_loaded": 1,
                        "total_files": len(available_files),
                        "last_modified": target_file["modified"].isoformat(),
                        "data_status": "loaded_with_real_data"  # Status updated
                    },
                    "records_count": len(real_records)  # REAL record count
                }
            }

            elapsed_ms = int((time.time() - start) * 1000)
            logger.info({
                "event": "load_data_success",
                "file": target_file["name"],
                "elapsed_ms": elapsed_ms
            })

            return result

        except Exception as e:
            logger.error({"event": "load_data_error", "error": str(e)})
            return {
                "success": False,
                "message": f"Error loading data: {str(e)}",
                "data": {}
            }
