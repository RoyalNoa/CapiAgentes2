"""OAuth helpers for Google Workspace integrations."""
from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Sequence

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

_TOKEN_URI = "https://oauth2.googleapis.com/token"


@dataclass(frozen=True)
class GoogleOAuthSettings:
    """Configuration resolved from environment variables."""

    client_id: str
    client_secret: str
    scopes: List[str]
    token_store: Path
    agent_email: str | None = None

    @staticmethod
    def load_from_env() -> "GoogleOAuthSettings":
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        scopes_raw = os.getenv("GOOGLE_OAUTH_SCOPES", "").strip()
        token_store_raw = os.getenv("GOOGLE_TOKEN_STORE")
        agent_email = os.getenv("GOOGLE_AGENT_EMAIL") or None

        if not client_id or not client_secret:
            raise RuntimeError("Google OAuth client id and secret must be configured via GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET")
        if not scopes_raw:
            raise RuntimeError("Google OAuth scopes must be provided via GOOGLE_OAUTH_SCOPES")
        if not token_store_raw:
            raise RuntimeError("Google token store path must be set in GOOGLE_TOKEN_STORE")

        scopes = [scope.strip() for scope in scopes_raw.replace(";", ",").split(",") if scope.strip()]
        if not scopes:
            raise RuntimeError("At least one Google OAuth scope is required")

        token_store = Path(token_store_raw).expanduser().resolve()
        token_store.parent.mkdir(parents=True, exist_ok=True)

        return GoogleOAuthSettings(
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes,
            token_store=token_store,
            agent_email=agent_email,
        )


class GoogleCredentialsManager:
    """Loads and refreshes OAuth credentials, persisting token updates safely."""

    def __init__(self, settings: GoogleOAuthSettings) -> None:
        self._settings = settings
        self._lock = threading.RLock()

    @property
    def settings(self) -> GoogleOAuthSettings:
        return self._settings

    def load_credentials(self, scopes: Iterable[str] | None = None) -> Credentials:
        requested_scopes = list(scopes) if scopes else self._settings.scopes
        with self._lock:
            token_payload = self._read_token_file()
            refresh_token = token_payload.get("refresh_token")
            if not refresh_token:
                raise RuntimeError(
                    "Refresh token not found in token store. Run scripts/bootstrap_google_oauth.py to bootstrap credentials."
                )

            expiry = self._parse_expiry(token_payload.get("expiry"))
            credentials = Credentials(
                token=token_payload.get("access_token"),
                refresh_token=refresh_token,
                token_uri=_TOKEN_URI,
                client_id=self._settings.client_id,
                client_secret=self._settings.client_secret,
                scopes=requested_scopes,
                expiry=expiry,
            )

            if not credentials.valid:
                if credentials.expired and credentials.refresh_token:
                    credentials.refresh(Request())
                    self._persist_credentials(credentials)
                elif not credentials.expired:
                    # token invalid for another reason (e.g. revoked). Let API raise.
                    pass
                else:
                    raise RuntimeError("Google credentials invalid and could not be refreshed")

            return credentials

    def _read_token_file(self) -> dict:
        if not self._settings.token_store.exists():
            return {}
        try:
            text = self._settings.token_store.read_text(encoding="utf-8")
            if not text.strip():
                return {}
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid JSON token store at {self._settings.token_store}: {exc}") from exc

    def persist_credentials(self, credentials: Credentials) -> None:
        with self._lock:
            self._persist_credentials(credentials)

    def _persist_credentials(self, credentials: Credentials) -> None:
        data = json.loads(credentials.to_json())
        payload = {
            "access_token": data.get("token"),
            "refresh_token": data.get("refresh_token"),
            "expiry": data.get("expiry"),
            "scopes": data.get("scopes") or credentials.scopes,
        }
        tmp_path = self._settings.token_store.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp_path.replace(self._settings.token_store)

    @staticmethod
    def _parse_expiry(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            # Google stores expiry in RFC3339 format
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None


class GoogleServiceFactory:
    """Lazily builds Google API clients reusing refreshed credentials."""

    def __init__(self, credentials_manager: GoogleCredentialsManager) -> None:
        self._credentials_manager = credentials_manager
        self._cache: dict[tuple[str, str, tuple[str, ...]], dict[str, object]] = {}
        self._lock = threading.RLock()

    def get_service(self, service_name: str, version: str, scopes: Sequence[str] | None = None):
        from googleapiclient.discovery import build

        scope_tuple = tuple(sorted(scopes or self._credentials_manager.settings.scopes))
        cache_key = (service_name, version, scope_tuple)

        with self._lock:
            cached = self._cache.get(cache_key)
            if cached:
                credentials = cached["credentials"]  # type: ignore[assignment]
                if isinstance(credentials, Credentials) and credentials.expired and credentials.refresh_token:
                    credentials.refresh(Request())
                    self._credentials_manager.persist_credentials(credentials)
                return cached["service"]

            credentials = self._credentials_manager.load_credentials(scope_tuple)
            service = build(service_name, version, credentials=credentials, cache_discovery=False)
            self._cache[cache_key] = {"service": service, "credentials": credentials}
            return service
