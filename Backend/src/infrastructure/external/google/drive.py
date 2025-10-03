"""Google Drive helpers for Agente G."""
from __future__ import annotations

import io
from datetime import datetime
from typing import Iterable, Optional

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

from .auth import GoogleServiceFactory, GoogleOAuthSettings, GoogleCredentialsManager

DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.file"


class DriveClient:
    """Wrapper for a subset of Drive API operations used by Agente G."""

    def __init__(self, service_factory: GoogleServiceFactory) -> None:
        self._service_factory = service_factory

    def list_files(
        self,
        *,
        query: str | None = None,
        page_size: int = 20,
        page_token: str | None = None,
        fields: str = "files(id, name, mimeType, modifiedTime, webViewLink), nextPageToken",
    ) -> dict:
        service = self._service_factory.get_service("drive", "v3", scopes=[DRIVE_SCOPE])
        params = {
            "pageSize": max(1, min(page_size, 100)),
            "fields": fields,
            "orderBy": "modifiedTime desc",
            "supportsAllDrives": False,
        }
        if query:
            params["q"] = query
        if page_token:
            params["pageToken"] = page_token
        return service.files().list(**params).execute()

    def create_text_file(self, *, name: str, content: str, folder_id: str | None = None) -> dict:
        service = self._service_factory.get_service("drive", "v3", scopes=[DRIVE_SCOPE])
        metadata = {
            "name": name.strip() or f"agente-g-{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            "mimeType": "text/plain",
        }
        if folder_id:
            metadata["parents"] = [folder_id]
        media = MediaIoBaseUpload(io.BytesIO(content.encode("utf-8")), mimetype="text/plain")
        return service.files().create(body=metadata, media_body=media, fields="id, name, webViewLink").execute()

    @staticmethod
    def build(settings: GoogleOAuthSettings) -> "DriveClient":
        manager = GoogleCredentialsManager(settings)
        factory = GoogleServiceFactory(manager)
        return DriveClient(factory)


__all__ = ["DriveClient", "DRIVE_SCOPE"]
