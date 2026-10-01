"""Tests for Layer 2 — Entity-Centric Business Memory.

Covers: extraction, entity resolution, relationships, timeline,
provenance, idempotency, LLM failure rollback, and FastAPI endpoints.
"""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import pytest
from fastapi.testclient import TestClient

from actiondesk.schema import RawItem, content_hash, make_id
from memory.database import MemoryDatabase
from memory.extractor.deterministic import DeterministicExtractor
from memory.extractor.llm_client import (
    FakeLLMClient,
    LLMCommitmentCandidate,
    LLMEntityCandidate,
    LLMExtractionResult,
    LLMRelationshipCandidate,
)
from memory.processor import MemoryProcessor
from memory.repository import MemoryRepository
from memory.resolution.resolver import EntityResolver
from memory.service import MemoryService


# ------------------------------------------------------------------ Fixtures
@pytest.fixture()
def mem_db(tmp_path: Path) -> MemoryDatabase:
    return MemoryDatabase(tmp_path / "test_memory.db")


@pytest.fixture()
def repo(mem_db: MemoryDatabase) -> MemoryRepository:
    return MemoryRepository(mem_db)


@pytest.fixture()
def resolver(repo: MemoryRepository) -> EntityResolver:
    return EntityResolver(repo)


@pytest.fixture()
def service(mem_db: MemoryDatabase) -> MemoryService:
    return MemoryService(mem_db)


@pytest.fixture()
def fake_llm() -> FakeLLMClient:
    return FakeLLMClient()


@pytest.fixture()
def processor(mem_db: MemoryDatabase, fake_llm: FakeLLMClient) -> MemoryProcessor:
    return MemoryProcessor(mem_db, llm_client=fake_llm)


def _raw_item(
    source: Literal["gmail", "drive", "quickbooks"] = "gmail",
    sid: str = "msg-001",
    content: str = "Hello from alice@example.com about Invoice INV-2024-001 for $1,500.00",
    owner: str = "alice@example.com",
) -> RawItem:
    return RawItem(
        id=make_id(source, sid),
        source=source,
        source_item_id=sid,
        source_url=f"https://example.com/{source}/{sid}",
        date=datetime(2024, 3, 15, 10, 30, tzinfo=timezone.utc),
        owner=owner,
        content=content,
        content_hash=content_hash(content),
    )


# ================================================================== EXTRACTION TESTS
class TestDeterministicExtraction:
    def test_extract_emails(self) -> None:
        text = "Contact alice@example.com or bob@corp.io for details."
        result = DeterministicExtractor.extract(text)
        assert "alice@example.com" in result.emails
        assert "bob@corp.io" in result.emails
        assert len(result.emails) == 2

    def test_extract_phones(self) -> None:
        text = "Call us at +1-555-123-4567 or (800) 555-0199."
        result = DeterministicExtractor.extract(text)
        assert len(result.phones) >= 1

    def test_extract_invoice_numbers(self) -> None:
        text = "Please pay Invoice INV-2024-001 and BILL-9923."
        result = DeterministicExtractor.extract(text)
        assert "INV-2024-001" in result.invoice_numbers
        assert "BILL-9923" in result.invoice_numbers

    def test_extract_amounts(self) -> None:
        text = "Total: $1,500.00 and €250.50 and 300.00 USD."
        result = DeterministicExtractor.extract(text)
        amounts = {(a.amount, a.currency) for a in result.amounts}
        assert (1500.00, "USD") in amounts
        assert (250.50, "EUR") in amounts
        assert (300.00, "USD") in amounts

    def test_extract_dates(self) -> None:
        text = "Due by 2024-03-31 and January 15, 2024."
        result = DeterministicExtractor.extract(text)
        assert len(result.dates) >= 1

    def test_extract_quickbooks_ids(self) -> None:
        text = "QB Customer ID: CUST-123 and TxnId=TXN-456."
        result = DeterministicExtractor.extract(text)
        assert len(result.quickbooks_ids) >= 1

    def test_rawitem_to_customer_extraction(self) -> None:
        """RawItem content with email and name produces a valid customer extraction."""
        item = _raw_item(
            content="From: Alice Johnson <alice@example.com> Phone: +1-555-123-4567"
        )
        result = DeterministicExtractor.extract(item.content)
        assert "alice@example.com" in result.emails
        assert len(result.phones) >= 1

    def test_rawitem_to_invoice_extraction(self) -> None:
        """RawItem with invoice data produces valid invoice extraction."""
        item = _raw_item(
            source="quickbooks",
            sid="qb-inv-001",
            content="Invoice INV-2024-042 Amount: $3,200.00 Due: 2024-04-30",
        )
        result = DeterministicExtractor.extract(item.content)
        assert "INV-2024-042" in result.invoice_numbers
        assert any(a.amount == 3200.00 for a in result.amounts)

    def test_rawitem_to_supplier_extraction(self) -> None:
        """RawItem from supplier with email yields deterministic extraction."""
        item = _raw_item(
            content="Supplier: Acme Corp supplier@acme.com Phone: 800-555-0100"
        )
        result = DeterministicExtractor.extract(item.content)
        assert "supplier@acme.com" in result.emails


# ================================================================== ENTITY RESOLUTION TESTS
class TestEntityResolution:
    def test_same_email_same_entity(
        self, resolver: EntityResolver, repo: MemoryRepository
    ) -> None:
        """Two items with the same email resolve to the same customer entity."""
        d1 = resolver.resolve_customer(
            name="Alice", email="alice@example.com", source="gmail"
        )
        d2 = resolver.resolve_customer(
            name="Alice Johnson", email="alice@example.com", source="quickbooks"
        )
        assert d1.entity_id == d2.entity_id
        assert d2.is_merged is True

    def test_name_variants_candidate(
        self, resolver: EntityResolver
    ) -> None:
        """Similar names without matching email stay separate (medium confidence)."""
        d1 = resolver.resolve_customer(
            name="Robert Smith", email="robert@example.com", source="gmail"
        )
        d2 = resolver.resolve_customer(
            name="Bob Smith", email="bob@different.com", source="gmail"
        )
        # Different emails -> should not auto-merge
        assert d1.entity_id != d2.entity_id

    def test_different_entities_stay_separate(
        self, resolver: EntityResolver
    ) -> None:
        """Completely different contacts stay as separate entities."""
        d1 = resolver.resolve_customer(
            name="Alice Johnson", email="alice@example.com", source="gmail"
        )
        d2 = resolver.resolve_customer(
            name="Charlie Brown", email="charlie@other.com", source="drive"
        )
        assert d1.entity_id != d2.entity_id

    def test_resolution_record_created(
        self, resolver: EntityResolver
    ) -> None:
        """Every resolution decision writes a ResolutionRecord."""
        d = resolver.resolve_customer(
            name="TestUser", email="test@test.com", source="gmail"
        )
        assert d.record is not None
        assert d.record.confidence > 0


# ================================================================== RELATIONSHIP TESTS
class TestRelationships:
    def test_customer_order_relationship(
        self, processor: MemoryProcessor
    ) -> None:
        """Processing an order-containing item links customer to order."""
        item = _raw_item(
            source="quickbooks",
            sid="qb-order-001",
            content="Order confirmation for alice@example.com total $500.00",
        )
        result = processor.process_item(item)
        assert len(result["relationships"]) >= 1

    def test_customer_invoice_relationship(
        self, processor: MemoryProcessor
    ) -> None:
        """Processing invoice content links customer to invoice."""
        item = _raw_item(
            content="Invoice INV-2024-055 for alice@example.com amount $1,200.00"
        )
        result = processor.process_item(item)
        assert len(result["entities"]) >= 1
        assert len(result["relationships"]) >= 1


# ================================================================== TIMELINE TESTS
class TestTimeline:
    def test_timeline_ordering(
        self, processor: MemoryProcessor, service: MemoryService
    ) -> None:
        """Timeline entries are ordered chronologically (newest first)."""
        item = _raw_item(
            content="Invoice INV-001 for $100.00 from alice@example.com"
        )
        result = processor.process_item(item)
        entity_id = result["entities"][0]
        timeline = service.get_entity_timeline(entity_id)
        if len(timeline) >= 2:
            # Check descending order
            timestamps = [
                t["timestamp"] for t in timeline if t.get("timestamp")
            ]
            assert timestamps == sorted(timestamps, reverse=True)


# ================================================================== PROVENANCE TESTS
class TestProvenance:
    def test_provenance_on_every_fact(
        self, processor: MemoryProcessor, service: MemoryService
    ) -> None:
        """Every created entity/invoice has provenance records."""
        item = _raw_item(
            content="Invoice INV-PROV-001 for $500.00 from test@prov.com"
        )
        result = processor.process_item(item)
        for entity_id in result["entities"]:
            evidence = service.get_source_evidence(entity_id)
            assert len(evidence) >= 1, f"No provenance for {entity_id}"


# ================================================================== IDEMPOTENCY TESTS
class TestIdempotency:
    def test_process_twice_no_duplicates(
        self, processor: MemoryProcessor, mem_db: MemoryDatabase
    ) -> None:
        """Processing the same RawItem twice creates no duplicate entities/events."""
        item = _raw_item(
            content="Invoice INV-IDEM-001 for $750.00 from idem@test.com"
        )
        r1 = processor.process_item(item)
        r2 = processor.process_item(item)

        # Same entity IDs
        assert set(r1["entities"]) == set(r2["entities"])

        # Count entities in DB
        cur = mem_db.execute("SELECT COUNT(*) FROM entities")
        count = cur.fetchone()[0]
        # Should not have doubled
        assert count == len(set(r1["entities"]))


# ================================================================== LLM FAILURE TESTS
class TestLLMFailure:
    def test_llm_failure_leaves_memory_intact(
        self, mem_db: MemoryDatabase
    ) -> None:
        """If the LLM client fails, the transaction rolls back and memory is unchanged."""
        failing_llm = FakeLLMClient(should_fail=True)
        proc = MemoryProcessor(mem_db, llm_client=failing_llm)

        # Count entities before
        before_count = mem_db.execute("SELECT COUNT(*) FROM entities").fetchone()[0]

        item = _raw_item(
            content="Invoice INV-FAIL-001 for $999.00 from fail@test.com"
        )
        with pytest.raises(RuntimeError, match="Simulated LLM"):
            proc.process_item(item)

        # Count entities after — should be unchanged
        after_count = mem_db.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        assert after_count == before_count


# ================================================================== LLM SEMANTIC TESTS
class TestLLMSemantics:
    def test_llm_entities_persisted(
        self, mem_db: MemoryDatabase
    ) -> None:
        """Validated LLM entity candidates are persisted via resolution."""
        llm = FakeLLMClient(
            default_result=LLMExtractionResult(
                entities=[
                    LLMEntityCandidate(
                        name="Acme Supplies",
                        entity_type="supplier",
                        email="info@acme.com",
                        company="Acme Corp",
                    )
                ],
                commitments=[
                    LLMCommitmentCandidate(
                        description="Ship 100 units by Friday",
                        owner="bob@acme.com",
                        related_entity_name="Acme Supplies",
                        confidence=0.85,
                    )
                ],
                relationships=[
                    LLMRelationshipCandidate(
                        from_name="Acme Supplies",
                        to_name="alice",
                        rel_type="supplies",
                    )
                ],
            )
        )
        proc = MemoryProcessor(mem_db, llm_client=llm)
        item = _raw_item(
            content="Acme Supplies will ship 100 units by Friday info@acme.com"
        )
        result = proc.process_item(item)
        assert len(result["entities"]) >= 2  # customer + supplier
        assert len(result["commitments"]) >= 1
        assert len(result["relationships"]) >= 1


# ================================================================== FASTAPI TESTS
class TestFastAPI:
    @pytest.fixture()
    def client(
        self, mem_db: MemoryDatabase, processor: MemoryProcessor
    ) -> Generator[TestClient, None, None]:
        """Create TestClient with pre-populated memory."""
        item = _raw_item(
            content="Invoice INV-API-001 for $2,000.00 from api-user@test.com"
        )
        processor.process_item(item)

        from memory.api import app

        svc = MemoryService(mem_db)

        def override_service() -> MemoryService:
            return svc

        # Monkey-patch the module-level get_service
        import memory.api

        original = memory.api.get_service
        memory.api.get_service = override_service
        tc = TestClient(app)
        yield tc
        memory.api.get_service = original

    def test_list_entities(self, client: TestClient) -> None:
        resp = client.get("/api/entities")
        assert resp.status_code == 200
        data = resp.json()
        assert "entities" in data
        assert data["count"] >= 1

    def test_get_entity_not_found(self, client: TestClient) -> None:
        resp = client.get("/api/entities/nonexistent-id-12345678")
        assert resp.status_code == 404

    def test_get_timeline(self, client: TestClient) -> None:
        # Get an entity first
        ents = client.get("/api/entities").json()["entities"]
        if ents:
            eid = ents[0]["id"]
            resp = client.get(f"/api/entities/{eid}/timeline")
            assert resp.status_code == 200
            assert "timeline" in resp.json()

    def test_get_relationships(self, client: TestClient) -> None:
        ents = client.get("/api/entities").json()["entities"]
        if ents:
            eid = ents[0]["id"]
            resp = client.get(f"/api/entities/{eid}/relationships")
            assert resp.status_code == 200
            assert "relationships" in resp.json()

    def test_search_entities(self, client: TestClient) -> None:
        resp = client.get("/api/entities", params={"q": "api-user"})
        assert resp.status_code == 200

    def test_recent_events(self, client: TestClient) -> None:
        resp = client.get("/api/events/recent")
        assert resp.status_code == 200
        assert "events" in resp.json()

    def test_open_commitments(self, client: TestClient) -> None:
        resp = client.get("/api/commitments/open")
        assert resp.status_code == 200

    def test_overdue_invoices(self, client: TestClient) -> None:
        resp = client.get("/api/invoices/overdue")
        assert resp.status_code == 200

    def test_provenance(self, client: TestClient) -> None:
        ents = client.get("/api/entities").json()["entities"]
        if ents:
            eid = ents[0]["id"]
            resp = client.get(f"/api/provenance/{eid}")
            assert resp.status_code == 200
            assert "provenance" in resp.json()
