"""
Ruta: Backend/src/infrastructure/langgraph/nodes/capi_gus_node.py
Descripción: Nodo responsable de entregar la respuesta final al usuario en tono amigable.
Estado: Activo
Objetivo: Tomar los resultados de Capi DataB y Capi El Cajas, combinarlos y generar
          una narrativa clara que responda la consulta del usuario.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import random
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

from src.application.reasoning.llm_reasoner import LLMReasoner, LLMReasoningResult
from src.core.config import get_settings
from src.core.logging import get_logger
from src.infrastructure.langgraph.nodes.base import GraphNode
from src.infrastructure.langgraph.state_schema import GraphState, StateMutator
from src.domain.contracts.intent import Intent

logger = get_logger(__name__)


class CapiGusNode(GraphNode):
    """Nodo que sintetiza los resultados del flujo y entrega una respuesta ejecutiva."""

    def __init__(self, name: str = "capi_gus", reasoner: Optional[LLMReasoner] = None) -> None:
        super().__init__(name=name)
        self._is_agent_node = True
        self._reasoner: Optional[LLMReasoner] = reasoner
        self._llm_disabled: bool = False
        self._greeting_responses = [
            "¡Hola! ¿Cómo puedo ayudarte hoy?",
            "¡Buen día! ¿Te gustaría un resumen financiero o revisamos alguna sucursal?",
            "¡Hola! Estoy listo para ayudarte con tus análisis.",
            "¡Saludos! ¿Quieres que revisemos saldos, sucursales o anomalías?",
        ]
        self._conversation_responses = [
            "Siempre es bueno conversar; si querés puedo preparar un resumen o revisar una sucursal.",
            "Estoy a tu disposición para analizar datos financieros cuando lo necesites.",
            "Gracias por el mensaje. ¿Te ayudo con un resumen, un análisis de sucursal o detección de anomalías?",
            "Encantado de seguir charlando, pero también puedo generar reportes o detectar anomalías.",
        ]
        self._greeting_keywords = {"hola", "hello", "buenas", "saludos", "buenos dias", "buenas tardes", "buenas noches"}
        self._gratitude_keywords = {"gracias", "thank", "excelente", "perfecto", "genial"}
        self._vdg_keywords = {"vdg", "viernes de garage", "viernes del garage", "viernes garage"}

    def run(self, state: GraphState) -> GraphState:
        start_time = time.time()
        logger.info({"event": "capi_gus_node_start", "session_id": state.session_id, "trace_id": state.trace_id})

        self._emit_agent_start(state)
        is_conversation = self._should_handle_conversation(state)
        if is_conversation:
            message, artifact = self._handle_conversation(state)
            usage = None
        else:
            message, artifact, usage = self._compose_response(state)

        updated = StateMutator.update_field(state, "current_node", self.name)
        updated = StateMutator.update_field(updated, "response_message", message)
        metadata_payload: Dict[str, Any] = {
            "agent_type": "capi_gus",
            "speaker": "capi_gus",
            "friendly_summary": True,
            "agent_raw_message": message,
            "result_summary": message,
        }
        if is_conversation:
            metadata_payload["interaction_mode"] = "conversation"
        if artifact.get("base_message"):
            metadata_payload["capi_gus_base_message"] = artifact["base_message"]
        if usage:
            metadata_payload["capi_gus_llm_usage"] = usage
        updated = StateMutator.merge_dict(updated, "response_metadata", metadata_payload)
        routing_target = "assemble" if is_conversation else "human_gate"
        updated = StateMutator.update_field(updated, "routing_decision", routing_target)
        if artifact:
            shared_update = {self.name: artifact}
            existing_shared = getattr(state, "shared_artifacts", {}) or {}
            datab_bucket = existing_shared.get("capi_datab") if isinstance(existing_shared, dict) else None
            if not is_conversation and isinstance(datab_bucket, dict):
                datab_update = dict(datab_bucket)
                datab_update["summary_message"] = message
                shared_update["capi_datab"] = datab_update
            updated = StateMutator.merge_dict(updated, "shared_artifacts", shared_update)
            updated = StateMutator.merge_dict(
                updated,
                "response_data",
                {"response": message, self.name: artifact},
            )

        updated = StateMutator.append_to_list(updated, "completed_nodes", self.name)

        duration_ms = int((time.time() - start_time) * 1000)
        logger.info(
            {
                "event": "capi_gus_node_end",
                "session_id": state.session_id,
                "trace_id": state.trace_id,
                "duration_ms": duration_ms,
                "message_preview": message[:160],
            }
        )
        self._emit_agent_end(updated, success=True, duration_ms=duration_ms)
        return updated

    # ------------------------------------------------------------------
    # Response composition helpers
    # ------------------------------------------------------------------

    def _should_handle_conversation(self, state: GraphState) -> bool:
        intent = getattr(state, 'detected_intent', None)
        if isinstance(intent, Intent):
            if intent in {Intent.SMALL_TALK, Intent.GREETING}:
                return True
        elif isinstance(intent, str) and intent.lower() in {'small_talk', 'greeting'}:
            return True

        metadata = getattr(state, 'response_metadata', {}) or {}
        semantic_result = metadata.get('semantic_result') or {}
        intent_hint = str(semantic_result.get('intent') or '').lower()
        target_hint = str(semantic_result.get('target_agent') or '').lower()
        if intent_hint in {'small_talk', 'greeting'} or target_hint in {'smalltalk'}:
            return True

        query = (state.original_query or '').lower()
        if any(token in query for token in self._greeting_keywords | self._gratitude_keywords):
            return True
        return False

    def _handle_conversation(self, state: GraphState) -> Tuple[str, Dict[str, Any]]:
        query = (state.original_query or '').lower()
        if any(token in query for token in self._vdg_keywords):
            response = (
                "Los Capi Agentes son el equipo más vibrante de Viernes de Garage: "
                "mezclamos datos, calle y pura onda para levantar cualquier demo y enamorar al público."
            )
        elif any(token in query for token in self._greeting_keywords):
            response = random.choice(self._greeting_responses)
        elif any(token in query for token in self._gratitude_keywords):
            response = random.choice(self._conversation_responses)
        else:
            response_pool = self._greeting_responses + self._conversation_responses
            response = random.choice(response_pool)

        artifact = {
            'type': 'conversation_reply',
            'agent': 'capi_gus',
            'mode': 'conversation',
            'message': response,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'query': state.original_query,
        }
        return response, artifact

    def _compose_response(self, state: GraphState) -> Tuple[str, Dict[str, Any], Optional[Dict[str, Any]]]:
        shared = getattr(state, "shared_artifacts", {}) or {}
        metadata = getattr(state, "response_metadata", {}) or {}

        def _build_gmail_confirmation(recipient_list: list[str], subject_line: str) -> Tuple[str, Dict[str, Any]]:
            subject_text = subject_line if subject_line else "(sin asunto)"
            joined = ", ".join(recipient_list) if recipient_list else "el destinatario indicado"
            message_text = f"Te confirmo que envié el correo a {joined} con asunto \"{subject_text}\". ¿Necesitás algo más?"
            artifact_payload = {
                "type": "gmail_send_confirmation",
                "agent": "agente_g",
                "recipients": recipient_list,
                "subject": subject_text,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "query": state.original_query,
            }
            return message_text, artifact_payload

        agente_operation = metadata.get("agente_g_operation")
        if isinstance(agente_operation, str) and agente_operation == "send_gmail":
            parameters = metadata.get("agente_g_parameters") or {}
            if not isinstance(parameters, dict):
                parameters = {}
            recipients = parameters.get("to") or []
            if isinstance(recipients, str):
                recipients = [recipients]
            elif not isinstance(recipients, list):
                recipients = []
            recipients = [str(item).strip() for item in recipients if item]
            subject = str(parameters.get("subject") or "(sin asunto)")
            message, artifact = _build_gmail_confirmation(recipients, subject)
            return message, artifact, None

        agente_shared = shared.get("agente_g") if isinstance(shared, dict) else None
        if isinstance(agente_shared, list):
            for raw_artifact in reversed(agente_shared):
                if isinstance(raw_artifact, dict) and raw_artifact.get("type") == "email_sent":
                    recipients = raw_artifact.get("recipients")
                    subject = raw_artifact.get("subject") or "(sin asunto)"
                    if isinstance(recipients, list):
                        recipient_list = [str(item).strip() for item in recipients if item]
                    elif isinstance(recipients, str):
                        recipient_list = [recipients]
                    else:
                        recipient_list = []
                    message, artifact = _build_gmail_confirmation(recipient_list, str(subject))
                    artifact.update(raw_artifact)
                    return message, artifact, None

        datab_bucket = shared.get("capi_datab") if isinstance(shared, dict) else {}
        elcajas_bucket = shared.get("capi_elcajas") if isinstance(shared, dict) else {}

        primary_row = self._select_primary_row(datab_bucket)
        branch_name = self._resolve_branch_name(primary_row, datab_bucket, metadata, state)
        balance_value, balance_text = self._extract_value(
            primary_row,
            ("saldo_total_sucursal", "saldo_total", "total_saldo", "balance_total"),
        )
        theoretical_value, theoretical_text = self._extract_value(
            primary_row,
            ("caja_teorica_sucursal", "saldo_teorico", "teorico_total"),
        )
        delta_value = self._compute_delta(balance_value, theoretical_value)
        distribution_raw = self._build_distribution_payload(primary_row)
        distribution_text = self._build_distribution_text(primary_row, distribution_raw)
        distribution_breakdown = {label: self._decimal_to_float(value) for label, value in distribution_raw.items()}
        alert_text, alert_payload = self._summarize_alerts(metadata, elcajas_bucket)

        export_path = datab_bucket.get("export_file") if isinstance(datab_bucket, dict) else None
        export_name = Path(export_path).name if export_path else None

        original_query = getattr(state, "original_query", "") or getattr(state, "user_query", "")

        base_message, closing_question = self._build_base_message(
            branch_name=branch_name,
            balance_text=balance_text,
            balance_value=balance_value,
            theoretical_text=theoretical_text,
            theoretical_value=theoretical_value,
            delta_value=delta_value,
            distribution_text=distribution_text,
            alert_text=alert_text,
            alert_payload=alert_payload,
            export_name=export_name,
            original_query=original_query,
        )

        context_snapshot: Dict[str, Any] = {
            "branch": branch_name,
            "balance_value": self._decimal_to_float(balance_value),
            "balance_text": balance_text,
            "theoretical_value": self._decimal_to_float(theoretical_value),
            "theoretical_text": theoretical_text,
            "difference_value": self._decimal_to_float(delta_value),
            "difference_text": self._format_currency(delta_value) if delta_value is not None else None,
            "distribution_text": distribution_text,
            "distribution_breakdown": distribution_breakdown,
            "alert_summary": alert_payload,
            "raw_alert_text": alert_text,
            "export_file": export_name,
            "previous_summary": metadata.get("result_summary")
                or metadata.get("agent_raw_message")
                or (datab_bucket.get("summary_message") if isinstance(datab_bucket, dict) else None),
            "original_query": original_query,
        }

        llm_message, usage = self._generate_ai_message(
            base_message=base_message,
            closing_question=closing_question,
            context_snapshot=context_snapshot,
            trace_id=state.trace_id,
        )

        final_message = llm_message or base_message
        artifact: Dict[str, Any] = {
            "type": "conversation_summary",
            "agent": "capi_gus",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "query": original_query,
            "message": final_message,
            "base_message": base_message,
            "branch": branch_name,
            "balance": self._decimal_to_float(balance_value),
            "balance_text": balance_text,
            "theoretical_balance": self._decimal_to_float(theoretical_value),
            "theoretical_balance_text": theoretical_text,
            "delta": self._decimal_to_float(delta_value),
            "delta_text": self._format_currency(delta_value) if delta_value is not None else None,
            "distribution_detail": distribution_text,
            "distribution_breakdown": distribution_breakdown,
            "alerts": alert_payload,
            "raw_alert_text": alert_text,
            "closing_prompt": closing_question,
            "llm_generated": bool(llm_message),
            "context_snapshot": context_snapshot,
        }
        if export_name:
            artifact["export_file"] = export_name
        if export_path:
            artifact["export_path"] = export_path
        if usage:
            artifact["llm_usage"] = usage

        return final_message, artifact, usage

    def _build_base_message(
        self,
        *,
        branch_name: Optional[str],
        balance_text: Optional[str],
        balance_value: Optional[Decimal],
        theoretical_text: Optional[str],
        theoretical_value: Optional[Decimal],
        delta_value: Optional[Decimal],
        distribution_text: Optional[str],
        alert_text: Optional[str],
        alert_payload: Dict[str, Any],
        export_name: Optional[str],
        original_query: str,
    ) -> Tuple[str, str]:
        message_parts: list[str] = []

        if balance_text:
            if branch_name:
                message_parts.append(f"El saldo total de la sucursal '{branch_name}' es {balance_text}.")
            else:
                message_parts.append(f"El saldo total disponible es {balance_text}.")
        else:
            if original_query:
                message_parts.append(
                    f"No pude generar un resumen actualizado de los datos para responder \"{original_query}\"."
                )
            else:
                message_parts.append("No pude generar un resumen actualizado de los datos solicitados.")
            fallback_question = "\u00bfPod\u00e9s darme un poco m\u00e1s de contexto o la sucursal que quer\u00e9s revisar?"
            readable_message = " ".join(part.strip() for part in message_parts if part).strip()
            readable_message = f"{readable_message} {fallback_question}".strip()
            return readable_message, fallback_question

        if theoretical_text:
            if delta_value is None or delta_value == 0:
                message_parts.append(f"La caja te\u00f3rica marca {theoretical_text}.")
            else:
                gap_text = self._format_currency(abs(delta_value))
                if delta_value > 0:
                    message_parts.append(
                        f"La caja te\u00f3rica marca {theoretical_text} y aparece un faltante de {gap_text} frente al saldo operativo."
                    )
                else:
                    message_parts.append(
                        f"La caja te\u00f3rica marca {theoretical_text} y aparece un excedente de {gap_text} frente al saldo operativo."
                    )

        if distribution_text:
            message_parts.append(f"Distribuci\u00f3n actual: {distribution_text}.")

        if alert_text:
            message_parts.append(alert_text)
        else:
            alert_count = alert_payload.get("count") if isinstance(alert_payload, dict) else None
            if isinstance(alert_count, int) and alert_count == 0:
                message_parts.append("No detect\u00e9 incidencias relevantes en la operatoria de caja.")

        closing_question = self._build_closing_question(export_name, branch_name)
        message_parts.append(closing_question)

        readable_message = " ".join(part.strip() for part in message_parts if part).strip()
        return readable_message, closing_question

    def _build_closing_question(self, export_name: Optional[str], branch_name: Optional[str]) -> str:
        if export_name and branch_name:
            return (
                f"\u00bfQuer\u00e9s que deje guardado el informe {export_name} de {branch_name} en el escritorio?"
            )
        if export_name:
            return f"\u00bfQuer\u00e9s que deje guardado el informe {export_name} en el escritorio?"
        if branch_name:
            return f"\u00bfQuer\u00e9s que guarde este an\u00e1lisis de {branch_name} en el escritorio?"
        return "\u00bfQuer\u00e9s que guarde este an\u00e1lisis en el escritorio o seguimos con otra consulta?"

    def _generate_ai_message(
        self,
        *,
        base_message: str,
        closing_question: str,
        context_snapshot: Dict[str, Any],
        trace_id: Optional[str],
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        if not base_message:
            return None, None

        reasoner = self._get_reasoner()
        if reasoner is None:
            return None, None

        system_prompt = (
            "Sos Capi Gus, el agente de comunicaci\u00f3n de CapiAgentes. "
            "Respond\u00e9 en castellano rioplatense, con tono profesional pero cercano. "
            "Contest\u00e1 primero la pregunta principal usando los datos brindados, "
            "luego resum\u00ed el hallazgo m\u00e1s relevante y cerr\u00e1 con una pregunta amable que invite a continuar."
        )

        query = (
            "Gener\u00e1 la respuesta final para el usuario combinando el snapshot financiero y el mensaje base. "
            "Mant\u00e9nelo en 2 o 3 frases. "
            "Seg\u00ed este orden: (1) responder de forma directa con el saldo actual, "
            "(2) compartir el insight m\u00e1s importante (brecha, distribuci\u00f3n o alertas) "
            "y (3) cerrar con una pregunta inspirada en: \"{closing}\". "
            "Evit\u00e1 listas y tecnicismos innecesarios."
        ).format(closing=closing_question)

        context_payload = {
            "base_message": base_message,
            "closing_prompt": closing_question,
            "financial_snapshot": context_snapshot,
        }

        async def _invoke_reasoner() -> LLMReasoningResult:
            return await reasoner.reason(
                query=query,
                context_data=context_payload,
                system_prompt=system_prompt,
                trace_id=trace_id,
                max_output_tokens=220,
            )

        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            try:
                llm_result = asyncio.run(_invoke_reasoner())
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning({"event": "capi_gus_llm_failed", "trace_id": trace_id, "error": str(exc)})
                if "api key" in str(exc).lower():
                    self._llm_disabled = True
                return None, None
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(lambda: asyncio.run(_invoke_reasoner()))
                try:
                    llm_result = future.result()
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.warning({"event": "capi_gus_llm_failed", "trace_id": trace_id, "error": str(exc)})
                    if "api key" in str(exc).lower():
                        self._llm_disabled = True
                    return None, None

        if not llm_result.success or not llm_result.response:
            if llm_result.error:
                logger.warning(
                    {
                        "event": "capi_gus_llm_error",
                        "trace_id": trace_id,
                        "error": llm_result.error,
                        "model": llm_result.model,
                    }
                )
                if "api key" in llm_result.error.lower():
                    self._llm_disabled = True
            return None, None

        message = llm_result.response.strip()
        if closing_question and closing_question not in message:
            if "?" in message:
                message = f"{message} {closing_question}"
            else:
                message = f"{message.rstrip('.')}. {closing_question}"

        usage = {
            "model": llm_result.model,
            "prompt_tokens": llm_result.prompt_tokens,
            "completion_tokens": llm_result.completion_tokens,
            "total_tokens": llm_result.total_tokens,
            "cost_usd": round(llm_result.cost_usd, 6),
            "processing_time": round(llm_result.processing_time, 4),
            "finish_reason": llm_result.finish_reason,
        }

        logger.info(
            {
                "event": "capi_gus_llm_completed",
                "trace_id": trace_id,
                "model": llm_result.model,
                "total_tokens": llm_result.total_tokens,
                "cost_usd": round(llm_result.cost_usd, 6),
            }
        )
        return message, usage

    def _get_reasoner(self) -> Optional[LLMReasoner]:
        if self._llm_disabled:
            return None
        if self._reasoner is not None:
            return self._reasoner

        settings = get_settings()
        api_key = getattr(settings, "OPENAI_API_KEY", None)
        if not api_key:
            logger.info("CapiGusNode LLM disabled: missing OPENAI_API_KEY")
            self._llm_disabled = True
            return None

        self._reasoner = LLMReasoner(
            model=getattr(settings, "DEFAULT_MODEL", None) or "gpt-5-mini",
            temperature=0.35,
            max_tokens=320,
        )
        return self._reasoner

    def _decimal_to_float(self, value: Optional[Decimal]) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _build_distribution_payload(self, row: Optional[Dict[str, Any]]) -> Dict[str, Decimal]:
        breakdown: Dict[str, Decimal] = {}
        if not isinstance(row, dict):
            return breakdown
        channel_map = [
            ("total_atm", "ATM"),
            ("total_ats", "ATS"),
            ("total_tesoro", "Tesoro"),
            ("total_cajas_ventanilla", "cajas ventanilla"),
            ("total_buzon_depositos", "buz\u00f3n de dep\u00f3sitos"),
            ("total_recaudacion", "recaudaci\u00f3n"),
            ("total_caja_chica", "caja chica"),
            ("total_otros", "otros"),
        ]
        for field, label in channel_map:
            value = self._to_decimal(row.get(field))
            if value is None:
                continue
            breakdown[label] = value
        return breakdown

    def _select_primary_row(self, bucket: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(bucket, dict):
            return None
        rows = bucket.get("rows")
        if isinstance(rows, Iterable):
            for item in rows:
                if isinstance(item, dict):
                    return item
        return None

    def _resolve_branch_name(
        self,
        row: Optional[Dict[str, Any]],
        datab_bucket: Any,
        metadata: Dict[str, Any],
        state: GraphState,
    ) -> Optional[str]:
        candidates: Iterable[Any] = ()
        if isinstance(row, dict):
            candidates = (
                row.get("sucursal_nombre"),
                row.get("branch_name"),
                row.get("sucursal"),
                row.get("branch"),
            )
            for candidate in candidates:
                if isinstance(candidate, str) and candidate.strip():
                    return candidate.strip()

        planner_meta = {}
        if isinstance(datab_bucket, dict):
            planner_meta = datab_bucket.get("planner_metadata") or {}
        if not planner_meta and isinstance(metadata, dict):
            planner_meta = metadata.get("planner_metadata") or {}
        branch_meta = planner_meta.get("branch") if isinstance(planner_meta, dict) else None
        if isinstance(branch_meta, dict):
            for key in ("name", "branch_name", "raw_text"):
                candidate = branch_meta.get(key)
                if isinstance(candidate, str) and candidate.strip():
                    return candidate.strip()

        payload = getattr(state, "external_payload", {}) or {}
        if isinstance(payload, dict):
            candidate = payload.get("branch") or payload.get("sucursal")
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        return None

    def _extract_value(self, row: Optional[Dict[str, Any]], keys: Iterable[str]) -> tuple[Optional[Decimal], Optional[str]]:
        if not isinstance(row, dict):
            return None, None
        for key in keys:
            if key in row:
                value = self._to_decimal(row.get(key))
                if value is not None:
                    return value, self._format_currency(value)
        return None, None

    def _compute_delta(self, balance: Optional[Decimal], theoretical: Optional[Decimal]) -> Optional[Decimal]:
        if balance is None or theoretical is None:
            return None
        return theoretical - balance

    def _build_distribution_text(
        self,
        row: Optional[Dict[str, Any]],
        breakdown: Optional[Dict[str, Decimal]] = None,
    ) -> Optional[str]:
        data = breakdown if breakdown is not None else self._build_distribution_payload(row)
        if not data:
            return None
        parts = [f"{label} {self._format_currency(amount)}" for label, amount in data.items()]
        return ", ".join(parts) if parts else None

    def _summarize_alerts(self, metadata: Dict[str, Any], elcajas_bucket: Any) -> tuple[Optional[str], Dict[str, Any]]:
        alert_ids: list[str] = []
        raw_ids = metadata.get("el_cajas_alert_ids")
        if isinstance(raw_ids, list):
            alert_ids = [str(item) for item in raw_ids if item]
        elif raw_ids:
            alert_ids = [str(raw_ids)]

        alerts_created = None
        if isinstance(metadata, dict):
            alerts_created = metadata.get("el_cajas_alerts")
        if alerts_created is None and isinstance(elcajas_bucket, dict):
            alerts_created = elcajas_bucket.get("alerts_created")
        alerts_created = int(alerts_created or 0)

        analysis = elcajas_bucket.get("analysis") if isinstance(elcajas_bucket, dict) else None
        headlines: list[str] = []
        if isinstance(analysis, list):
            for entry in analysis:
                if isinstance(entry, dict):
                    headline = entry.get("headline")
                    if isinstance(headline, str) and headline.strip():
                        headlines.append(headline.strip())

        duplicates = metadata.get("el_cajas_alert_duplicates")
        if isinstance(duplicates, list):
            duplicate_ids = [str(item) for item in duplicates if item]
        elif duplicates:
            duplicate_ids = [str(duplicates)]
        else:
            duplicate_ids = []

        if alert_ids:
            joined = ", ".join(alert_ids)
            alert_message = (
                f"Tamb\u00e9n analic\u00e9 la operatoria y gener\u00e9 la alerta autom\u00e1tica ID {joined} con las desviaciones detectadas."
            )
        elif alerts_created > 0:
            alert_message = (
                "Tamb\u00e9n analic\u00e9 la operatoria y gener\u00e9 alertas autom\u00e1ticas con las desviaciones detectadas."
            )
        elif headlines:
            alert_message = "Analic\u00e9 la operatoria de caja: " + "; ".join(headlines[:2])
        else:
            alert_message = None
        payload = {
            "count": alerts_created,
            "ids": alert_ids,
            "headlines": headlines,
            "duplicates": duplicate_ids,
        }
        return alert_message, payload

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------

    def _to_decimal(self, value: Any) -> Optional[Decimal]:
        if value is None:
            return None
        if isinstance(value, Decimal):
            return value
        if isinstance(value, (int, float)):
            return Decimal(str(value))

        str_value = str(value).strip()
        if not str_value:
            return None
        cleaned = str_value.replace("ARS", "").replace("$", "").strip()
        cleaned = cleaned.replace(" ", " ").replace("\u00a0", " ")
        cleaned = cleaned.replace(" ", "")
        if "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        elif "," in cleaned:
            cleaned = cleaned.replace(",", ".")
        try:
            return Decimal(cleaned)
        except (InvalidOperation, ValueError):
            return None

    def _format_currency(self, value: Decimal) -> str:
        quantized = value.quantize(Decimal("0.01"))
        sign = "-" if quantized < 0 else ""
        abs_value = abs(quantized)
        integer_part, decimal_part = f"{abs_value:,.2f}".split(".")
        integer_part = integer_part.replace(",", ".")
        return f"{sign}${integer_part},{decimal_part}"


__all__ = ["CapiGusNode"]
