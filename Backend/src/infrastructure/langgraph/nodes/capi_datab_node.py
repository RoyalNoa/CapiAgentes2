"""LangGraph node for the Capi DataB agent."""
from __future__ import annotations

import asyncio
import importlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, List, Tuple
from datetime import datetime, timezone
import uuid

from langgraph.types import interrupt

from src.domain.contracts.agent_io import AgentTask, TaskStatus
from src.core.logging import get_logger
from src.infrastructure.langgraph.nodes.base import GraphNode
from src.infrastructure.langgraph.nodes.capi_elcajas_node import CapiElCajasNode
from src.infrastructure.langgraph.state_schema import GraphState, StateMutator
from src.infrastructure.langgraph.utils.capi_datab_formatter import (
    compose_success_message,
    extract_branch_descriptor,
    relax_branch_filters,
)
from src.infrastructure.database.postgres_client import (
    PostgreSQLClient,
    HistoricalAlert,
    AlertPriority,
    AlertStatus,
)

logger = get_logger(__name__)

def _ensure_paths() -> None:
    """Ensure ia_workspace is available for dynamic imports."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_src_path = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
    backend_root_path = os.path.abspath(os.path.join(backend_src_path, '..'))
    ia_workspace_path = os.path.join(backend_root_path, 'ia_workspace')
    if backend_src_path not in sys.path:
        sys.path.insert(0, backend_src_path)
    if ia_workspace_path not in sys.path:
        sys.path.insert(0, ia_workspace_path)

_ensure_paths()
from agentes.capi_datab.handler import DbOperation
class CapiDataBNode(GraphNode):
    """Executes database operations through the Capi DataB agent."""

    def __init__(self, name: str = "capi_datab") -> None:
        super().__init__(name=name)
        self._is_agent_node = True
        self.agent = self._load_agent()

    def run(self, state: GraphState) -> GraphState:
        start_time = time.time()
        self._emit_agent_start(state)

        updated = StateMutator.update_field(state, "current_node", self.name)

        if self.agent is None:
            message = "El agente Capi DataB no estÃ¡ disponible."
            logger.error({"event": "capi_datab_not_loaded"})
            updated = StateMutator.update_field(updated, "response_message", message)
            updated = StateMutator.add_error(updated, "agent_unavailable", message, {"agent": self.name})
            updated = StateMutator.append_to_list(updated, "completed_nodes", self.name)
            self._emit_agent_end(state, success=False, duration_ms=int((time.time() - start_time) * 1000))
            return updated

        if self._should_run_alert_monitor(state):
            return self._process_alert_monitor(updated, state, start_time)

        instruction = self._extract_instruction(state)
        if not instruction:
            message = "No se encontrÃ³ una instrucciÃ³n de base de datos en la consulta."
            updated = StateMutator.update_field(updated, "response_message", message)
            updated = StateMutator.add_error(updated, "datab_invalid_instruction", message, {"agent": self.name})
            updated = StateMutator.append_to_list(updated, "completed_nodes", self.name)
            self._emit_agent_end(state, success=False, duration_ms=int((time.time() - start_time) * 1000))
            return updated

        try:
            operation = self.agent.prepare_operation(instruction)
            planner_meta = getattr(operation, 'metadata', {}) or {}
            branch_hint = extract_branch_descriptor(
                operation.preview(),
                planner_meta,
                {"parameters": operation.parameters},
                getattr(operation, 'metadata', None),
            )
            relax_branch_filters(operation, branch_hint)
            planner_meta = getattr(operation, 'metadata', {}) or planner_meta
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error({
                "event": "capi_datab_parse_error",
                "error": str(exc),
                "instruction": instruction,
            })
            message = f"No se pudo interpretar la operaciÃ³n solicitada: {exc}"
            updated = StateMutator.update_field(updated, "response_message", message)
            updated = StateMutator.add_error(updated, "datab_parse_error", message, {"agent": self.name})
            updated = StateMutator.append_to_list(updated, "completed_nodes", self.name)
            self._emit_agent_end(state, success=False, duration_ms=int((time.time() - start_time) * 1000))
            return updated

        decision: Optional[Dict[str, Any]] = None
        if operation.requires_approval:
            approval_context = operation.preview()
            approval_context.update({
                "agent": self.name,
                "reason": "ActualizaciÃ³n de registros requiere autorizaciÃ³n humana.",
            })
            decision = interrupt(approval_context)
            if not decision.get("approved", False):
                message = decision.get("message") or "OperaciÃ³n cancelada por revisiÃ³n humana."
                metadata = {
                    "human_decision": decision,
                    "db_operation": approval_context,
                    "db_operation_status": "rejected",
                }
                updated = StateMutator.merge_dict(updated, "response_metadata", metadata)
                updated = StateMutator.update_field(updated, "response_message", message)
                updated = StateMutator.append_to_list(updated, "completed_nodes", self.name)
                self._emit_agent_end(state, success=False, duration_ms=int((time.time() - start_time) * 1000))
                return updated

        try:
            task = AgentTask(
                task_id=f"datab_{state.session_id}_{int(start_time)}",
                intent="db_operation",
                query=instruction,
                user_id=state.user_id,
                session_id=state.session_id,
                context={"human_decision": decision or {}},
            )
            agent_result = self.agent.execute_operation(
                operation,
                task_id=task.task_id,
                user_id=task.user_id,
                session_id=task.session_id,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error({
                "event": "capi_datab_execution_error",
                "error": str(exc),
                "operation": operation.preview(),
            })
            message = f"Error al ejecutar la operaciÃ³n de base de datos: {exc}"
            updated = StateMutator.add_error(updated, "datab_execution_error", message, {"agent": self.name})
            updated = StateMutator.update_field(updated, "response_message", message)
            updated = StateMutator.append_to_list(updated, "completed_nodes", self.name)
            self._emit_agent_end(state, success=False, duration_ms=int((time.time() - start_time) * 1000))
            return updated

        processing_ms = int((time.time() - start_time) * 1000)
        success = agent_result.status == TaskStatus.COMPLETED and not agent_result.error

        data_payload = agent_result.data or {}
        shared_bucket: Dict[str, Any] = {
            "mode": "db_operation",
            "operation": operation.preview(),
            "export_file": data_payload.get("file_path"),
            "rows": data_payload.get("rows"),
            "rowcount": data_payload.get("rowcount"),
            "success": success,
        }
        if planner_meta:
            shared_bucket["planner_metadata"] = planner_meta

        metadata_update: Dict[str, Any] = {
            "agent": self.name,
            "db_operation": operation.preview(),
            "db_operation_status": "completed" if success else "failed",
        }
        if decision:
            metadata_update["human_decision"] = decision
        if planner_meta:
            metadata_update["planner_metadata"] = planner_meta

        raw_agent_message = agent_result.message
        metadata_update["agent_raw_message"] = raw_agent_message

        export_file = shared_bucket.get("export_file")
        if success:
            success_message = compose_success_message(
                operation=operation,
                data_payload=data_payload,
                planner_meta=planner_meta or {},
                export_file=export_file,
                fallback_message=raw_agent_message,
            )
            shared_bucket["summary_message"] = success_message
            metadata_update["result_summary"] = success_message
            policies = self._load_cash_policies(state)
            if policies:
                shared_bucket["policies"] = policies
            if shared_bucket.get("rows"):
                updated = StateMutator.update_field(updated, "routing_decision", "capi_elcajas")
            updated = StateMutator.update_field(updated, "response_message", success_message)
            updated = StateMutator.merge_dict(updated, "response_data", data_payload)
        else:
            updated = StateMutator.add_error(
                updated,
                "datab_operation_failed",
                raw_agent_message,
                {
                    "agent": self.name,
                    "operation": operation.preview(),
                },
            )
            updated = StateMutator.update_field(updated, "response_message", raw_agent_message)

        desktop_instruction = None
        if success:
            desktop_instruction = self._build_desktop_instruction_from_export(
                shared_bucket.get("export_file"),
                shared_bucket.get("rows"),
            )
            if desktop_instruction:
                metadata_update.update(
                    {
                        "desktop_instruction": desktop_instruction,
                        "semantic_action": "EXPORT_FILE",
                        "requires_human_approval": False,
                        "datab_desktop_ready": True,
                    }
                )
            elif shared_bucket.get("rows"):
                metadata_update["datab_desktop_ready"] = True
            else:
                metadata_update["datab_desktop_ready"] = False
        else:
            metadata_update["datab_desktop_ready"] = False
            metadata_update.setdefault("el_cajas_pending", False)

        updated = StateMutator.merge_dict(updated, "response_metadata", metadata_update)
        updated = StateMutator.merge_dict(updated, "shared_artifacts", {"capi_datab": shared_bucket})

        metrics_payload = {
            "capi_datab_latency_ms": processing_ms,
        }
        if planner_meta.get("planner_confidence") is not None:
            metrics_payload["planner_confidence"] = planner_meta.get("planner_confidence")
        if planner_meta.get("planner_latency_ms") is not None:
            metrics_payload["nl_query_planner_ms"] = planner_meta.get("planner_latency_ms")
        if shared_bucket.get("rows") is not None:
            try:
                metrics_payload["capi_datab_rows"] = len(shared_bucket["rows"])
            except TypeError:
                pass
        elif data_payload.get("rowcount") is not None:
            metrics_payload["capi_datab_rows"] = data_payload.get("rowcount")
        updated = StateMutator.merge_dict(updated, "processing_metrics", metrics_payload)
        updated = StateMutator.append_to_list(updated, "completed_nodes", self.name)

        alerts_persisted = False
        if shared_bucket.get("rows"):
            try:
                el_cajas_node = CapiElCajasNode()
                updated = el_cajas_node.run(updated)
                updated, alerts_persisted = self._persist_elcajas_alerts(updated)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.error({"event": "capi_elcajas_inline_failed", "error": str(exc)})

        self._emit_agent_end(state, success=success, duration_ms=processing_ms)
        return updated

    # ------------------------------------------------------------------
    # Helpers
    def _load_cash_policies(self, state: GraphState) -> List[Dict[str, Any]]:
        operation = DbOperation(
            operation="select",
            sql=(
                "SELECT channel, max_surplus_pct, max_deficit_pct, min_buffer_amount, "
                "daily_withdrawal_limit, daily_deposit_limit, reload_lead_hours, sla_hours, "
                "truck_fixed_cost, truck_variable_cost_per_kg, notes, updated_at "
                "FROM alerts.cash_policies ORDER BY channel"
            ),
            parameters=[],
            output_format="json",
            table="alerts.cash_policies",
            requires_approval=False,
            description="Carga de politicas de efectivo para El Cajas",
            raw_request="internal:cash_policies",
        )
        try:
            result = self.agent.execute_operation(
                operation,
                task_id=f"{state.session_id}_cash_policies",
                user_id=state.user_id,
                session_id=state.session_id,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning({"event": "capi_datab_policies_failed", "error": str(exc)})
            return []
        data = result.data or {}
        rows = data.get("rows")
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
        return []

    def _persist_elcajas_alerts(self, state: GraphState) -> Tuple[GraphState, bool]:
        shared = getattr(state, "shared_artifacts", {}) or {}
        el_cajas_bucket = shared.get("capi_elcajas") if isinstance(shared, dict) else None
        operations = None
        el_cajas_data = None
        if isinstance(el_cajas_bucket, dict):
            ops = el_cajas_bucket.get("alert_operations")
            if isinstance(ops, list):
                operations = ops

        if not operations:
            data_bucket = getattr(state, "response_data", {}) or {}
            el_cajas_data = data_bucket.get("el_cajas") if isinstance(data_bucket, dict) else None
            if isinstance(el_cajas_data, dict):
                ops = el_cajas_data.get("alert_operations")
                if isinstance(ops, list):
                    operations = ops

        if not isinstance(operations, list) or not operations:
            return state, False

        user_id = getattr(state, "user_id", "system") or "system"
        session_id = getattr(state, "session_id", "default") or "default"
        persisted_ids: List[str] = []
        failure_messages: List[str] = []
        duplicate_claves: List[str] = []

        allowed_columns = {
            "creada_en",
            "agente_id",
            "prioridad",
            "estado",
            "problema",
            "hipotesis",
            "impacto",
            "datos_clave",
            "acciones",
            "sucursal_id",
            "dispositivo_id",
            "evento_id",
            "dedupe_clave",
        }

        for op in operations:
            if not isinstance(op, dict):
                continue
            if op.get("persisted"):
                db_id = op.get("database_id")
                if db_id is not None:
                    persisted_ids.append(str(db_id))
                continue

            values = op.get("values")
            if not isinstance(values, dict) or not values:
                continue

            sanitized_values: Dict[str, Any] = {
                key: value
                for key, value in values.items()
                if key in allowed_columns and value is not None
            }
            if not sanitized_values:
                continue

            for key in list(sanitized_values):
                value = sanitized_values[key]
                if key == "datos_clave":
                    if value is None:
                        sanitized_values[key] = json.dumps([], ensure_ascii=False)
                    elif isinstance(value, (list, tuple)):
                        sanitized_values[key] = json.dumps(list(value), ensure_ascii=False)
                    else:
                        sanitized_values[key] = json.dumps([str(value)], ensure_ascii=False)
                elif key == "creada_en" and isinstance(value, str):
                    try:
                        sanitized_values[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    except ValueError:
                        sanitized_values[key] = datetime.utcnow().replace(tzinfo=timezone.utc)
                elif key == "agente_id":
                    try:
                        sanitized_values[key] = uuid.UUID(str(value))
                    except (ValueError, AttributeError, TypeError):
                        sanitized_values[key] = uuid.UUID('b37d1f90-6b35-4fb3-866e-2f88c9b29850')

            columns = list(sanitized_values.keys())
            parameters = [sanitized_values[column] for column in columns]
            placeholders = [f'${idx + 1}' for idx, _ in enumerate(columns)]
            sql = f"INSERT INTO public.alertas ({', '.join(columns)}) VALUES ({', '.join(placeholders)}) RETURNING id"
            description = op.get("description") or "Insert alerta El Cajas"
            metadata = {
                key: op.get(key)
                for key in ("branch_id", "branch_name", "source")
                if op.get(key)
            }

            db_operation = DbOperation(
                operation="insert",
                sql=sql,
                parameters=parameters,
                output_format="json",
                table="public.alertas",
                requires_approval=False,
                description=description,
                raw_request="el_cajas:alert_insert",
                metadata=metadata or None,
            )

            attempts = 0
            while attempts < 2:
                try:
                    agent_result = self.agent.execute_operation(
                        db_operation,
                        task_id=f"{session_id}_alert_insert_{attempts}",
                        user_id=user_id,
                        session_id=session_id,
                    )
                    if agent_result.status != TaskStatus.COMPLETED or agent_result.error:
                        raise RuntimeError(agent_result.error or agent_result.message or "alert_insert_failed")

                    data_payload = agent_result.data or {}
                    inserted_id = None
                    rows = data_payload.get("rows")
                    if isinstance(rows, list) and rows:
                        inserted_id = rows[0].get("id")
                    if inserted_id is None and data_payload.get("rowcount"):
                        inserted_id = data_payload.get("rowcount")

                    op["persisted"] = True
                    if inserted_id is not None:
                        op["database_id"] = inserted_id
                        persisted_ids.append(str(inserted_id))
                    payload = op.get("payload")
                    if isinstance(payload, dict):
                        payload["persisted"] = True
                        if inserted_id is not None:
                            payload["database_id"] = inserted_id
                    break
                except Exception as exc:  # pragma: no cover - defensive logging
                    error_text = str(exc) if exc else ""
                    if "uq_alertas_dedupe_abiertas" in error_text.lower():
                        op["persisted"] = True
                        payload = op.get("payload")
                        if isinstance(payload, dict):
                            payload["persisted"] = True
                            payload["duplicate"] = True
                        dedupe_value = sanitized_values.get("dedupe_clave")
                        if dedupe_value:
                            duplicate_claves.append(str(dedupe_value))
                        logger.info({
                            "event": "capi_datab_alert_duplicate",
                            "dedupe_clave": sanitized_values.get("dedupe_clave"),
                            "operation": op.get("description"),
                        })
                        break
                    attempts += 1
                    if attempts >= 2:
                        logger.error({
                            "event": "capi_datab_alert_persist_failed",
                            "error": error_text,
                            "operation": op.get("description"),
                        })
                        op["persisted"] = False
                        op["error"] = error_text
                        payload = op.get("payload")
                        if isinstance(payload, dict):
                            payload["persisted"] = False
                            payload["error"] = error_text
                        failure_messages.append(error_text)

        if isinstance(el_cajas_bucket, dict):
            el_cajas_bucket["alert_operations"] = operations
        if isinstance(el_cajas_data, dict):
            el_cajas_data["alert_operations"] = operations

        metadata_updates: Dict[str, Any] = {}
        success = False
        if persisted_ids:
            metadata_updates["el_cajas_alert_ids"] = persisted_ids
            success = True
        if duplicate_claves:
            metadata_updates["el_cajas_alert_duplicates"] = duplicate_claves
            metadata_updates["el_cajas_alert_duplicate"] = True
            success = True
        if success:
            metadata_updates["el_cajas_alert_persisted"] = True
            state = StateMutator.merge_dict(state, "response_metadata", metadata_updates)
            state = self._append_alert_notification(state, duplicate_claves if duplicate_claves else None)
            return state, True

        if failure_messages:
            state = self._append_alert_failure(state, failure_messages)

        return state, False
    def _should_run_alert_monitor(self, state: GraphState) -> bool:
        mode = str(getattr(state, "workflow_mode", "") or "").lower()
        if mode in {"alert_monitor", "alerts", "alert"}:
            return True
        payload = getattr(state, "external_payload", {}) or {}
        if isinstance(payload, dict):
            requested_mode = str(payload.get("workflow_mode") or payload.get("mode") or "").lower()
            if requested_mode in {"alert_monitor", "alerts", "alert"}:
                return True
            if payload.get("alert_poll") or payload.get("alert_monitor"):
                return True
        return False

    def _extract_instruction(self, state: GraphState) -> str:
        payload = getattr(state, "external_payload", {}) or {}
        for key in ("db_instruction", "sql", "query"):
            value = payload.get(key)
            if isinstance(value, dict):
                try:
                    return json.dumps(value)
                except Exception:  # pragma: no cover - defensive logging
                    continue
            if isinstance(value, str) and value.strip():
                return value.strip()
        instruction = (state.original_query or "").strip()
        return instruction

    def _resolve_alert_filters(self, state: GraphState) -> Dict[str, Any]:
        payload = getattr(state, "external_payload", {}) or {}
        filters = dict(payload.get("alert_filters") or {})
        for key in ("priority", "status", "agent", "limit"):
            if key in payload and key not in filters and payload[key] is not None:
                filters[key] = payload[key]
        return filters

    def _build_alert_query(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        conditions: Dict[str, Any] = {}
        status = filters.get("status") or "active"
        if status:
            conditions["status"] = status
        priority = filters.get("priority")
        if priority:
            conditions["priority"] = priority
        agent = filters.get("agent")
        if agent:
            conditions["agent_source"] = agent

        return {
            "operation": "select",
            "table": "alerts.historical_alerts",
            "columns": [
                "id",
                "alert_code",
                "title",
                "description",
                "priority",
                "status",
                "timestamp",
                "financial_impact",
                "confidence_score",
                "agent_source",
            ],
            "conditions": conditions,
            "order_by": ["timestamp DESC"],
            "limit": int(filters.get("limit") or 10),
            "output_format": "json",
        }

    def _process_alert_monitor(self, updated: GraphState, state: GraphState, start_time: float) -> GraphState:
        filters = self._resolve_alert_filters(state)
        query_payload = self._build_alert_query(filters)

        try:
            operation = self.agent.prepare_operation(json.dumps(query_payload))
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error({
                "event": "capi_datab_alert_parse_error",
                "error": str(exc),
                "filters": filters,
            })
            message = f"No se pudo preparar la consulta de alertas: {exc}"
            updated = StateMutator.update_field(updated, "response_message", message)
            updated = StateMutator.add_error(updated, "datab_alert_parse_error", message, {"agent": self.name})
            updated = StateMutator.append_to_list(updated, "completed_nodes", self.name)
            self._emit_agent_end(state, success=False, duration_ms=int((time.time() - start_time) * 1000))
            return updated

        try:
            agent_result = self.agent.execute_operation(
                operation,
                task_id=f"datab_alerts_{state.session_id}_{int(start_time)}",
                user_id=state.user_id,
                session_id=state.session_id,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error({
                "event": "capi_datab_alert_execution_error",
                "error": str(exc),
                "filters": filters,
            })
            message = f"Error al consultar alertas: {exc}"
            updated = StateMutator.update_field(updated, "response_message", message)
            updated = StateMutator.add_error(updated, "datab_alert_execution_error", message, {"agent": self.name})
            updated = StateMutator.append_to_list(updated, "completed_nodes", self.name)
            self._emit_agent_end(state, success=False, duration_ms=int((time.time() - start_time) * 1000))
            return updated

        processing_ms = int((time.time() - start_time) * 1000)
        data_payload = agent_result.data or {}
        alerts = data_payload.get("rows")
        if not isinstance(alerts, list):
            alerts = []

        message = (
            f"Se detectaron {len(alerts)} alertas activas." if alerts else "No se detectaron alertas nuevas."
        )
        metadata_update = {
            "agent": self.name,
            "db_operation": operation.preview(),
            "db_operation_status": "completed" if alerts else "empty",
            "datab_alerts_pending": bool(alerts),
            "alert_filters": filters,
        }
        shared_bucket = {
            "mode": "alert_monitor",
            "filters": filters,
            "export_file": data_payload.get("file_path"),
            "alerts": alerts,
            "success": agent_result.status == TaskStatus.COMPLETED and not agent_result.error,
        }

        updated = StateMutator.update_field(updated, "response_message", message)
        updated = StateMutator.merge_dict(updated, "response_metadata", metadata_update)
        updated = StateMutator.merge_dict(updated, "response_data", {"datab_alerts": alerts})
        updated = StateMutator.merge_dict(updated, "shared_artifacts", {"capi_datab": shared_bucket})
        updated = StateMutator.merge_dict(
            updated,
            "processing_metrics",
            {
                "capi_datab_latency_ms": processing_ms,
                "capi_datab_rows": len(alerts),
            },
        )
        updated = StateMutator.append_to_list(updated, "completed_nodes", self.name)

        self._emit_agent_end(state, success=bool(alerts), duration_ms=processing_ms)
        return updated

    def _append_alert_notification(
        self,
        state: GraphState,
        duplicate_claves: Optional[List[str]] = None,
    ) -> GraphState:
        message = (state.response_message or '').strip()
        metadata = dict(state.response_metadata or {})
        alert_ids = metadata.get('el_cajas_alert_ids')

        if isinstance(alert_ids, list) and alert_ids:
            id_text = ', '.join(str(item) for item in alert_ids)
            addition = f"Genere una alerta automatica (ID: {id_text}) con las desviaciones detectadas."
        elif alert_ids:
            addition = f"Genere una alerta automatica (ID: {alert_ids}) con las desviaciones detectadas."
        elif duplicate_claves:
            dup_text = ', '.join(str(item) for item in duplicate_claves)
            addition = f"La alerta ya existia en la base de datos (ID: {dup_text})."
        else:
            addition = 'Genere una alerta automatica con las desviaciones detectadas.'

        if addition not in message:
            new_message = f"{message}\n\n{addition}" if message else addition
            state = StateMutator.update_field(state, 'response_message', new_message)

        artifact = self._extract_latest_recommendation(state)
        metadata_updates: Dict[str, Any] = {
            'el_cajas_alert_persisted': True,
        }
        if duplicate_claves:
            metadata_updates['el_cajas_alert_duplicate'] = True
            metadata_updates['el_cajas_alert_duplicates'] = duplicate_claves

        if artifact:
            action = self._build_save_recommendation_action(state, artifact)
            metadata = dict(state.response_metadata or {})
            actions = list(metadata.get('actions') or [])
            actions = [item for item in actions if item.get('id') != action.get('id')]
            actions.append(action)
            metadata_updates.update({
                'actions': actions,
                'desktop_recommendation': artifact,
                'pending_desktop_instruction': self._build_recommendation_instruction(artifact),
                'requires_human_approval': True,
                'approval_reason': 'Deseas que guardemos la recomendacion en el escritorio?',
                'el_cajas_pending': True,
            })
            state = StateMutator.merge_dict(state, 'response_metadata', metadata_updates)
            state = StateMutator.update_field(state, 'routing_decision', 'human_gate')
            return state

        return StateMutator.merge_dict(state, 'response_metadata', metadata_updates)

    def _append_alert_failure(self, state: GraphState, failures: List[str]) -> GraphState:
        message = (state.response_message or '').strip()
        reason = failures[0] if failures else 'No se pudo crear la alerta'
        sanitized = reason.replace('\r', ' ').replace('\n', ' ').strip()[:200]
        addition = f"No se pudo crear la alerta en la base de datos ({sanitized})."
        if addition not in message:
            new_message = f"{message}\n\n{addition}" if message else addition
            state = StateMutator.update_field(state, 'response_message', new_message)

        metadata_updates = {
            'el_cajas_alert_persisted': False,
            'el_cajas_alert_error': sanitized,
            'actions': [],
            'requires_human_approval': False,
            'el_cajas_pending': False,
        }
        state = StateMutator.merge_dict(state, 'response_metadata', metadata_updates)
        state = StateMutator.update_field(state, 'routing_decision', 'assemble')
        return state

    def _extract_latest_recommendation(self, state: GraphState) -> Optional[Dict[str, Any]]:
        shared = getattr(state, 'shared_artifacts', {}) or {}
        bucket = shared.get('capi_elcajas') if isinstance(shared, dict) else None
        artifacts = None
        if isinstance(bucket, dict):
            artifacts = bucket.get('recommendation_files')
        if not artifacts:
            data_bucket = getattr(state, 'response_data', {}) or {}
            el_cajas_data = data_bucket.get('el_cajas') if isinstance(data_bucket, dict) else None
            if isinstance(el_cajas_data, dict):
                artifacts = el_cajas_data.get('recommendation_files')
        if isinstance(artifacts, list) and artifacts:
            return artifacts[-1]
        return None

    def _build_save_recommendation_action(self, state: GraphState, artifact: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            'artifact_path': artifact.get('path'),
            'artifact_filename': artifact.get('filename'),
            'summary': artifact.get('summary'),
            'hypothesis': artifact.get('hypothesis'),
            'impact': artifact.get('impact'),
            'suggested_actions': artifact.get('suggested_actions'),
            'branch_name': artifact.get('branch_name'),
            'session_id': getattr(state, 'session_id', 'default'),
        }
        return {
            'id': 'save_recommendation',
            'label': 'Guardar recomendacion en escritorio',
            'payload': payload,
        }
    def _build_recommendation_instruction(self, artifact: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(artifact, dict):
            return None

        suggestions = artifact.get('suggested_actions')
        rows: List[Dict[str, Any]] = []
        if isinstance(suggestions, list) and suggestions:
            for item in suggestions:
                if isinstance(item, dict):
                    rows.append({
                        'Canal': item.get('channel'),
                        'Accion': item.get('action'),
                        'Monto': item.get('amount'),
                        'Motivo': item.get('reason'),
                        'Urgencia': item.get('urgency'),
                        'CostoEstimado': item.get('estimated_cost'),
                        'PesoKg': item.get('weight_kg'),
                    })
                else:
                    rows.append({'Detalle': str(item)})

        summary = artifact.get('summary')
        hypothesis = artifact.get('hypothesis')
        impact = artifact.get('impact')
        if summary or hypothesis or impact:
            rows.append({
                'Resumen': summary,
                'Hipotesis': hypothesis,
                'Impacto': impact,
            })

        if not rows:
            return None

        base_name = artifact.get('filename') or f"recomendacion_{artifact.get('branch_name') or 'sucursal'}"
        stem = Path(base_name).stem or 'recomendacion'
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        filename = f"{stem}_{timestamp}.xlsx"
        sheet_name = artifact.get('branch_name') or artifact.get('sucursal') or 'Recomendacion'

        return {
            'intent': 'escribir_archivo_excel',
            'action': 'write_file',
            'parameters': {
                'filename': filename,
                'sheet_name': sheet_name,
                'data': rows,
            },
        }

    def _build_desktop_instruction_from_export(
        self,
        export_file: Optional[str],
        rows: Optional[List[Dict[str, Any]]],
    ) -> Optional[Dict[str, Any]]:
        content: Optional[str] = None
        filename: Optional[str] = None

        if export_file:
            try:
                path = Path(export_file)
                if path.exists():
                    content = path.read_text(encoding="utf-8")
                    filename = f"{path.stem}_desktop.txt"
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning({"event": "capi_datab_export_read_failed", "error": str(exc), "file": export_file})

        if content is None and rows:
            try:
                content = json.dumps(rows, ensure_ascii=False, indent=2)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning({"event": "capi_datab_rows_dump_failed", "error": str(exc)})
                content = str(rows)
            filename = filename or f"capi_datab_{int(time.time())}.txt"

        if content is None:
            return None

        filename = filename or f"capi_datab_{int(time.time())}.txt"
        return {
            "intent": "escribir_archivo_txt",
            "parameters": {
                "filename": filename,
                "content": content,
            },
            "action": "write_file",
        }

    def _load_agent(self):
        try:
            _ensure_paths()
            module = importlib.import_module('agentes.capi_datab.handler')
            AgentClass = getattr(module, 'CapiDataBAgent')
            return AgentClass()
        except Exception as exc:  # pragma: no cover
            logger.error({"event": "capi_datab_agent_import_error", "error": str(exc)})
            return None











