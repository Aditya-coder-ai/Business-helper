"""Deterministic regex extractors for emails, phones, invoices, amounts, dates, and QB IDs."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

EMAIL_RE = re.compile(
    r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
    re.IGNORECASE,
)

PHONE_RE = re.compile(
    r"(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}\b"
)

INVOICE_NO_RE = re.compile(
    r"\b((?:INV|INVOICE|BILL)[-:\s#]*[A-Z0-9\-_]{3,20})\b",
    re.IGNORECASE,
)

AMOUNT_RE = re.compile(
    r"(?:(\$|€|£|USD|EUR|GBP)\s*([\d,]+(?:\.\d{1,2})?)|([\d,]+(?:\.\d{1,2})?)\s*(USD|EUR|GBP))",
    re.IGNORECASE,
)

QB_ID_RE = re.compile(
    r"\b(?:qb|quickbooks|txnid|listid)[-_\s]*(?:customer|vendor|invoice|id)?[:=\s]+([A-Za-z0-9\-_]+)\b",
    re.IGNORECASE,
)

DATE_PATTERNS = [
    r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b",
    r"\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b",
    (
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* "
        r"\d{1,2}(?:st|nd|rd|th)?,? \d{4}\b"
    ),
]
DATE_COMBINED_RE = re.compile("|".join(DATE_PATTERNS), re.IGNORECASE)


class ParsedAmount(BaseModel):
    """Normalized monetary figure with currency code."""

    amount: float
    currency: str = "USD"


class DeterministicResult(BaseModel):
    """Structured extraction outputs obtained without non-deterministic LLM inference."""

    emails: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
    invoice_numbers: list[str] = Field(default_factory=list)
    amounts: list[ParsedAmount] = Field(default_factory=list)
    dates: list[datetime] = Field(default_factory=list)
    quickbooks_ids: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DeterministicExtractor:
    """Extracts known business patterns from raw text deterministically."""

    @classmethod
    def extract_emails(cls, text: str) -> list[str]:
        found = EMAIL_RE.findall(text)
        seen: set[str] = set()
        res: list[str] = []
        for e in found:
            low = e.lower().strip()
            # Ignore trailing dot
            if low.endswith("."):
                low = low[:-1]
            if low and low not in seen:
                seen.add(low)
                res.append(low)
        return res

    @classmethod
    def extract_phones(cls, text: str) -> list[str]:
        raw_matches = PHONE_RE.findall(text)
        res: list[str] = []
        seen: set[str] = set()
        for p in raw_matches:
            cleaned = p.strip()
            # Filter out things that are too short or just dates
            digits_only = re.sub(r"\D", "", cleaned)
            if len(digits_only) >= 7 and cleaned not in seen:
                seen.add(cleaned)
                res.append(cleaned)
        return res

    @classmethod
    def extract_invoice_numbers(cls, text: str) -> list[str]:
        matches = INVOICE_NO_RE.findall(text)
        res: list[str] = []
        seen: set[str] = set()
        for num in matches:
            clean = num.strip()
            if clean and clean.upper() not in seen:
                seen.add(clean.upper())
                res.append(clean)
        return res

    @classmethod
    def extract_amounts(cls, text: str) -> list[ParsedAmount]:
        matches = AMOUNT_RE.findall(text)
        results: list[ParsedAmount] = []
        seen: set[tuple[float, str]] = set()

        sym_map = {"$": "USD", "€": "EUR", "£": "GBP"}

        for sym1, val1, val2, sym2 in matches:
            sym = sym1 or sym2
            raw_val = val1 or val2
            if not raw_val:
                continue
            cur = sym_map.get(sym.upper(), sym.upper() if sym else "USD")
            try:
                numeric = float(raw_val.replace(",", ""))
                pair = (numeric, cur)
                if pair not in seen:
                    seen.add(pair)
                    results.append(ParsedAmount(amount=numeric, currency=cur))
            except ValueError:
                continue
        return results

    @classmethod
    def extract_dates(cls, text: str) -> list[datetime]:
        from dateutil.parser import parse as dtparse

        matches = DATE_COMBINED_RE.findall(text)
        dates: list[datetime] = []
        seen: set[datetime] = set()
        for m in matches:
            if not m:
                continue
            try:
                dt = dtparse(m, fuzzy=True)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if dt not in seen:
                    seen.add(dt)
                    dates.append(dt)
            except (ValueError, TypeError, OverflowError):
                continue
        return dates

    @classmethod
    def extract_quickbooks_ids(cls, text: str) -> dict[str, str]:
        matches = QB_ID_RE.finditer(text)
        qb_dict: dict[str, str] = {}
        for m in matches:
            full = m.group(0).lower()
            val = m.group(1).strip()
            if "customer" in full:
                qb_dict["customer_id"] = val
            elif "vendor" in full or "supplier" in full:
                qb_dict["supplier_id"] = val
            elif "invoice" in full:
                qb_dict["invoice_id"] = val
            else:
                qb_dict["txnid"] = val
        return qb_dict

    @classmethod
    def extract(cls, text: str) -> DeterministicResult:
        """Run all deterministic extractors on input text."""
        return DeterministicResult(
            emails=cls.extract_emails(text),
            phones=cls.extract_phones(text),
            invoice_numbers=cls.extract_invoice_numbers(text),
            amounts=cls.extract_amounts(text),
            dates=cls.extract_dates(text),
            quickbooks_ids=cls.extract_quickbooks_ids(text),
        )
