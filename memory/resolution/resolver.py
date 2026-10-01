"""Entity resolution logic across email, phone, name, company, and relationships."""

from __future__ import annotations

import difflib
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from memory.models import Customer, ResolutionRecord, Supplier
from memory.repository import MemoryRepository

HIGH_CONFIDENCE_THRESHOLD = 0.85
MEDIUM_CONFIDENCE_THRESHOLD = 0.60


def make_entity_id(entity_type: str, seed: str) -> str:
    """Generate deterministic 24-character hexadecimal ID."""
    clean = seed.strip().lower()
    return hashlib.sha256(f"{entity_type}:{clean}".encode()).hexdigest()[:24]


@dataclass
class ResolutionDecision:
    """Result of entity resolution process."""

    entity_id: str
    is_merged: bool
    matched_entity_id: str | None
    confidence: float
    reasons: list[str]
    record: ResolutionRecord | None


class EntityResolver:
    """Discovers matches and links identity candidates across business sources."""

    def __init__(self, repo: MemoryRepository) -> None:
        self.repo = repo

    @staticmethod
    def _normalize_name(name: str) -> str:
        clean = name.strip().lower()
        for suffix in ("ltd.", "limited", "ltd", "inc.", "inc", "corp.", "corp", "llc", "co."):
            if clean.endswith(f" {suffix}"):
                clean = clean[: -len(suffix) - 1].strip()
        return clean

    @classmethod
    def _name_similarity(cls, a: str, b: str) -> float:
        na = a.strip().lower()
        nb = b.strip().lower()
        if not na or not nb:
            return 0.0
        if na == nb:
            return 1.0
        norm_a = cls._normalize_name(na)
        norm_b = cls._normalize_name(nb)
        if norm_a and norm_b and norm_a == norm_b:
            return 0.95
        # Check substring containment
        if na in nb or nb in na or (norm_a and norm_a in norm_b) or (norm_b and norm_b in norm_a):
            return 0.85
        return difflib.SequenceMatcher(None, na, nb).ratio()

    def resolve_customer(
        self,
        name: str,
        email: str = "",
        phone: str = "",
        company: str = "",
        source: str = "",
        timestamp: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ResolutionDecision:
        now = timestamp or datetime.now(timezone.utc)
        clean_email = email.strip().lower()
        clean_phone = phone.strip()
        clean_name = name.strip()
        clean_company = company.strip()

        # Deterministic candidate ID
        seed = clean_email or clean_phone or f"{clean_name}:{clean_company}"
        candidate_id = make_entity_id("customer", seed)

        # 1. Search candidates by email, phone, company, or name
        candidates = self.repo.find_customers_by_email_or_phone_or_company(
            email=clean_email if clean_email else None,
            phone=clean_phone if clean_phone else None,
            company=clean_company if clean_company else None,
            canonical_name=clean_name if clean_name else None,
        )

        best_match: Customer | None = None
        best_conf = 0.0
        best_reasons: list[str] = []

        for c in candidates:
            conf = 0.0
            reasons: list[str] = []

            # Email match
            if clean_email and c.email and clean_email == c.email.lower():
                conf = max(conf, 0.98)
                reasons.append(f"exact_email_match:{clean_email}")

            # Phone match
            if clean_phone and c.phone and clean_phone == c.phone:
                conf = max(conf, 0.92)
                reasons.append(f"exact_phone_match:{clean_phone}")

            # Canonical name similarity
            sim = self._name_similarity(clean_name, c.canonical_name)
            if sim >= 0.90:
                is_company_match = (
                    clean_company
                    and clean_company.lower() in (c.company or "").lower()
                )
                conf = max(conf, 0.88 if is_company_match else 0.75)
                reasons.append(f"high_name_similarity:{sim:.2f}")
            elif sim >= 0.70:
                conf = max(conf, 0.65)
                reasons.append(f"medium_name_similarity:{sim:.2f}")

            if conf > best_conf:
                best_conf = conf
                best_match = c
                best_reasons = reasons

        matched_id = best_match.id if best_match else "none"
        hash_seed = f"res:{candidate_id}:{matched_id}:{now.isoformat()}"
        rec_id = hashlib.sha256(hash_seed.encode()).hexdigest()[:24]

        # Decision handling
        if best_match and best_conf >= HIGH_CONFIDENCE_THRESHOLD:
            # Auto-merge: update interaction dates and contact details if empty
            merged_customer = Customer(
                id=best_match.id,
                canonical_name=best_match.canonical_name or clean_name,
                email=best_match.email or clean_email,
                phone=best_match.phone or clean_phone,
                company=best_match.company or clean_company,
                first_seen=best_match.first_seen or now,
                last_interaction=now,
                metadata={**best_match.metadata, **(metadata or {})},
                created_at=best_match.created_at,
                updated_at=now,
            )
            self.repo.upsert_customer(merged_customer)

            record = ResolutionRecord(
                id=rec_id,
                candidate_entity=candidate_id,
                matched_entity=best_match.id,
                confidence=best_conf,
                matching_reasons=best_reasons + ["auto_merged"],
                source=source,
                timestamp=now,
            )
            self.repo.insert_resolution_record(record)
            return ResolutionDecision(
                entity_id=best_match.id,
                is_merged=True,
                matched_entity_id=best_match.id,
                confidence=best_conf,
                reasons=best_reasons,
                record=record,
            )

        if best_match and best_conf >= MEDIUM_CONFIDENCE_THRESHOLD:
            # Possible match: Keep separate, do not auto-merge
            new_customer = Customer(
                id=candidate_id,
                canonical_name=clean_name or clean_email or candidate_id,
                email=clean_email,
                phone=clean_phone,
                company=clean_company,
                first_seen=now,
                last_interaction=now,
                metadata=metadata or {},
                created_at=now,
                updated_at=now,
            )
            self.repo.upsert_customer(new_customer)

            record = ResolutionRecord(
                id=rec_id,
                candidate_entity=candidate_id,
                matched_entity=best_match.id,
                confidence=best_conf,
                matching_reasons=best_reasons + ["possible_match_no_merge"],
                source=source,
                timestamp=now,
            )
            self.repo.insert_resolution_record(record)
            return ResolutionDecision(
                entity_id=candidate_id,
                is_merged=False,
                matched_entity_id=best_match.id,
                confidence=best_conf,
                reasons=best_reasons,
                record=record,
            )

        # Low confidence or no match: Keep separate
        new_customer = Customer(
            id=candidate_id,
            canonical_name=clean_name or clean_email or candidate_id,
            email=clean_email,
            phone=clean_phone,
            company=clean_company,
            first_seen=now,
            last_interaction=now,
            metadata=metadata or {},
            created_at=now,
            updated_at=now,
        )
        self.repo.upsert_customer(new_customer)

        record = ResolutionRecord(
            id=rec_id,
            candidate_entity=candidate_id,
            matched_entity=candidate_id,
            confidence=1.0 if not best_match else best_conf,
            matching_reasons=["new_distinct_entity"],
            source=source,
            timestamp=now,
        )
        self.repo.insert_resolution_record(record)
        return ResolutionDecision(
            entity_id=candidate_id,
            is_merged=False,
            matched_entity_id=None,
            confidence=1.0 if not best_match else best_conf,
            reasons=["new_distinct_entity"],
            record=record,
        )

    def resolve_supplier(
        self,
        name: str,
        email: str = "",
        phone: str = "",
        company: str = "",
        source: str = "",
        timestamp: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ResolutionDecision:
        now = timestamp or datetime.now(timezone.utc)
        clean_email = email.strip().lower()
        clean_phone = phone.strip()
        clean_name = name.strip()
        clean_company = company.strip()

        seed = clean_email or clean_phone or f"{clean_name}:{clean_company}"
        candidate_id = make_entity_id("supplier", seed)

        candidates = self.repo.find_suppliers_by_email_or_phone_or_company(
            email=clean_email if clean_email else None,
            phone=clean_phone if clean_phone else None,
            company=clean_company if clean_company else None,
            canonical_name=clean_name if clean_name else None,
        )

        best_match: Supplier | None = None
        best_conf = 0.0
        best_reasons: list[str] = []

        for s in candidates:
            conf = 0.0
            reasons: list[str] = []

            if clean_email and s.email and clean_email == s.email.lower():
                conf = max(conf, 0.98)
                reasons.append(f"exact_email_match:{clean_email}")

            if clean_phone and s.phone and clean_phone == s.phone:
                conf = max(conf, 0.92)
                reasons.append(f"exact_phone_match:{clean_phone}")

            sim = self._name_similarity(clean_name, s.canonical_name)
            if sim >= 0.90:
                is_company_match = (
                    clean_company
                    and clean_company.lower() in (s.company or "").lower()
                )
                conf = max(conf, 0.88 if is_company_match else 0.75)
                reasons.append(f"high_name_similarity:{sim:.2f}")
            elif sim >= 0.70:
                conf = max(conf, 0.65)
                reasons.append(f"medium_name_similarity:{sim:.2f}")

            if conf > best_conf:
                best_conf = conf
                best_match = s
                best_reasons = reasons

        matched_s_id = best_match.id if best_match else "none"
        hash_seed = f"res:{candidate_id}:{matched_s_id}:{now.isoformat()}"
        rec_id = hashlib.sha256(hash_seed.encode()).hexdigest()[:24]

        if best_match and best_conf >= HIGH_CONFIDENCE_THRESHOLD:
            merged_supplier = Supplier(
                id=best_match.id,
                canonical_name=best_match.canonical_name or clean_name,
                email=best_match.email or clean_email,
                phone=best_match.phone or clean_phone,
                company=best_match.company or clean_company,
                last_interaction=now,
                metadata={**best_match.metadata, **(metadata or {})},
                created_at=best_match.created_at,
                updated_at=now,
            )
            self.repo.upsert_supplier(merged_supplier)

            record = ResolutionRecord(
                id=rec_id,
                candidate_entity=candidate_id,
                matched_entity=best_match.id,
                confidence=best_conf,
                matching_reasons=best_reasons + ["auto_merged"],
                source=source,
                timestamp=now,
            )
            self.repo.insert_resolution_record(record)
            return ResolutionDecision(
                entity_id=best_match.id,
                is_merged=True,
                matched_entity_id=best_match.id,
                confidence=best_conf,
                reasons=best_reasons,
                record=record,
            )

        if best_match and best_conf >= MEDIUM_CONFIDENCE_THRESHOLD:
            new_supplier = Supplier(
                id=candidate_id,
                canonical_name=clean_name or clean_email or candidate_id,
                email=clean_email,
                phone=clean_phone,
                company=clean_company,
                last_interaction=now,
                metadata=metadata or {},
                created_at=now,
                updated_at=now,
            )
            self.repo.upsert_supplier(new_supplier)

            record = ResolutionRecord(
                id=rec_id,
                candidate_entity=candidate_id,
                matched_entity=best_match.id,
                confidence=best_conf,
                matching_reasons=best_reasons + ["possible_match_no_merge"],
                source=source,
                timestamp=now,
            )
            self.repo.insert_resolution_record(record)
            return ResolutionDecision(
                entity_id=candidate_id,
                is_merged=False,
                matched_entity_id=best_match.id,
                confidence=best_conf,
                reasons=best_reasons,
                record=record,
            )

        new_supplier = Supplier(
            id=candidate_id,
            canonical_name=clean_name or clean_email or candidate_id,
            email=clean_email,
            phone=clean_phone,
            company=clean_company,
            last_interaction=now,
            metadata=metadata or {},
            created_at=now,
            updated_at=now,
        )
        self.repo.upsert_supplier(new_supplier)

        record = ResolutionRecord(
            id=rec_id,
            candidate_entity=candidate_id,
            matched_entity=candidate_id,
            confidence=1.0 if not best_match else best_conf,
            matching_reasons=["new_distinct_entity"],
            source=source,
            timestamp=now,
        )
        self.repo.insert_resolution_record(record)
        return ResolutionDecision(
            entity_id=candidate_id,
            is_merged=False,
            matched_entity_id=None,
            confidence=1.0 if not best_match else best_conf,
            reasons=["new_distinct_entity"],
            record=record,
        )
