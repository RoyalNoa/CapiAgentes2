"""Google Calendar helpers for Agente G."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from .auth import GoogleServiceFactory, GoogleOAuthSettings, GoogleCredentialsManager

CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.events"


class CalendarClient:
    """Wrapper for creating basic calendar events."""

    def __init__(self, service_factory: GoogleServiceFactory, calendar_id: str = "primary") -> None:
        self._service_factory = service_factory
        self._calendar_id = calendar_id or "primary"

    def list_events(
        self,
        *,
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        max_results: int = 20,
        q: Optional[str] = None,
    ) -> dict:
        service = self._service_factory.get_service("calendar", "v3", scopes=[CALENDAR_SCOPE])
        params = {
            "calendarId": self._calendar_id,
            "maxResults": max(1, min(max_results, 2500)),
            "singleEvents": True,
            "orderBy": "startTime",
        }
        if time_min:
            params["timeMin"] = time_min
        if time_max:
            params["timeMax"] = time_max
        if q:
            params["q"] = q
        return service.events().list(**params).execute()

    def create_event(
        self,
        *,
        summary: str,
        start_iso: str,
        end_iso: str,
        description: Optional[str] = None,
        attendees: Optional[list[str]] = None,
        timezone: str | None = None,
    ) -> dict:
        service = self._service_factory.get_service("calendar", "v3", scopes=[CALENDAR_SCOPE])
        event_body = {
            "summary": summary,
            "description": description or "",
            "start": self._build_datetime_block(start_iso, timezone),
            "end": self._build_datetime_block(end_iso, timezone),
        }
        if attendees:
            event_body["attendees"] = [{"email": email.strip()} for email in attendees if email.strip()]
        return service.events().insert(calendarId=self._calendar_id, body=event_body).execute()

    @staticmethod
    def _build_datetime_block(value: str, timezone: str | None) -> dict:
        block: dict[str, str] = {}
        if value.endswith("Z") or value.lower().endswith("+00:00"):
            block["dateTime"] = value
            block["timeZone"] = timezone or "UTC"
            return block
        try:
            # Attempt to parse isoformat; fallback to all-day event
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            block["dateTime"] = value
            if timezone:
                block["timeZone"] = timezone
        except ValueError:
            block["date"] = value.split("T")[0]
            if timezone:
                block["timeZone"] = timezone
        return block

    @staticmethod
    def build(settings: GoogleOAuthSettings) -> "CalendarClient":
        manager = GoogleCredentialsManager(settings)
        factory = GoogleServiceFactory(manager)
        return CalendarClient(factory)


__all__ = ["CalendarClient", "CALENDAR_SCOPE"]
