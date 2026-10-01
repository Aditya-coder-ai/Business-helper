"""Test fixtures — sample API responses for Gmail, Drive, QuickBooks.

Includes edge cases: empty mailbox, attachment-only email, deleted file,
expired token, rate-limit 429, malformed JSON, duplicate item.
"""

from __future__ import annotations

from typing import Any

# ──────────────────────────────────────────────────────────────────────
# GMAIL FIXTURES
# ──────────────────────────────────────────────────────────────────────

GMAIL_LIST_RESPONSE = {
    "messages": [
        {"id": "msg001", "threadId": "t001"},
        {"id": "msg002", "threadId": "t002"},
        {"id": "msg003", "threadId": "t003"},  # excluded (SPAM)
        {"id": "msg004", "threadId": "t004"},  # attachment-only
        {"id": "msg001", "threadId": "t001"},  # duplicate
    ]
}

GMAIL_EMPTY_LIST: dict[str, Any] = {"messages": []}
GMAIL_EMPTY_MAILBOX: dict[str, Any] = {}  # no "messages" key at all

GMAIL_MSG_001 = {
    "id": "msg001",
    "threadId": "t001",
    "labelIds": ["INBOX"],
    "snippet": "Here is the Q3 report.",
    "internalDate": "1695000000000",
    "payload": {
        "headers": [
            {"name": "Subject", "value": "Q3 Financial Report"},
            {"name": "From", "value": "alice@company.com"},
            {"name": "Date", "value": "Mon, 18 Sep 2023 12:00:00 +0000"},
        ]
    },
}

GMAIL_MSG_002 = {
    "id": "msg002",
    "threadId": "t002",
    "labelIds": ["INBOX"],
    "snippet": "Invoice #1234 attached.",
    "internalDate": "1695100000000",
    "payload": {
        "headers": [
            {"name": "Subject", "value": "Invoice from Vendor"},
            {"name": "From", "value": "billing@vendor.com"},
            {"name": "Date", "value": "Tue, 19 Sep 2023 15:46:40 +0000"},
        ]
    },
}

GMAIL_MSG_003_EXCLUDED = {
    "id": "msg003",
    "threadId": "t003",
    "labelIds": ["SPAM"],
    "snippet": "You won a prize!",
    "internalDate": "1695200000000",
    "payload": {
        "headers": [
            {"name": "Subject", "value": "WINNER"},
            {"name": "From", "value": "spam@evil.com"},
            {"name": "Date", "value": "Wed, 20 Sep 2023 10:00:00 +0000"},
        ]
    },
}

GMAIL_MSG_004_ATTACHMENT_ONLY = {
    "id": "msg004",
    "threadId": "t004",
    "labelIds": ["INBOX"],
    "snippet": "",
    "internalDate": "1695300000000",
    "payload": {
        "headers": [
            {"name": "Subject", "value": "(no subject)"},
            {"name": "From", "value": "bob@company.com"},
            {"name": "Date", "value": "Thu, 21 Sep 2023 18:00:00 +0000"},
        ]
    },
}

GMAIL_MESSAGES = {
    "msg001": GMAIL_MSG_001,
    "msg002": GMAIL_MSG_002,
    "msg003": GMAIL_MSG_003_EXCLUDED,
    "msg004": GMAIL_MSG_004_ATTACHMENT_ONLY,
}

# ──────────────────────────────────────────────────────────────────────
# GOOGLE DRIVE FIXTURES
# ──────────────────────────────────────────────────────────────────────

DRIVE_LIST_RESPONSE = {
    "files": [
        {
            "id": "file001",
            "name": "Q3 Report.xlsx",
            "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "modifiedTime": "2023-09-18T14:30:00Z",
            "owners": [{"emailAddress": "alice@company.com"}],
            "webViewLink": "https://docs.google.com/spreadsheets/d/file001",
        },
        {
            "id": "file002",
            "name": "Meeting Notes.docx",
            "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "modifiedTime": "2023-09-19T10:00:00Z",
            "owners": [{"emailAddress": "bob@company.com"}],
            "webViewLink": "https://docs.google.com/document/d/file002",
        },
        {
            "id": "file003_excluded",
            "name": "Private",
            "mimeType": "application/vnd.google-apps.folder",
            "modifiedTime": "2023-09-20T08:00:00Z",
            "owners": [{"emailAddress": "alice@company.com"}],
            "webViewLink": "",
        },
        {
            "id": "file004_deleted",
            "name": "Old Draft",
            "mimeType": "application/vnd.google-apps.document",
            "modifiedTime": "2023-09-17T06:00:00Z",
            "trashed": True,
            "owners": [],
            "webViewLink": "",
        },
    ]
}

DRIVE_EMPTY_LIST: dict[str, Any] = {"files": []}

# ──────────────────────────────────────────────────────────────────────
# QUICKBOOKS FIXTURES
# ──────────────────────────────────────────────────────────────────────

QB_INVOICE_RESPONSE = {
    "QueryResponse": {
        "Invoice": [
            {
                "Id": "101",
                "DocNumber": "INV-1001",
                "TotalAmt": 2500.00,
                "MetaData": {
                    "CreateTime": "2023-09-15T08:00:00-07:00",
                    "LastUpdatedTime": "2023-09-18T12:00:00-07:00",
                },
            },
            {
                "Id": "102",
                "DocNumber": "INV-1002",
                "TotalAmt": 750.50,
                "MetaData": {
                    "CreateTime": "2023-09-16T09:00:00-07:00",
                    "LastUpdatedTime": "2023-09-19T14:00:00-07:00",
                },
            },
        ]
    }
}

QB_CUSTOMER_RESPONSE = {
    "QueryResponse": {
        "Customer": [
            {
                "Id": "201",
                "DisplayName": "Acme Corp",
                "MetaData": {
                    "CreateTime": "2023-01-10T10:00:00-07:00",
                    "LastUpdatedTime": "2023-09-01T11:00:00-07:00",
                },
            },
        ]
    }
}

QB_PAYMENT_RESPONSE: dict[str, object] = {"QueryResponse": {"Payment": []}}
QB_BILL_RESPONSE: dict[str, object] = {"QueryResponse": {"Bill": []}}

QB_EMPTY_RESPONSE: dict[str, object] = {"QueryResponse": {}}

QB_MALFORMED_RESPONSE = "NOT VALID JSON {{{{"

# ──────────────────────────────────────────────────────────────────────
# ERROR FIXTURES
# ──────────────────────────────────────────────────────────────────────


class MockHttpError(Exception):
    """Simulates an HTTP error with a status code."""

    def __init__(self, status_code: int, message: str = "Error") -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTP {status_code}: {message}")


class ExpiredTokenError(Exception):
    """Simulates an expired OAuth token."""

    def __init__(self) -> None:
        super().__init__("Token has expired and cannot be refreshed")


class RateLimitError(MockHttpError):
    """429 Too Many Requests."""

    def __init__(self) -> None:
        super().__init__(429, "Rate limit exceeded")
