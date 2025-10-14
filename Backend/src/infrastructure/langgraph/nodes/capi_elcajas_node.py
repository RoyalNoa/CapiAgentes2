"""LangGraph node for the El Cajas cash diagnostics agent."""
from __future__ import annotations

import asyncio
import os
import sys
import threading
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.core.logging import get_logger
from src.infrastructure.langgraph.nodes.base import GraphNode
from src.infrastructure.langgraph.state_schema import GraphState, StateMutator

logger = get_logger(__name__)

AGENT_AVAILABLE = False
el_cajas_agent_class = None

try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_src_path = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
    if backend_src_path not in sys.path:
        sys.path.insert(0, backend_src_path)
    workspace_path = os.path.abspath(os.path.join(backend_src_path, "..", "ia_workspace"))
    if workspace_path not in sys.path:
        sys.path.insert(0, workspace_path)

    from agentes.capi_elcajas.handler import ElCajasAgent
    from src.domain.agents.agent_models import AgentResult, AgentTask, IntentType, TaskStatus

    el_cajas_agent_class = ElCajasAgent
    AGENT_AVAILABLE = True
except ImportError as exc:  # pragma: no cover - defensive logging
    logger.warning({"event": "elcajas_import_failed", "error": str(exc)})
    AGENT_AVAILABLE = False


class CapiElCajasNode(GraphNode):
    """Node that delegates to the El Cajas agent for cash diagnostics."""

    def __init__(self, name: str = "capi_elcajas") -> None:
        super().__init__(name=name)
        self._is_agent_node = True
        self.agent = el_cajas_agent_class() if AGENT_AVAILABLE and el_cajas_agent_class else None

    def run(self, state: GraphState) -> GraphState:
        start_time = time.time()
        self._emit_agent_start(state)

        updated = StateMutator.update_field(state, "current_node", self.name)

        if self.agent is None:
            duration_ms = self._elapsed_ms(start_time)
            message = "El agente El Cajas no esta disponible."
            updated = StateMutator.add_error(updated, "el_cajas_unavailable", message, {"agent": self.name})
            updated = StateMutator.merge_dict(
                updated,
                "response_metadata",
                {"el_cajas_status": "unavailable", "el_cajas_pending": False},
            )
            updated = StateMutator.update_field(updated, "response_message", self._compose_message(updated, message))
            updated = StateMutator.append_to_list(updated, "completed_nodes", self.name)
            self._emit_agent_end(state, success=False, duration_ms=duration_ms)
            return updated

        branch_rows = self._extract_branch_rows(state)
        if not branch_rows:
            duration_ms = self._elapsed_ms(start_time)
            message = "Sin resultados de caja para analizar."
            updated = StateMutator.merge_dict(
                updated,
                "response_metadata",
                {"el_cajas_status": "no_data", "el_cajas_pending": False},
            )
            updated = StateMutator.update_field(updated, "response_message", self._compose_message(updated, message))
            updated = StateMutator.append_to_list(updated, "completed_nodes", self.name)
            self._emit_agent_end(state, success=True, duration_ms=duration_ms)
            return updated

        shared_bucket = self._extract_datab_bucket(state)
        task = AgentTask(
            task_id=f"el_cajas_{state.session_id}_{int(start_time)}",
            intent=IntentType.BRANCH,
            query=self._resolve_query(state),
            user_id=state.user_id,
            session_id=state.session_id,
            context={
                "branch_rows": branch_rows,
                "shared": shared_bucket,
                "policies": shared_bucket.get("policies"),
            },
            metadata={"workflow_mode": state.workflow_mode},
        )

        try:
            result = self._run_agent(task)
        except Exception as exc:  # pragma: no cover - defensive logging
            duration_ms = self._elapsed_ms(start_time)
            logger.error({"event": "el_cajas_execution_failed", "error": str(exc)})
            message = f"Error al ejecutar El Cajas: {exc}"
            updated = StateMutator.add_error(updated, "el_cajas_error", message, {"agent": self.name})
            updated = StateMutator.merge_dict(
                updated,
                "response_metadata",
                {"el_cajas_status": "error", "el_cajas_pending": False},
            )
            updated = StateMutator.update_field(updated, "response_message", self._compose_message(updated, message))
            updated = StateMutator.append_to_list(updated, "completed_nodes", self.name)
            self._emit_agent_end(state, success=False, duration_ms=duration_ms)
            return updated

        if not isinstance(result, AgentResult):
            duration_ms = self._elapsed_ms(start_time)
            message = "El Cajas devolvio un resultado invalido."
            updated = StateMutator.add_error(updated, "el_cajas_invalid_result", message, {"agent": self.name})
            updated = StateMutator.merge_dict(
                updated,
                "response_metadata",
                {"el_cajas_status": "error", "el_cajas_pending": False},
            )
            updated = StateMutator.update_field(updated, "response_message", self._compose_message(updated, message))
            updated = StateMutator.append_to_list(updated, "completed_nodes", self.name)
            self._emit_agent_end(state, success=False, duration_ms=duration_ms)
            return updated

        if result.status != TaskStatus.COMPLETED or result.error:
            duration_ms = self._elapsed_ms(start_time)
            message = result.message or "El Cajas no pudo completar el analisis."
            updated = StateMutator.add_error(updated, "el_cajas_failed", message, {"agent": self.name})
            updated = StateMutator.merge_dict(
                updated,
                "response_metadata",
                {"el_cajas_status": "error", "el_cajas_pending": False},
            )
            updated = StateMutator.update_field(updated, "response_message", self._compose_message(updated, message))
            updated = StateMutator.append_to_list(updated, "completed_nodes", self.name)
            self._emit_agent_end(state, success=False, duration_ms=duration_ms)
            return updated

        data = result.data or {}
        message = result.message or "Diagnostico de caja completado"
        severity = self._extract_overall_status(data)
        duration_ms = self._elapsed_ms(start_time)

        metadata_updates: Dict[str, Any] = {
            "el_cajas_status": severity,
            "el_cajas_alerts": data.get("alerts_created", 0),
            "el_cajas_pending": False,
        }
        metrics = {
            "el_cajas_latency_ms": duration_ms,
            "el_cajas_alerts": data.get("alerts_created", 0),
        }

        combined_message = self._compose_message(updated, message)
        metadata_updates["result_summary"] = combined_message

        shared_updates: Dict[str, Any] = {self.name: data}
        if shared_bucket:
            merged_datab = dict(shared_bucket)
            merged_datab["summary_message"] = combined_message
            shared_updates["capi_datab"] = merged_datab

        updated = StateMutator.merge_dict(updated, "response_metadata", metadata_updates)
        updated = StateMutator.merge_dict(updated, "response_data", {"el_cajas": data})
        updated = StateMutator.merge_dict(updated, "shared_artifacts", shared_updates)
        updated = StateMutator.merge_dict(updated, "processing_metrics", metrics)
        updated = StateMutator.update_field(updated, "routing_decision", "capi_gus")
        updated = StateMutator.update_field(updated, "response_message", combined_message)
        updated = self._prepare_desktop_action(updated, data)
        updated = StateMutator.append_to_list(updated, "completed_nodes", self.name)

        self._emit_agent_end(state, success=True, duration_ms=duration_ms)
        return updated

    def _prepare_desktop_action(self, state: GraphState, data: Dict[str, Any]) -> GraphState:
        artifacts: List[Dict[str, Any]] = []
        files = data.get('recommendation_files')
        if isinstance(files, list) and files:
            artifacts = files
        else:
            artifact_single = data.get('recommendation_artifact')
            if isinstance(artifact_single, dict):
                artifacts = [artifact_single]
        if not artifacts:
            return state

        artifact = artifacts[-1]
        instruction = self._build_recommendation_instruction(state, artifact)
        if instruction is None:
            return state

        action = self._build_save_recommendation_action(state, artifact)
        metadata = dict(state.response_metadata or {})
        actions = [item for item in metadata.get('actions') or [] if isinstance(item, dict)]
        actions = [item for item in actions if item.get('id') != action.get('id')]
        actions.append(action)

        metadata_updates = {
            'actions': actions,
            'desktop_recommendation': artifact,
            'pending_desktop_instruction': instruction,
            'requires_human_approval': True,
            'approval_reason': 'Deseas que guardemos la recomendacion en el escritorio?',
            'el_cajas_pending': True,
        }
        updated = StateMutator.merge_dict(state, 'response_metadata', metadata_updates)
        updated = StateMutator.update_field(updated, 'routing_decision', 'human_gate')
        return updated

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

    def _build_recommendation_instruction(self, state: GraphState, artifact: Dict[str, Any]) -> Optional[Dict[str, Any]]:
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
        stem = Path(base_name).stem
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        filename = f"{stem}_{timestamp}.xlsx"

        sheet_name = artifact.get('branch_name') or 'Recomendacion'
        return {
            'intent': 'escribir_archivo_excel',
            'action': 'write_file',
            'parameters': {
                'filename': filename,
                'sheet_name': sheet_name,
                'data': rows,
            },
        }

    def _run_agent(self, task: AgentTask) -> AgentResult:
        result_container: Dict[str, AgentResult] = {}
        error_container: Dict[str, Exception] = {}

        def runner() -> None:
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                if not (AGENT_AVAILABLE and el_cajas_agent_class):
                    error_container["error"] = RuntimeError("El Cajas no disponible")
                    return

                agent_instance = self.agent or el_cajas_agent_class()
                result_container["result"] = loop.run_until_complete(agent_instance.process(task))
            except Exception as exc:  # pragma: no cover - defensive logging
                error_container["error"] = exc
            finally:
                loop.close()
        worker = threading.Thread(target=runner, name="el_cajas_runner", daemon=True)
        worker.start()
        worker.join()

        if "error" in error_container:
            raise error_container["error"]
        result = result_container.get("result")
        if result is None:
            raise RuntimeError("El Cajas no devolvio resultado")
        return result

    def _extract_branch_rows(self, state: GraphState) -> List[Dict[str, Any]]:
        shared = getattr(state, "shared_artifacts", {}) or {}
        datab_bucket = shared.get("capi_datab") if isinstance(shared, dict) else None
        if isinstance(datab_bucket, dict):
            rows = datab_bucket.get("rows")
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
        response_data = getattr(state, "response_data", {}) or {}
        rows = response_data.get("rows")
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
        return []

    def _extract_datab_bucket(self, state: GraphState) -> Dict[str, Any]:
        shared = getattr(state, "shared_artifacts", {}) or {}
        if isinstance(shared, dict):
            bucket = shared.get("capi_datab")
            if isinstance(bucket, dict):
                return bucket
        return {}

    def _resolve_query(self, state: GraphState) -> str:
        candidates = [
            getattr(state, "original_query", ""),
            getattr(state, "response_message", ""),
            "Diagnostico de caja",
        ]
        for candidate in candidates:
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        return "Diagnostico de caja"

    def _compose_message(self, state: GraphState, agent_message: str) -> str:
        base = (getattr(state, "response_message", None) or "").strip()
        addition = agent_message.strip()
        if not addition:
            return base
        if not addition.lower().startswith("el cajas"):
            addition = f"El Cajas: {addition}"
        if not base:
            return addition
        if addition in base:
            return base
        return f"{base}\n\n{addition}"

    def _extract_overall_status(self, data: Dict[str, Any]) -> str:
        analysis = data.get("analysis")
        if not isinstance(analysis, list):
            return "unknown"
        statuses = {item.get("status", "ok") for item in analysis if isinstance(item, dict)}
        if not statuses:
            return "ok"
        if "critical" in statuses:
            return "critical"
        if "alert" in statuses:
            return "alert"
        if "warning" in statuses:
            return "warning"
        return "ok"

    def _elapsed_ms(self, start_time: float) -> int:
        return int((time.time() - start_time) * 1000)



