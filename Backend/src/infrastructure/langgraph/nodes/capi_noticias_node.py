"""LangGraph node for the Capi Noticias financial news agent."""
from __future__ import annotations

import os
import sys
import time
from typing import Any, Dict

from src.infrastructure.langgraph.nodes.base import GraphNode
from src.infrastructure.langgraph.state_schema import GraphState, StateMutator
from src.core.logging import get_logger

# Ensure ia_workspace and scheduler service are importable
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_SRC = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))
BACKEND_ROOT = os.path.abspath(os.path.join(BACKEND_SRC, ".."))
IA_WORKSPACE = os.path.join(BACKEND_ROOT, "ia_workspace")

if BACKEND_SRC not in sys.path:
    sys.path.insert(0, BACKEND_SRC)
if IA_WORKSPACE not in sys.path:
    sys.path.insert(0, IA_WORKSPACE)

from src.application.services.capi_noticias_service import get_capi_noticias_scheduler  # noqa: E402

logger = get_logger(__name__)


class CapiNoticiasNode(GraphNode):
    """Executes the Capi Noticias agent within the LangGraph pipeline."""

    def __init__(self, name: str = "capi_noticias") -> None:
        super().__init__(name=name)
        self._is_agent_node = True
        self.scheduler = get_capi_noticias_scheduler()

    def run(self, state: GraphState) -> GraphState:
        start_time = time.time()
        self._emit_agent_start(state)

        try:
            logger.info({"event": "capi_noticias_node_start", "session_id": state.session_id})

            result = self.scheduler.trigger_run(trigger="langgraph")
            if not result:
                raise RuntimeError("No se pudo obtener resultados del agente Capi Noticias")

            summary = result.get("summary", {})
            message = summary.get("detail") or summary.get("headline") or "Monitoreo de noticias completado"

            response_payload: Dict[str, Any] = {
                "news_report": {
                    "generated_at": result.get("generated_at"),
                    "summary": summary,
                    "alerts": result.get("alerts", []),
                    "metrics": result.get("metrics", {}),
                    "articles": result.get("articles", []),
                    "source_urls": result.get("source_urls", []),
                }
            }

            s = StateMutator.update_field(state, "current_node", self.name)
            s = StateMutator.append_to_list(s, "completed_nodes", self.name)
            s = StateMutator.update_field(s, "response_message", message)
            s = StateMutator.merge_dict(s, "response_data", response_payload)
            s = StateMutator.merge_dict(
                s,
                "response_metadata",
                {
                    "agent": self.name,
                    "news_article_count": len(result.get("articles", [])),
                    "news_high_alerts": len([a for a in result.get("alerts", []) if a.get("impact_level") == "high"]),
                },
            )

            duration_ms = (time.time() - start_time) * 1000
            self._emit_agent_end(state, success=True, duration_ms=duration_ms)

            logger.info(
                {
                    "event": "capi_noticias_node_end",
                    "duration_ms": round(duration_ms, 2),
                    "alerts": len(result.get("alerts", [])),
                    "articles": len(result.get("articles", [])),
                }
            )
            return s

        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("[capi_noticias_node] error: %s", exc)
            s = StateMutator.update_field(state, "current_node", self.name)
            s = StateMutator.add_error(s, "capi_noticias_error", str(exc), {"agent": self.name})
            self._emit_agent_end(state, success=False)
            return s
