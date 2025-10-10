"""ReAct-inspired coordinator node that performs lightweight reasoning and tool use before routing."""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from src.core.logging import get_logger
from src.infrastructure.langgraph.nodes.base import GraphNode
from src.infrastructure.langgraph.state_schema import GraphState, StateMutator

logger = get_logger(__name__)


@dataclass
class ToolObservation:
    name: str
    input_payload: Dict[str, Any]
    output: Dict[str, Any]


@dataclass
class ActionDecision:
    tool_name: Optional[str]
    thought: str
    kwargs: Dict[str, Any]
    recommended_agent: Optional[str]


class ReActNode(GraphNode):
    """Reason + Act loop that enriches the GraphState with tool observations."""

    def __init__(self, name: str = "react", max_iterations: int = 3) -> None:
        super().__init__(name=name)
        self.max_iterations = max(1, max_iterations)
        self._tools: Dict[str, Callable[[GraphState, Dict[str, Any]], Dict[str, Any]]] = {
            "summarize_context": self._tool_summarize_context,
            "collect_metrics": self._tool_collect_metrics,
            "inspect_desktop": self._tool_inspect_desktop,
            "detect_anomalies": self._tool_detect_anomalies,
            "gather_news": self._tool_gather_news,
        }
        self._file_keywords = {"archivo", "file", "excel", "pdf", "word", "documento"}
        self._summary_keywords = {"resumen", "summary", "total", "general", "overview"}
        self._anomaly_keywords = {"anomalia", "anomaly", "irregular", "outlier", "sospech"}
        self._news_keywords = {"noticia", "news", "ambito", "alerta", "liquidez"}
        self._greeting_keywords = {"hola", "hello", "saludos", "buenos dias"}
        self._google_keywords = {"correo", "correos", "gmail", "mail", "google", "drive", "calendar", "calendario", "agenda", "evento"}

    def run(self, state: GraphState) -> GraphState:
        start = time.time()
        logger.debug({"event": "react_node_start", "session_id": state.session_id})

        updated = StateMutator.update_field(state, "current_node", self.name)
        updated = StateMutator.append_to_list(updated, "completed_nodes", self.name)

        steps: List[Dict[str, Any]] = []
        observations: List[ToolObservation] = []
        query = (state.original_query or state.response_message or "").strip()
        recommended_agent: Optional[str] = None

        # Always gather short context summary first
        context_obs = self._safe_invoke_tool("summarize_context", updated, {})
        if context_obs is not None:
            observations.append(context_obs)
            steps.append({"thought": "Reviso el contexto reciente para entender la conversacion.",
                          "action": context_obs.name,
                          "observation": context_obs.output})

        for iteration in range(self.max_iterations):
            decision = self._decide_next_action(query, updated, iteration, recommended_agent)
            steps.append({"thought": decision.thought, "action": decision.tool_name, "params": decision.kwargs, "iteration": iteration})

            if not decision.tool_name:
                break

            observation = self._safe_invoke_tool(decision.tool_name, updated, decision.kwargs)
            if observation is None:
                continue
            observations.append(observation)
            steps[-1]["observation"] = observation.output
            if decision.recommended_agent:
                recommended_agent = decision.recommended_agent
            if recommended_agent is None:
                recommended_agent = observation.output.get("recommended_agent")

            # If the tool itself signals finish, we can exit early
            if observation.output.get("should_finish"):
                break

        finish_message = self._build_finish_message(query, observations, recommended_agent)
        steps.append({
            "thought": "Finalizo el ciclo ReAct con una recomendacion.",
            "action": "finish",
            "observation": {"message": finish_message, "recommended_agent": recommended_agent},
        })

        meta_updates = {
            "react_trace": steps,
            "react_recommended_agent": recommended_agent,
            "react_finished_at": datetime.now().isoformat(),
        }
        needs_follow_up = recommended_agent is None
        if recommended_agent and recommended_agent != state.active_agent:
            meta_updates["active_agent"] = recommended_agent
        if recommended_agent:
            meta_updates["loop_fallback"] = recommended_agent
        meta_updates["react_follow_up"] = needs_follow_up
        if not needs_follow_up:
            meta_updates["needs_retry"] = None
        updated = StateMutator.merge_dict(
            updated,
            "response_metadata",
            meta_updates,
        )
        updated = StateMutator.merge_dict(
            updated,
            "response_data",
            {"react_observations": [obs.output for obs in observations]},
        )
        updated = StateMutator.append_to_list(
            updated,
            "reasoning_trace",
            {
                "type": "react",
                "steps": steps,
                "recommended_agent": recommended_agent,
                "timestamp": datetime.now().isoformat(),
            },
        )
        if recommended_agent:
            updated = StateMutator.update_field(updated, "routing_decision", recommended_agent)
            updated = StateMutator.update_field(updated, "active_agent", recommended_agent)

        duration_ms = int((time.time() - start) * 1000)
        updated = StateMutator.merge_dict(
            updated,
            "processing_metrics",
            {
                "react_steps": len(steps),
                "react_latency_ms": duration_ms,
            },
        )

        logger.info({
            "event": "react_node_end",
            "session_id": state.session_id,
            "recommended_agent": recommended_agent,
            "steps": len(steps),
            "duration_ms": duration_ms,
        })
        return updated

    # ------------------------------------------------------------------
    # Decision helpers
    # ------------------------------------------------------------------
    def _decide_next_action(
        self, query: str, state: GraphState, iteration: int, recommended_agent: Optional[str]
    ) -> ActionDecision:
        query_lower = query.lower()
        if iteration == 0:
            # First iteration after context focuses on intent classification
            return ActionDecision(
                tool_name="collect_metrics",
                thought="Verifico metricas previas para identificar senales relevantes.",
                kwargs={},
                recommended_agent=recommended_agent,
            )

        if any(token in query_lower for token in self._file_keywords):
            return ActionDecision(
                tool_name="inspect_desktop",
                thought="El usuario habla de archivos, inspecciono el entorno de escritorio.",
                kwargs={},
                recommended_agent="capi_desktop",
            )

        if any(token in query_lower for token in self._google_keywords):
            return ActionDecision(
                tool_name=None,
                thought="Detecto una solicitud vinculada a Gmail, Drive o Calendar; delego en Agente G.",
                kwargs={},
                recommended_agent="agente_g",
            )

        if any(token in query_lower for token in self._summary_keywords):
            return ActionDecision(
                tool_name="collect_metrics",
                thought="Necesito datos para explicarlo de forma clara.",
                kwargs={},
                recommended_agent="capi_gus",
            )

        if any(token in query_lower for token in self._anomaly_keywords):
            return ActionDecision(
                tool_name="detect_anomalies",
                thought="Busco anomalias registradas para la alerta.",
                kwargs={},
                recommended_agent="anomaly",
            )

        if any(token in query_lower for token in self._news_keywords):
            return ActionDecision(
                tool_name="gather_news",
                thought="El usuario pide noticias, consulto senales externas.",
                kwargs={},
                recommended_agent="capi_noticias",
            )

        if any(token in query_lower for token in self._greeting_keywords):
            return ActionDecision(
                tool_name=None,
                thought="El usuario saluda; responderá Capi Gus de forma cordial.",
                kwargs={},
                recommended_agent="capi_gus",
            )

        # Default: if we already recommended something, finish, otherwise fallback to summary
        if recommended_agent:
            return ActionDecision(
                tool_name=None,
                thought="Ya tengo una recomendacion, concluyo la iteracion.",
                kwargs={},
                recommended_agent=recommended_agent,
            )

        return ActionDecision(
            tool_name="collect_metrics",
            thought="Sin senales claras, tomo metricas generales para decidir.",
            kwargs={},
            recommended_agent="capi_gus",
        )

    def _build_finish_message(
        self, query: str, observations: List[ToolObservation], recommended_agent: Optional[str]
    ) -> str:
        if recommended_agent:
            return f"Derivare la consulta '{query}' al agente '{recommended_agent}' con la evidencia recopilada."
        if not observations:
            return "No se encontraron observaciones relevantes; se continuara con la ruta por defecto."
        last_obs = observations[-1].output
        detail = last_obs.get("observation") or last_obs.get("summary") or "observaciones previas"
        return f"Continuare el flujo con base en {detail}."

    # ------------------------------------------------------------------
    # Tool implementations
    # ------------------------------------------------------------------
    def _safe_invoke_tool(
        self, tool_name: str, state: GraphState, kwargs: Dict[str, Any]
    ) -> Optional[ToolObservation]:
        handler = self._tools.get(tool_name)
        if handler is None:
            logger.warning({"event": "react_tool_missing", "tool": tool_name})
            return None
        try:
            output = handler(state, dict(kwargs))
            return ToolObservation(name=tool_name, input_payload=dict(kwargs), output=output)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error({"event": "react_tool_error", "tool": tool_name, "error": str(exc)})
            return None

    def _tool_summarize_context(self, state: GraphState, payload: Dict[str, Any]) -> Dict[str, Any]:
        history = list(state.conversation_history or [])
        limit = int(payload.get("limit", 3))
        recent = history[-limit:]
        summary = " ".join(
            entry.get("content", "")[:160] for entry in recent if isinstance(entry, dict)
        ).strip()
        summary = summary or "Sin historial relevante."
        return {
            "summary": summary,
            "recent_turns": recent,
        }

    def _tool_collect_metrics(self, state: GraphState, payload: Dict[str, Any]) -> Dict[str, Any]:
        metrics = dict(state.processing_metrics or {})
        data_summary = dict(state.data_summary or {})
        observation = "Se encontraron metricas previas." if metrics else "No hay metricas almacenadas."
        return {
            "observation": observation,
            "metrics": metrics,
            "data_summary": data_summary,
            "recommended_agent": payload.get("fallback_agent"),
        }

    def _tool_inspect_desktop(self, state: GraphState, payload: Dict[str, Any]) -> Dict[str, Any]:
        desktop_meta = state.response_metadata.get("desktop_insights", {}) if state.response_metadata else {}
        observation = desktop_meta.get("status", "Se requiere acceder al agente CAPI Desktop.")
        return {
            "observation": observation,
            "desktop": desktop_meta,
            "recommended_agent": "capi_desktop",
        }

    def _tool_detect_anomalies(self, state: GraphState, payload: Dict[str, Any]) -> Dict[str, Any]:
        anomalies = state.response_metadata.get("anomaly_signals", []) if state.response_metadata else []
        observation = "Se detectaron senales anomalas." if anomalies else "Sin anomalias pendientes."
        return {
            "observation": observation,
            "anomalies": anomalies,
            "recommended_agent": "anomaly",
        }

    def _tool_gather_news(self, state: GraphState, payload: Dict[str, Any]) -> Dict[str, Any]:
        news_buffer = state.response_metadata.get("news_signals", []) if state.response_metadata else []
        observation = "Noticias recientes disponibles." if news_buffer else "Sin noticias cacheadas."
        return {
            "observation": observation,
            "news": news_buffer,
            "recommended_agent": "capi_noticias",
        }

__all__ = ["ReActNode"]

