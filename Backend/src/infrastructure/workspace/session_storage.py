"""Session manifest persistence for LangGraph orchestrator.

Provides helpers to persist and retrieve chat session history and related
artifacts under ``Backend/ia_workspace/data/sessions``.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.logging import get_logger
from src.infrastructure.langgraph.state_schema import GraphState

logger = get_logger(__name__)

_SANITIZE_SESSION_ID = re.compile(r"[^A-Za-z0-9._-]")


def resolve_workspace_root(env_var: str = "CAPI_IA_WORKSPACE") -> Path:
    """Resolve the base workspace directory used for session persistence."""

    def _looks_like_workspace(path: Path) -> bool:
        return any((path / child).exists() for child in ("data", "agentes"))

    env_path = os.getenv(env_var)
    if env_path:
        candidate = Path(env_path).expanduser()
        try:
            if candidate.is_file():
                candidate = candidate.parent
            if candidate.name in {"data", "agentes"}:
                candidate = candidate.parent
            candidate = candidate.resolve()
            candidate.mkdir(parents=True, exist_ok=True)
            if not _looks_like_workspace(candidate):
                (candidate / "data").mkdir(parents=True, exist_ok=True)
            return candidate
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning(
                {
                    "event": "workspace_path_error",
                    "provided_path": env_path,
                    "error": str(exc),
                }
            )

    default_root = Path(__file__).resolve().parents[3] / "ia_workspace"
    default_root.mkdir(parents=True, exist_ok=True)
    if not (default_root / "data").exists():
        (default_root / "data").mkdir(parents=True, exist_ok=True)
    return default_root


class SessionStorage:
    """Manages conversation manifests stored on disk for each session."""

    def __init__(self, workspace_root: Optional[Path] = None) -> None:
        self._workspace_root = workspace_root or resolve_workspace_root()
        (self._workspace_root / "data" / "sessions").mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_from_state(self, state: GraphState) -> None:
        """Persist the latest session snapshot using the provided graph state."""
        sanitized = self.sanitize_session_id(state.session_id)
        manifest = self._load_manifest(sanitized)

        now = datetime.now().isoformat()
        manifest.setdefault("created_at", now)
        manifest["session_id"] = state.session_id
        manifest["sanitized_session_id"] = sanitized
        manifest["updated_at"] = now
        manifest.setdefault("datab_exports", [])

        # Core summary
        manifest["status"] = state.status.value
        manifest["trace_id"] = state.trace_id
        manifest["user_id"] = state.user_id
        manifest["workflow_mode"] = state.workflow_mode
        manifest["active_agent"] = state.active_agent
        manifest["completed_nodes"] = list(state.completed_nodes or [])
        manifest["intent"] = getattr(state.detected_intent, "value", None)
        manifest["intent_confidence"] = state.intent_confidence
        manifest["last_query"] = state.original_query
        manifest["last_response"] = {
            "message": state.response_message,
            "data": state.response_data,
        }
        manifest["response_metadata"] = state.response_metadata or {}
        manifest["routing_decision"] = state.routing_decision

        # Conversation context (ensure JSON-serializable)
        manifest["conversation_history"] = state.conversation_history or []
        manifest["memory_window"] = state.memory_window or []
        manifest["reasoning_summary"] = state.reasoning_summary
        manifest["processing_metrics"] = state.processing_metrics or {}
        manifest["shared_artifacts"] = state.shared_artifacts or {}
        manifest["errors"] = state.errors or []

        self._write_manifest(sanitized, manifest)

    def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        manifest = self._load_manifest(self.sanitize_session_id(session_id))
        history = manifest.get("conversation_history")
        if isinstance(history, list):
            return history
        return []

    def get_manifest(self, session_id: str) -> Dict[str, Any]:
        return self._load_manifest(self.sanitize_session_id(session_id))

    def list_sessions(self) -> List[str]:
        sessions_dir = self._workspace_root / "data" / "sessions"
        if not sessions_dir.exists():
            return []

        session_ids: List[str] = []
        for entry in sessions_dir.iterdir():
            if not entry.is_dir():
                continue
            manifest_path = entry / f"{entry.name}.json"
            if not manifest_path.exists():
                continue
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            session_id = manifest.get("session_id") or manifest.get("sanitized_session_id")
            if session_id:
                session_ids.append(session_id)
        return session_ids

    def clear_session_history(self, session_id: str) -> None:
        sanitized = self.sanitize_session_id(session_id)
        manifest = self._load_manifest(sanitized)
        if not manifest:
            return

        manifest["conversation_history"] = []
        manifest["memory_window"] = []
        manifest["last_response"] = None
        manifest["updated_at"] = datetime.now().isoformat()
        self._write_manifest(sanitized, manifest)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def sanitize_session_id(self, session_id: str) -> str:
        if not session_id:
            return "default"
        cleaned = _SANITIZE_SESSION_ID.sub("_", session_id.strip())
        return cleaned[:128] or "default"

    def _session_dir(self, sanitized_session_id: str) -> Path:
        session_dir = self._workspace_root / "data" / "sessions" / f"session_{sanitized_session_id}"
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir

    def _manifest_path(self, sanitized_session_id: str) -> Path:
        session_dir = self._session_dir(sanitized_session_id)
        return session_dir / f"session_{sanitized_session_id}.json"

    def _load_manifest(self, sanitized_session_id: str) -> Dict[str, Any]:
        path = self._manifest_path(sanitized_session_id)
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                logger.warning(
                    {
                        "event": "session_manifest_corrupt",
                        "path": str(path),
                    }
                )
        return {}

    def _write_manifest(self, sanitized_session_id: str, manifest: Dict[str, Any]) -> None:
        path = self._manifest_path(sanitized_session_id)
        safe_payload = json.loads(json.dumps(manifest, ensure_ascii=False, default=str))
        path.write_text(json.dumps(safe_payload, ensure_ascii=False, indent=2), encoding="utf-8")