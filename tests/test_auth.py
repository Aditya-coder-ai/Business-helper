"""Tests for actiondesk.auth OAuth module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from actiondesk.auth import (
    DRIVE_READONLY_SCOPE,
    GMAIL_READONLY_SCOPE,
    MissingCredentialsError,
    get_drive_service,
    get_gmail_service,
    get_google_credentials,
)


class TestGoogleAuth:
    def test_missing_credentials_raises_error(self, tmp_path: Path) -> None:
        creds_file = tmp_path / "credentials.json"
        token_file = tmp_path / "token.json"
        with pytest.raises(MissingCredentialsError, match="credentials.json.*not found"):
            get_google_credentials(credentials_path=creds_file, token_path=token_file)

    def test_write_scope_rejected_by_hard_constraint(self, tmp_path: Path) -> None:
        creds_file = tmp_path / "credentials.json"
        token_file = tmp_path / "token.json"
        with pytest.raises(ValueError, match="Hard constraint violation"):
            get_google_credentials(
                credentials_path=creds_file,
                token_path=token_file,
                scopes=["https://www.googleapis.com/auth/gmail.send"],
            )

    @patch("actiondesk.auth.Credentials")
    def test_existing_valid_token_loaded(
        self, mock_creds_cls: MagicMock, tmp_path: Path
    ) -> None:
        creds_file = tmp_path / "credentials.json"
        token_file = tmp_path / "token.json"
        token_file.write_text('{"token": "xyz"}', encoding="utf-8")

        mock_instance = MagicMock()
        mock_instance.valid = True
        mock_creds_cls.from_authorized_user_file.return_value = mock_instance

        creds = get_google_credentials(credentials_path=creds_file, token_path=token_file)
        assert creds == mock_instance
        mock_creds_cls.from_authorized_user_file.assert_called_once_with(
            str(token_file), [GMAIL_READONLY_SCOPE]
        )

    @patch("actiondesk.auth.Credentials")
    @patch("actiondesk.auth.Request")
    def test_expired_token_refreshed(
        self, mock_request_cls: MagicMock, mock_creds_cls: MagicMock, tmp_path: Path
    ) -> None:
        creds_file = tmp_path / "credentials.json"
        token_file = tmp_path / "token.json"
        token_file.write_text('{"token": "old"}', encoding="utf-8")

        mock_instance = MagicMock()
        mock_instance.valid = False
        mock_instance.expired = True
        mock_instance.refresh_token = "refresh-xyz"  # noqa: S105
        mock_instance.to_json.return_value = '{"token": "new"}'
        mock_creds_cls.from_authorized_user_file.return_value = mock_instance

        creds = get_google_credentials(credentials_path=creds_file, token_path=token_file)
        assert creds == mock_instance
        mock_instance.refresh.assert_called_once()
        assert token_file.read_text(encoding="utf-8") == '{"token": "new"}'

    @patch("actiondesk.auth.InstalledAppFlow")
    def test_interactive_flow_on_fresh_login(
        self, mock_flow_cls: MagicMock, tmp_path: Path
    ) -> None:
        creds_file = tmp_path / "credentials.json"
        creds_file.write_text('{"installed": {"client_id": "123"}}', encoding="utf-8")
        token_file = tmp_path / "token.json"

        mock_flow = MagicMock()
        mock_creds = MagicMock()
        mock_creds.to_json.return_value = '{"token": "fresh"}'
        mock_flow.run_local_server.return_value = mock_creds
        mock_flow_cls.from_client_secrets_file.return_value = mock_flow

        creds = get_google_credentials(credentials_path=creds_file, token_path=token_file)
        assert creds == mock_creds
        mock_flow_cls.from_client_secrets_file.assert_called_once_with(
            str(creds_file), [GMAIL_READONLY_SCOPE]
        )
        assert token_file.read_text(encoding="utf-8") == '{"token": "fresh"}'

    @patch("actiondesk.auth.build")
    @patch("actiondesk.auth.get_google_credentials")
    def test_get_gmail_service(
        self, mock_get_creds: MagicMock, mock_build: MagicMock, tmp_path: Path
    ) -> None:
        mock_creds = MagicMock()
        mock_get_creds.return_value = mock_creds

        get_gmail_service(
            credentials_path=tmp_path / "creds.json",
            token_path=tmp_path / "token.json",
        )
        mock_get_creds.assert_called_once_with(
            credentials_path=tmp_path / "creds.json",
            token_path=tmp_path / "token.json",
            scopes=[GMAIL_READONLY_SCOPE],
        )
        mock_build.assert_called_once_with(
            "gmail", "v1", credentials=mock_creds, cache_discovery=False
        )

    @patch("actiondesk.auth.build")
    @patch("actiondesk.auth.get_google_credentials")
    def test_get_drive_service(
        self, mock_get_creds: MagicMock, mock_build: MagicMock, tmp_path: Path
    ) -> None:
        mock_creds = MagicMock()
        mock_get_creds.return_value = mock_creds

        get_drive_service(
            credentials_path=tmp_path / "creds.json",
            token_path=tmp_path / "token.json",
        )
        mock_get_creds.assert_called_once_with(
            credentials_path=tmp_path / "creds.json",
            token_path=tmp_path / "token.json",
            scopes=[DRIVE_READONLY_SCOPE],
        )
        mock_build.assert_called_once_with(
            "drive", "v3", credentials=mock_creds, cache_discovery=False
        )
