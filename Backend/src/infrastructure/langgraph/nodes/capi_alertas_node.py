"""Alert coordination node that bridges database signals with human decisions."""
from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from langgraph.types import interrupt

from src.infrastructure.langgraph.nodes.base import GraphNode
from src.infrastructure.langgraph.state_schema import GraphState, StateMutator
from src.core.logging import get_logger

logger = get_logger(__name__)


class CapiAlertasNode(GraphNode):
    """Collects alerts produced by Capi DataB and coordinates human approval."""

    def __init__(self, name: str = "capi_alertas") -> None:
        super().__init__(name=name)
        self._is_agent_node = False

    def run(self, state: GraphState) -> GraphState:
        start_time = time.time()
        updated = StateMutator.update_field(state, "current_node", self.name)

        alerts_payload = self._extract_alerts(state)
        if not alerts_payload:
            logger.info({
                "event": "capi_alertas_no_alerts",
                "session_id": state.session_id,
            })
            updated = StateMutator.merge_dict(
                updated,
                "response_metadata",
                {
                    "alerts_processed": False,
                    "alerts_reason": "no_alerts_available",
                },
            )
            return StateMutator.append_to_list(updated, "completed_nodes", self.name)

        summary = self._summarize(alerts_payload)
        decision_payload = {
            "node": self.name,
            "session_id": state.session_id,
            "trace_id": state.trace_id,
            "summary": summary,
            "alerts": alerts_payload,
            "desktop_suggestion": self._build_default_instruction(alerts_payload, summary),
        }

        logger.info({
            "event": "capi_alertas_interrupt",
            "session_id": state.session_id,
            "alert_count": len(alerts_payload),
        })
        decision = interrupt(decision_payload)
        decision = decision if isinstance(decision, dict) else {}

        accepted = bool(decision.get("accepted") or decision.get("action") == "accept")
        instruction = decision.get("desktop_instruction")
        if accepted and not instruction:
            instruction = self._build_default_instruction(alerts_payload, summary)

        metadata_updates: Dict[str, Any] = {
            "alerts_processed": True,
            "alerts_count": len(alerts_payload),
            "alerts_summary": summary,
            "alerts_decision": decision,
            "alerts_duration_ms": int((time.time() - start_time) * 1000),
        }

        if instruction:
            metadata_updates["desktop_instruction"] = instruction
            metadata_updates["semantic_action"] = "WRITE_FILE"
            metadata_updates["requires_human_approval"] = False

        if accepted:
            metadata_updates["alerts_action"] = "accepted"
        else:
            metadata_updates["alerts_action"] = "dismissed"

        updated = StateMutator.merge_dict(updated, "response_metadata", metadata_updates)
        updated = StateMutator.merge_dict(
            updated,
            "response_data",
            {"alert_events": alerts_payload},
        )
        updated = StateMutator.append_to_list(updated, "completed_nodes", self.name)
        return updated

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _extract_alerts(self, state: GraphState) -> List[Dict[str, Any]]:
        data_section = dict(state.response_data or {})
        metadata = dict(state.response_metadata or {})
        shared = dict(state.shared_artifacts or {})

        alerts: List[Dict[str, Any]] = []
        datab_bucket = shared.get("capi_datab", {})
        if isinstance(datab_bucket, dict):
            raw_alerts = datab_bucket.get("alerts")
            if isinstance(raw_alerts, list):
                alerts.extend(self._normalize_alert_list(raw_alerts))

        raw_from_data = data_section.get("datab_alerts")
        if isinstance(raw_from_data, list):
            alerts.extend(self._normalize_alert_list(raw_from_data))

        metadata_alerts = metadata.get("datab_alerts")
        if isinstance(metadata_alerts, list):
            alerts.extend(self._normalize_alert_list(metadata_alerts))

        # Deduplicate by id/title pair
        seen: set[tuple[str, str]] = set()
        unique_alerts: List[Dict[str, Any]] = []
        for alert in alerts:
            key = (str(alert.get("id")), alert.get("title", ""))
            if key in seen:
                continue
            seen.add(key)
            unique_alerts.append(alert)
        return unique_alerts

    def _normalize_alert_list(self, alerts: List[Any]) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for alert in alerts:
            if isinstance(alert, dict):
                normalized.append(alert)
            elif hasattr(alert, "dict"):
                normalized.append(alert.model_dump() if hasattr(alert, 'model_dump') else alert.dict())
        return normalized

    def _summarize(self, alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
        total = len(alerts)
        priorities: Dict[str, int] = {}
        for alert in alerts:
            priority = str(alert.get("priority") or alert.get("severity") or "unknown").lower()
            priorities[priority] = priorities.get(priority, 0) + 1
        top_priority = max(priorities, key=priorities.get) if priorities else "unknown"
        return {
            "total": total,
            "by_priority": priorities,
            "top_priority": top_priority,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }

    def _build_default_instruction(
        self,
        alerts: List[Dict[str, Any]],
        summary: Dict[str, Any],
    ) -> Dict[str, Any]:
        filename = f"alertas_capi_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.txt"
        payload = {
            "summary": summary,
            "alerts": alerts,
        }
        return {
            "intent": "escribir_archivo_txt",
            "parameters": {
                "filename": filename,
                "content": json.dumps(payload, ensure_ascii=False, indent=2),
            },
            "action": "write_file",
        }
