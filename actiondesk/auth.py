"""Google OAuth authentication helper for read-only Gmail & Drive access."""

from __future__ import annotations

import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build

from actiondesk.logging_config import get_logger

logger = get_logger(__name__)

GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
DRIVE_READONLY_SCOPE = "https://www.googleapis.com/auth/drive.readonly"

DEFAULT_CREDENTIALS_FILE = Path("credentials.json")
DEFAULT_TOKEN_FILE = Path("token.json")


class MissingCredentialsError(FileNotFoundError):
    """Raised when credentials.json is not found."""


def get_google_credentials(
    credentials_path: Path = DEFAULT_CREDENTIALS_FILE,
    token_path: Path = DEFAULT_TOKEN_FILE,
    scopes: list[str] | None = None,
) -> Credentials:
    """Load, refresh, or initiate OAuth 2.0 flow for Google credentials.

    Enforces that only read-only scopes are requested.
    """
    if scopes is None:
        scopes = [GMAIL_READONLY_SCOPE]

    # Safety check: enforce read-only scopes
    for s in scopes:
        if "readonly" not in s:
            raise ValueError(f"Hard constraint violation: non-readonly scope requested: {s}")

    creds: Credentials | None = None

    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(
                str(token_path), scopes
            )  # type: ignore[no-untyped-call]
        except Exception:
            logger.warning("auth.token_invalid", extra={"data": {"token_path": str(token_path)}})
            creds = None

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())  # type: ignore[no-untyped-call]
            token_path.write_text(creds.to_json(), encoding="utf-8")  # type: ignore[no-untyped-call]
            logger.info("auth.token_refreshed", extra={"data": {"token_path": str(token_path)}})
            return creds
        except Exception:
            logger.warning("auth.token_refresh_failed", extra={"data": {}})
            creds = None

    if not credentials_path.exists():
        msg = (
            f"Google OAuth credentials file '{credentials_path}' not found.\n\n"
            "To connect to live Gmail:\n"
            "1. Go to Google Cloud Console (https://console.cloud.google.com/)\n"
            "2. Create a project and enable the 'Gmail API'\n"
            "3. Configure OAuth Consent Screen (External, add your Gmail as a Test User)\n"
            "4. Go to 'Credentials' -> 'Create Credentials' -> 'OAuth client ID'\n"
            "5. Select Application type: 'Desktop app'\n"
            "6. Download the JSON and save it as 'credentials.json' in this project folder."
        )
        raise MissingCredentialsError(msg)

    # Launch local web server to complete OAuth consent
    logger.info("auth.flow_start", extra={"data": {"scopes": scopes}})
    flow = InstalledAppFlow.from_client_secrets_file(
        str(credentials_path), scopes
    )
    creds = flow.run_local_server(port=0)

    token_path.write_text(creds.to_json(), encoding="utf-8")
    logger.info("auth.token_saved", extra={"data": {"token_path": str(token_path)}})

    return creds


def get_gmail_service(
    credentials_path: Path = DEFAULT_CREDENTIALS_FILE,
    token_path: Path = DEFAULT_TOKEN_FILE,
) -> Resource:
    """Return an authenticated Gmail v1 API Resource client."""
    creds = get_google_credentials(
        credentials_path=credentials_path,
        token_path=token_path,
        scopes=[GMAIL_READONLY_SCOPE],
    )
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def get_drive_service(
    credentials_path: Path = DEFAULT_CREDENTIALS_FILE,
    token_path: Path = DEFAULT_TOKEN_FILE,
) -> Resource:
    """Return an authenticated Google Drive v3 API Resource client."""
    creds = get_google_credentials(
        credentials_path=credentials_path,
        token_path=token_path,
        scopes=[DRIVE_READONLY_SCOPE],
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def main() -> None:
    """CLI entrypoint to authenticate and test connection."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("ActionDesk -- Google OAuth Authorization")
    print("=" * 45)
    try:
        service = get_gmail_service()
        profile = service.users().getProfile(userId="me").execute()
        email = profile.get("emailAddress", "unknown")
        total_messages = profile.get("messagesTotal", 0)
        print("Connected successfully to Gmail!")
        print(f"Account: {email}")
        print(f"Total messages in mailbox: {total_messages}")
        print("token.json saved securely (ignored by git).")
    except MissingCredentialsError as exc:
        print(f"\n{exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"\nError during authorization: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
