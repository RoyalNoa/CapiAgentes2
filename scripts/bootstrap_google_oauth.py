"""Bootstrap script to obtain Google OAuth refresh token for Agente G."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "Backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
BACKEND_SRC = BACKEND_ROOT / "src"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from src.infrastructure.external.google import GoogleOAuthSettings, GoogleCredentialsManager

AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"


def build_client_config(settings: GoogleOAuthSettings) -> dict:
    return {
        "installed": {
            "client_id": settings.client_id,
            "client_secret": settings.client_secret,
            "auth_uri": AUTH_URI,
            "token_uri": TOKEN_URI,
            "redirect_uris": ["http://localhost:8765/"],
        }
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap Google OAuth tokens for Agente G")
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser automatically")
    args = parser.parse_args()

    settings = GoogleOAuthSettings.load_from_env()
    manager = GoogleCredentialsManager(settings)

    flow = InstalledAppFlow.from_client_config(build_client_config(settings), scopes=settings.scopes)
    if args.no_browser:
        creds = flow.run_console()
    else:
        creds = flow.run_local_server(port=8765, prompt="consent", authorization_prompt_message="Autoriza Agente G para acceder a Google Workspace.")

    if not creds.refresh_token:
        raise RuntimeError("Google did not return a refresh token. Ensure you revoke previous tokens and re-run the script.")

    manager.persist_credentials(creds)
    print(f"Tokens stored in {settings.token_store}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
