from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Dict

from src.core.logging import get_logger

_LOGGER = get_logger(__name__)
_LOCK = Lock()
_LOG_FILE_NAME = "agent_metrics.jsonl"


def _resolve_log_path() -> Path:
    env_dir = os.getenv("CAPI_LOG_DIR")
    if env_dir:
        base = Path(env_dir)
    elif os.name != "nt" and os.path.exists("/app"):
        base = Path("/app/logs")
    else:
        base = Path(__file__).resolve().parents[3] / "logs"
    base.mkdir(parents=True, exist_ok=True)
    return base / _LOG_FILE_NAME


def _now_iso(timestamp: str | None = None) -> str:
    if timestamp:
        return timestamp
    return datetime.utcnow().isoformat(timespec="milliseconds") + "Z"


def _sanitize(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}


def _write_event(payload: Dict[str, Any]) -> None:
    try:
        line = json.dumps(payload, ensure_ascii=True)
    except (TypeError, ValueError) as exc:
        _LOGGER.warning({"event": "agent_metrics_serialization_failed", "error": str(exc)})
        return

    path = _resolve_log_path()
    with _LOCK:
        try:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        except OSError as exc:
            _LOGGER.error({"event": "agent_metrics_write_failed", "error": str(exc), "path": str(path)})


def record_turn_event(
    *,
    agent_name: str,
    session_id: str,
    turn_id: int,
    latency_ms: int,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    timestamp: str | None = None,
    user_id: str | None = None,
    channel: str | None = None,
    model: str | None = None,
    trace_id: str | None = None,
    intent: str | None = None,
    response_type: str | None = None,
    success: bool | None = None,
    metadata: Dict[str, Any] | None = None,
) -> None:
    tokens_total = int(max(input_tokens, 0)) + int(max(output_tokens, 0))
    payload = {
        "timestamp": _now_iso(timestamp),
        "event_type": "agent_turn_completed",
        "agent_name": agent_name,
        "session_id": session_id,
        "turn_id": int(turn_id),
        "latency_ms": int(max(latency_ms, 0)),
        "input_tokens": int(max(input_tokens, 0)),
        "output_tokens": int(max(output_tokens, 0)),
        "tokens_total": tokens_total,
        "cost_usd": float(max(cost_usd, 0.0)),
        "user_id": user_id,
        "channel": channel,
        "model": model,
        "trace_id": trace_id,
        "intent": intent,
        "response_type": response_type,
        "success": success,
    }
    if metadata:
        payload["metadata"] = metadata

    _write_event(_sanitize(payload))


def record_error_event(
    *,
    agent_name: str,
    session_id: str,
    turn_id: int,
    error_code: str,
    error_message: str,
    timestamp: str | None = None,
    latency_ms: int | None = None,
    user_id: str | None = None,
    channel: str | None = None,
    trace_id: str | None = None,
    intent: str | None = None,
    metadata: Dict[str, Any] | None = None,
) -> None:
    payload = {
        "timestamp": _now_iso(timestamp),
        "event_type": "agent_error",
        "agent_name": agent_name,
        "session_id": session_id,
        "turn_id": int(turn_id),
        "error_code": error_code,
        "error_message": error_message,
        "latency_ms": int(latency_ms) if latency_ms is not None else None,
        "user_id": user_id,
        "channel": channel,
        "trace_id": trace_id,
        "intent": intent,
    }
    if metadata:
        payload["metadata"] = metadata

    _write_event(_sanitize(payload))


def record_feedback_event(
    *,
    agent_name: str,
    session_id: str,
    turn_id: int,
    feedback_score: float | None = None,
    feedback_text: str | None = None,
    timestamp: str | None = None,
    user_id: str | None = None,
    channel: str | None = None,
    trace_id: str | None = None,
    intent: str | None = None,
    metadata: Dict[str, Any] | None = None,
) -> None:
    score_value = None
    if feedback_score is not None:
        try:
            score_value = float(feedback_score)
        except (TypeError, ValueError):
            score_value = None

    payload = {
        "timestamp": _now_iso(timestamp),
        "event_type": "feedback_recorded",
        "agent_name": agent_name,
        "session_id": session_id,
        "turn_id": int(turn_id),
        "feedback_score": score_value,
        "feedback_text": feedback_text,
        "user_id": user_id,
        "channel": channel,
        "trace_id": trace_id,
        "intent": intent,
    }
    if metadata:
        payload["metadata"] = metadata

    _write_event(_sanitize(payload))
