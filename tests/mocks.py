"""Shared mock helpers for building fake Google API clients and QuickBooks HTTP."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from tests.fixtures import (
    DRIVE_LIST_RESPONSE,
    GMAIL_LIST_RESPONSE,
    GMAIL_MESSAGES,
    QB_BILL_RESPONSE,
    QB_CUSTOMER_RESPONSE,
    QB_INVOICE_RESPONSE,
    QB_PAYMENT_RESPONSE,
)

# ──────────────────────────────────────────────────────────────────────
# Gmail mock client (simulates googleapiclient.discovery.Resource)
# ──────────────────────────────────────────────────────────────────────

def make_gmail_client(
    list_response: dict[str, Any] | None = None,
    messages: dict[str, Any] | None = None,
) -> MagicMock:
    """Return a mock Gmail API client wired to fixture data."""
    lr = list_response if list_response is not None else GMAIL_LIST_RESPONSE
    msgs = messages or GMAIL_MESSAGES

    client = MagicMock()

    # Build a stable chain: client.users() -> users_resource
    users_resource = MagicMock()
    client.users.return_value = users_resource

    messages_resource = MagicMock()
    users_resource.messages.return_value = messages_resource

    # .list(...).execute() -> lr
    list_req = MagicMock()
    list_req.execute.return_value = lr
    messages_resource.list.return_value = list_req

    # .get(...).execute() -> individual message
    def _get_message(userId: str = "me", id: str = "", format: str = "metadata") -> MagicMock:
        req = MagicMock()
        req.execute.return_value = msgs.get(id, {})
        return req

    messages_resource.get.side_effect = _get_message

    return client


# ──────────────────────────────────────────────────────────────────────
# Drive mock client
# ──────────────────────────────────────────────────────────────────────

def make_drive_client(
    list_response: dict[str, Any] | None = None,
) -> MagicMock:
    """Return a mock Drive API client wired to fixture data."""
    lr = list_response if list_response is not None else DRIVE_LIST_RESPONSE

    client = MagicMock()

    files_resource = MagicMock()
    client.files.return_value = files_resource

    list_req = MagicMock()
    list_req.execute.return_value = lr
    files_resource.list.return_value = list_req

    return client


# ──────────────────────────────────────────────────────────────────────
# QuickBooks mock HTTP client
# ──────────────────────────────────────────────────────────────────────

_QB_RESPONSES: dict[str, dict[str, Any]] = {
    "Invoice": QB_INVOICE_RESPONSE,
    "Customer": QB_CUSTOMER_RESPONSE,
    "Payment": QB_PAYMENT_RESPONSE,
    "Bill": QB_BILL_RESPONSE,
}


def make_qb_http_client(
    responses: dict[str, dict[str, Any]] | None = None,
) -> MagicMock:
    """Return a mock requests-like HTTP client that handles QB queries."""
    resp_map = responses or _QB_RESPONSES

    http = MagicMock()

    def _get(url: str, params: dict[str, Any] | None = None, **kwargs: Any) -> MagicMock:
        resp = MagicMock()
        if params and "query" in params:
            sql = params["query"]
            # Extract entity type from "SELECT * FROM <EntityType>"
            for etype in resp_map:
                if etype in sql:
                    resp.json.return_value = resp_map[etype]
                    resp.status_code = 200
                    return resp
        resp.json.return_value = {"QueryResponse": {}}
        resp.status_code = 200
        return resp

    http.get.side_effect = _get
    return http
