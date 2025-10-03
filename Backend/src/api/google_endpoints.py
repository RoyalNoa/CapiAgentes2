"""Endpoints HTTP para integraciones de Google (Agente G)."""
from __future__ import annotations

import json
from typing import List, Optional

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from src.core.logging import get_logger
from src.infrastructure.external.google import (
    GoogleCredentialsManager,
    GoogleOAuthSettings,
    GoogleServiceFactory,
    GmailClient,
)

from ia_workspace.agentes.agente_g import AgenteGPushService, AgenteGPushSettings


logger = get_logger(__name__)
router = APIRouter(prefix="/api/google", tags=["google"])

_push_service: AgenteGPushService | None = None


def _get_push_service() -> AgenteGPushService:
    global _push_service
    if _push_service is None:
        google_settings = GoogleOAuthSettings.load_from_env()
        manager = GoogleCredentialsManager(google_settings)
        factory = GoogleServiceFactory(manager)
        gmail_client = GmailClient(factory, user_id=google_settings.agent_email or "me")
        push_settings = AgenteGPushSettings.load_from_env()
        _push_service = AgenteGPushService(gmail_client=gmail_client, settings=push_settings)
    return _push_service


class WatchRequest(BaseModel):
    topic_name: Optional[str] = Field(default=None, description="Topic de Pub/Sub a utilizar")
    label_ids: Optional[List[str]] = Field(default=None, description="Filtro de etiquetas para la suscripción")
    label_filter_action: Optional[str] = Field(
        default=None, description="Acción para etiquetas (include | exclude)"
    )


@router.get("/gmail/watch/status")
async def get_gmail_watch_status() -> dict:
    service = _get_push_service()
    status = service.get_status()
    return {"status": "ok", "data": status}


@router.post("/gmail/watch")
async def enable_gmail_watch(request: WatchRequest) -> dict:
    service = _get_push_service()
    try:
        status = service.enable_push(
            topic_name=request.topic_name,
            label_ids=request.label_ids,
            label_filter_action=request.label_filter_action,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "ok", "data": status}


@router.post("/gmail/watch/stop")
async def disable_gmail_watch() -> dict:
    service = _get_push_service()
    status = service.disable_push()
    return {"status": "ok", "data": status}


@router.post("/gmail/push")
async def gmail_push_webhook(request: Request, authorization: str | None = Header(default=None)) -> dict:
    service = _get_push_service()
    try:
        payload = await request.json()
    except json.JSONDecodeError as exc:
        logger.warning("agente_g_push_invalid_json", extra={"error": str(exc)})
        payload = {}

    try:
        result = service.handle_notification(payload, auth_header=authorization)
    except PermissionError as exc:
        logger.warning("agente_g_push_auth_failed")
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    return {"status": "ok", "data": result}


__all__ = ["router"]
