"""Gestor de notificaciones push para Agente G (Gmail + Pub/Sub)."""
from __future__ import annotations

import base64
import copy
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence
from uuid import uuid4

from googleapiclient.errors import HttpError

from src.infrastructure.external.google.gmail import GmailClient


logger = logging.getLogger(__name__)


@dataclass
class AgenteGPushSettings:
    """Configuración cargada desde variables de entorno."""

    topic_name: Optional[str]
    verification_token: Optional[str]
    label_ids: List[str]
    label_filter_action: str
    storage_dir: Path
    status_file: Path
    history_dir: Path
    max_history_items: int

    @classmethod
    def load_from_env(cls) -> "AgenteGPushSettings":
        topic_name = os.getenv("GOOGLE_GMAIL_PUSH_TOPIC")
        verification_token = os.getenv("GOOGLE_GMAIL_PUSH_VERIFICATION_TOKEN")

        label_ids_raw = os.getenv("GOOGLE_GMAIL_PUSH_LABEL_IDS", "")
        label_ids = [item.strip() for item in label_ids_raw.replace(";", ",").split(",") if item.strip()]

        label_filter_action = os.getenv("GOOGLE_GMAIL_PUSH_LABEL_ACTION", "include").lower()
        if label_filter_action not in {"include", "exclude"}:
            label_filter_action = "include"

        storage_root = os.getenv("AGENTE_G_STORAGE_DIR")
        if storage_root:
            storage_dir = Path(storage_root).expanduser().resolve()
        else:
            storage_dir = Path("Backend/ia_workspace/data/agent-output/agente_g").resolve()

        history_dir = storage_dir / "inbox_updates"
        status_file = storage_dir / "push_status.json"

        max_history_items = int(os.getenv("GOOGLE_GMAIL_PUSH_MAX_HISTORY", "50") or 50)

        # Asegurar existencia de carpetas en la configuración
        storage_dir.mkdir(parents=True, exist_ok=True)
        history_dir.mkdir(parents=True, exist_ok=True)

        return cls(
            topic_name=topic_name,
            verification_token=verification_token,
            label_ids=label_ids,
            label_filter_action=label_filter_action,
            storage_dir=storage_dir,
            status_file=status_file,
            history_dir=history_dir,
            max_history_items=max_history_items,
        )


class AgenteGPushService:
    """Administra el ciclo de vida de la suscripción push de Gmail."""

    def __init__(
        self,
        *,
        gmail_client: GmailClient,
        settings: AgenteGPushSettings | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.gmail = gmail_client
        self.settings = settings or AgenteGPushSettings.load_from_env()
        self._clock = clock or datetime.utcnow
        self._status_cache: Dict[str, Any] | None = None

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def enable_push(
        self,
        *,
        topic_name: Optional[str] = None,
        label_ids: Sequence[str] | None = None,
        label_filter_action: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Registra una suscripción push vía Gmail users.watch."""

        resolved_topic = topic_name or self.settings.topic_name
        if not resolved_topic:
            raise RuntimeError("GOOGLE_GMAIL_PUSH_TOPIC debe configurarse para habilitar push")

        resolved_labels = list(label_ids) if label_ids is not None else list(self.settings.label_ids)
        resolved_action = (label_filter_action or self.settings.label_filter_action or "include").lower()
        if resolved_action not in {"include", "exclude"}:
            resolved_action = "include"

        logger.info(
            "agente_g_watch_enable",
            extra={
                "topic": resolved_topic,
                "label_ids": resolved_labels,
                "label_action": resolved_action,
            },
        )

        response = self.gmail.watch_mailbox(
            topic_name=resolved_topic,
            label_ids=resolved_labels or None,
            label_filter_action=resolved_action,
        )

        now = self._clock().isoformat()
        status = self.get_status()
        status.update(
            {
                "active": True,
                "topic_name": resolved_topic,
                "label_ids": resolved_labels,
                "label_filter_action": resolved_action,
                "history_id": response.get("historyId"),
                "last_history_id": response.get("historyId"),
                "expiration": response.get("expiration"),
                "updated_at": now,
            }
        )
        status.pop("last_error", None)
        self._write_status(status)
        return copy.deepcopy(status)

    def disable_push(self) -> Dict[str, Any]:
        """Detiene la suscripción push activa (si existe)."""

        logger.info("agente_g_watch_disable")
        response = self.gmail.stop_watch()
        status = self.get_status()
        status.update({"active": False, "updated_at": self._clock().isoformat(), "last_disable_response": response})
        self._write_status(status)
        return copy.deepcopy(status)

    def get_status(self) -> Dict[str, Any]:
        if self._status_cache is None:
            self._status_cache = self._read_status()
        return copy.deepcopy(self._status_cache)

    def handle_notification(self, payload: Dict[str, Any], *, auth_header: str | None = None) -> Dict[str, Any]:
        """Procesa un webhook de Pub/Sub proveniente de Gmail."""

        self._validate_auth(payload, auth_header)

        message = payload.get("message") or {}
        attributes = message.get("attributes") or {}
        data_b64 = message.get("data")

        if not data_b64:
            logger.debug("agente_g_push_missing_data", extra={"attributes": attributes})
            return {"status": "ignored", "reason": "missing_data"}

        try:
            decoded = base64.b64decode(data_b64)
            gmail_payload = json.loads(decoded.decode("utf-8"))
        except (ValueError, json.JSONDecodeError) as exc:
            logger.warning("agente_g_push_decode_error", extra={"error": str(exc)})
            return {"status": "ignored", "reason": "invalid_payload"}

        history_id = str(gmail_payload.get("historyId")) if gmail_payload.get("historyId") else None
        email_address = gmail_payload.get("emailAddress")

        if not history_id:
            return {"status": "ignored", "reason": "missing_history_id"}

        status = self.get_status()
        now = self._clock().isoformat()
        start_history_id = status.get("last_history_id") or status.get("history_id") or history_id

        result: Dict[str, Any] = {
            "status": "processed",
            "history_id": history_id,
            "start_history_id": str(start_history_id) if start_history_id else None,
            "email_address": email_address,
            "received_at": now,
            "attributes": attributes,
        }

        if not status.get("active"):
            status["last_history_id"] = history_id
            status["updated_at"] = now
            self._write_status(status)
            result["status"] = "inactive"
            return result

        updates: List[Dict[str, Any]] = []
        history_snapshot: Dict[str, Any] | None = None

        try:
            history_response = self.gmail.list_history(
                start_history_id=str(start_history_id),
                max_results=self.settings.max_history_items,
                history_types=["messageAdded", "messageDeleted", "labelAdded", "labelRemoved"],
            )
            updates = self._extract_updates(history_response)
            history_snapshot = {
                "gmail_payload": gmail_payload,
                "history_response": history_response,
                "received_at": now,
                "topic": attributes.get("subscription"),
            }
            result["update_count"] = len(updates)
        except HttpError as exc:
            logger.warning("agente_g_history_error", extra={"error": str(exc)})
            status["last_error"] = str(exc)
            result.update({"status": "error", "error": "history_fetch_failed", "error_detail": str(exc)})
        except Exception as exc:  # pragma: no cover - protección adicional
            logger.exception("agente_g_history_unexpected_error")
            status["last_error"] = str(exc)
            result.update({"status": "error", "error": "unexpected", "error_detail": str(exc)})
        else:
            status.pop("last_error", None)

        status["last_history_id"] = history_id
        status["updated_at"] = now
        self._write_status(status)

        if updates:
            snapshot_path = self._write_history_snapshot({**history_snapshot, "updates": updates}) if history_snapshot else None
            if snapshot_path:
                result["snapshot_path"] = snapshot_path
        result["updates"] = updates
        return result

    # ------------------------------------------------------------------
    # Utilidades internas
    # ------------------------------------------------------------------

    def _validate_auth(self, payload: Dict[str, Any], auth_header: str | None) -> None:
        expected_token = self.settings.verification_token
        if not expected_token:
            return

        if auth_header:
            if auth_header.strip() == f"Bearer {expected_token}":
                return

        attributes = (payload.get("message") or {}).get("attributes") or {}
        token_attr = attributes.get("token") or attributes.get("authToken")
        if token_attr == expected_token:
            return

        raise PermissionError("Token de verificación inválido para push de Agente G")

    def _extract_updates(self, history_response: Dict[str, Any]) -> List[Dict[str, Any]]:
        updates: List[Dict[str, Any]] = []
        for entry in history_response.get("history", []) or []:
            entry_id = entry.get("id")
            for added in entry.get("messagesAdded", []) or []:
                message = added.get("message", {})
                updates.append(
                    {
                        "type": "message_added",
                        "message_id": message.get("id"),
                        "thread_id": message.get("threadId"),
                        "label_ids": message.get("labelIds"),
                        "history_entry_id": entry_id,
                    }
                )
            for removed in entry.get("messagesDeleted", []) or []:
                message = removed.get("message", {})
                updates.append(
                    {
                        "type": "message_deleted",
                        "message_id": message.get("id"),
                        "thread_id": message.get("threadId"),
                        "history_entry_id": entry_id,
                    }
                )
            for labels_added in entry.get("labelsAdded", []) or []:
                message = labels_added.get("message", {})
                updates.append(
                    {
                        "type": "label_added",
                        "message_id": message.get("id"),
                        "thread_id": message.get("threadId"),
                        "label_ids": labels_added.get("labelIds"),
                        "history_entry_id": entry_id,
                    }
                )
            for labels_removed in entry.get("labelsRemoved", []) or []:
                message = labels_removed.get("message", {})
                updates.append(
                    {
                        "type": "label_removed",
                        "message_id": message.get("id"),
                        "thread_id": message.get("threadId"),
                        "label_ids": labels_removed.get("labelIds"),
                        "history_entry_id": entry_id,
                    }
                )
        return updates

    def _write_history_snapshot(self, snapshot: Dict[str, Any]) -> str:
        timestamp = self._clock().strftime("%Y%m%dT%H%M%S%f")
        filename = f"push_{timestamp}_{uuid4().hex[:6]}.json"
        path = self.settings.history_dir / filename
        path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
        return str(path)

    def _read_status(self) -> Dict[str, Any]:
        if not self.settings.status_file.exists():
            return {"active": False, "updated_at": self._clock().isoformat()}
        try:
            content = self.settings.status_file.read_text(encoding="utf-8")
            if not content.strip():
                return {"active": False, "updated_at": self._clock().isoformat()}
            return json.loads(content)
        except json.JSONDecodeError:
            logger.warning(
                "agente_g_push_status_corrupt",
                extra={"path": str(self.settings.status_file)},
            )
            return {"active": False, "updated_at": self._clock().isoformat()}

    def _write_status(self, status: Dict[str, Any]) -> None:
        self.settings.status_file.write_text(json.dumps(status, indent=2, ensure_ascii=False), encoding="utf-8")
        self._status_cache = copy.deepcopy(status)


__all__ = ["AgenteGPushService", "AgenteGPushSettings"]
