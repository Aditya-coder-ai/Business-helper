"""Standardised ingestion record schema — validated with Pydantic."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator

SourceType = Literal["gmail", "drive", "quickbooks"]


class RawItem(BaseModel):
    """The standard record produced by every connector.

    Fields
    ------
    id              : deterministic, globally-unique key  (source + source_item_id hash)
    source          : which connector produced this
    source_item_id  : the ID in the upstream system
    source_url      : link back to the original object (best-effort)
    date            : authoritative timestamp from the source
    owner           : email / user who owns the item
    content         : textual payload (subject+snippet for mail, title for drive, etc.)
    content_hash    : SHA-256 of *content* — used for change detection
    fetched_at      : UTC timestamp when this record was fetched
    """

    id: str = Field(..., min_length=1)
    source: SourceType
    source_item_id: str = Field(..., min_length=1)
    source_url: str = ""
    date: datetime
    owner: str = ""
    content: str = ""
    content_hash: str = Field(..., min_length=1)
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("date", mode="before")
    @classmethod
    def _parse_date(cls, v: object) -> datetime:
        if isinstance(v, str):
            from dateutil.parser import parse as dtparse

            return dtparse(v)
        if isinstance(v, datetime):
            return v
        raise ValueError(f"Cannot parse date: {v!r}")

    @field_validator("date")
    @classmethod
    def _ensure_tz(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

    model_config = {"frozen": True}


def make_id(source: str, source_item_id: str) -> str:
    """Deterministic global ID from source + source_item_id."""
    return hashlib.sha256(f"{source}:{source_item_id}".encode()).hexdigest()[:24]


def content_hash(content: str) -> str:
    """SHA-256 hex digest of content for change detection."""
    return hashlib.sha256(content.encode()).hexdigest()
