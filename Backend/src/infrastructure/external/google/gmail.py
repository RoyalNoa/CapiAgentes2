"""Gmail helpers for Agente G."""
from __future__ import annotations

import base64
from email.message import EmailMessage
from typing import Any, Dict, Iterable, List, Optional, Sequence

from googleapiclient.errors import HttpError

from .auth import GoogleServiceFactory, GoogleOAuthSettings, GoogleCredentialsManager

GMAIL_READ_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
GMAIL_MODIFY_SCOPE = "https://www.googleapis.com/auth/gmail.modify"


class GmailClient:
    """Thin wrapper over the Gmail API with sensible defaults."""

    def __init__(self, service_factory: GoogleServiceFactory, user_id: str = "me") -> None:
        self._service_factory = service_factory
        self._user_id = user_id or "me"

    def list_messages(
        self,
        *,
        query: str | None = None,
        label_ids: Iterable[str] | None = None,
        max_results: int = 10,
        page_token: str | None = None,
    ) -> dict:
        service = self._service_factory.get_service("gmail", "v1", scopes=[GMAIL_READ_SCOPE])
        kwargs = {
            "userId": self._user_id,
            "maxResults": max(1, min(max_results, 100)),
        }
        if query:
            kwargs["q"] = query
        if label_ids:
            kwargs["labelIds"] = list(label_ids)
        if page_token:
            kwargs["pageToken"] = page_token
        return service.users().messages().list(**kwargs).execute()

    def get_message(self, message_id: str, *, format: str = "metadata") -> dict:
        service = self._service_factory.get_service("gmail", "v1", scopes=[GMAIL_READ_SCOPE])
        return service.users().messages().get(userId=self._user_id, id=message_id, format=format).execute()

    def send_plain_text(
        self,
        *,
        to: List[str],
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        sender: Optional[str] = None,
    ) -> dict:
        if not to:
            raise ValueError("At least one recipient is required to send an email")

        message = EmailMessage()
        message["To"] = ", ".join(sorted(set(to)))
        if cc:
            message["Cc"] = ", ".join(sorted(set(cc)))
        if sender:
            message["From"] = sender
        message["Subject"] = subject
        message.set_content(body or "")

        service = self._service_factory.get_service("gmail", "v1", scopes=[GMAIL_MODIFY_SCOPE])
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
        return service.users().messages().send(userId=self._user_id, body={"raw": raw}).execute()

    def watch_mailbox(
        self,
        *,
        topic_name: str,
        label_ids: Iterable[str] | None = None,
        label_filter_action: str | None = None,
    ) -> Dict[str, Any]:
        """Registers a Gmail push notification watch using Pub/Sub."""
        if not topic_name:
            raise ValueError("topic_name is required to create a Gmail watch")

        body: Dict[str, Any] = {"topicName": topic_name}
        if label_ids:
            body["labelIds"] = list(label_ids)
        if label_filter_action in {"include", "exclude"}:
            body["labelFilterAction"] = label_filter_action

        service = self._service_factory.get_service("gmail", "v1", scopes=[GMAIL_READ_SCOPE])
        return service.users().watch(userId=self._user_id, body=body).execute()

    def stop_watch(self) -> Dict[str, Any]:
        """Stops any active Gmail watch for the configured user."""
        service = self._service_factory.get_service("gmail", "v1", scopes=[GMAIL_READ_SCOPE])
        return service.users().stop(userId=self._user_id, body={}).execute()

    def list_history(
        self,
        *,
        start_history_id: str,
        history_types: Sequence[str] | None = None,
        label_id: str | None = None,
        max_results: int = 100,
        page_token: str | None = None,
    ) -> Dict[str, Any]:
        """Fetches Gmail history entries starting from the provided history id."""
        if not start_history_id:
            raise ValueError("start_history_id is required to list Gmail history")

        service = self._service_factory.get_service("gmail", "v1", scopes=[GMAIL_READ_SCOPE])
        kwargs: Dict[str, Any] = {
            "userId": self._user_id,
            "startHistoryId": start_history_id,
            "maxResults": max(1, min(int(max_results or 100), 500)),
        }
        if history_types:
            kwargs["historyTypes"] = list(history_types)
        if label_id:
            kwargs["labelId"] = label_id
        if page_token:
            kwargs["pageToken"] = page_token
        return service.users().history().list(**kwargs).execute()

    @staticmethod
    def build(credentials_settings: GoogleOAuthSettings) -> "GmailClient":
        manager = GoogleCredentialsManager(credentials_settings)
        factory = GoogleServiceFactory(manager)
        return GmailClient(factory, user_id=credentials_settings.agent_email or "me")


__all__ = ["GmailClient", "GMAIL_READ_SCOPE", "GMAIL_MODIFY_SCOPE"]
