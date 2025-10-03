"""Google Workspace integration helpers (OAuth, Gmail, Drive, Calendar)."""

from .auth import GoogleOAuthSettings, GoogleCredentialsManager, GoogleServiceFactory
from .gmail import GmailClient, GMAIL_READ_SCOPE, GMAIL_MODIFY_SCOPE
from .drive import DriveClient, DRIVE_SCOPE
from .calendar import CalendarClient, CALENDAR_SCOPE

__all__ = [
    "GoogleOAuthSettings",
    "GoogleCredentialsManager",
    "GoogleServiceFactory",
    "GmailClient",
    "GMAIL_READ_SCOPE",
    "GMAIL_MODIFY_SCOPE",
    "DriveClient",
    "DRIVE_SCOPE",
    "CalendarClient",
    "CALENDAR_SCOPE",
]

