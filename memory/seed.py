"""Seed script to populate memory.db with realistic sample business data."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from actiondesk.schema import RawItem, content_hash, make_id
from memory.database import MemoryDatabase
from memory.extractor.llm_client import (
    FakeLLMClient,
    LLMCommitmentCandidate,
    LLMEntityCandidate,
    LLMExtractionResult,
    LLMRelationshipCandidate,
)
from memory.processor import MemoryProcessor


def seed_database(db_path: Path | str = "memory.db") -> None:
    """Populate database with rich sample data for UI demo and testing."""
    db = MemoryDatabase(Path(db_path))

    # Configure FakeLLMClient with rich semantic mock responses
    client = FakeLLMClient()

    sample_items = [
        (
            RawItem(
                id=make_id("gmail", "msg_acme_001"),
                source="gmail",
                source_item_id="msg_acme_001",
                source_url="https://mail.google.com/mail/u/0/#inbox/msg_acme_001",
                date=datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc),
                owner="alice@acme.com",
                content=(
                    "Hi Team,\n\nConfirming Invoice INV-2024-001 for $15,400.00 from Acme Corp. "
                    "Contact: Alice Smith at alice@acme.com or phone (555) 234-5678. "
                    "We promise to deliver shipment batch 3 by next Friday. "
                    "Thanks, Alice"
                ),
                content_hash=content_hash(
                    "Hi Team, confirming Invoice INV-2024-001 for $15,400.00 from Acme Corp..."
                ),
                fetched_at=datetime.now(timezone.utc),
            ),
            LLMExtractionResult(
                entities=[
                    LLMEntityCandidate(
                        name="Acme Corp",
                        entity_type="customer",
                        email="alice@acme.com",
                        phone="(555) 234-5678",
                        metadata={"industry": "Manufacturing", "tier": "Enterprise"},
                    )
                ],
                commitments=[
                    LLMCommitmentCandidate(
                        description="Deliver shipment batch 3 by Friday",
                        related_entity_name="Acme Corp",
                        due_date=datetime(2024, 1, 26, 17, 0, tzinfo=timezone.utc),
                        confidence=0.95,
                    )
                ],
            ),
        ),
        (
            RawItem(
                id=make_id("quickbooks", "qb_inv_002"),
                source="quickbooks",
                source_item_id="qb_inv_002",
                source_url="https://app.qbo.intuit.com/app/invoice?txnId=qb_inv_002",
                date=datetime(2024, 2, 1, 14, 0, tzinfo=timezone.utc),
                owner="billing@waynecorp.com",
                content=(
                    "QuickBooks Invoice: INV-2024-002 amount $4,500.00. "
                    "Customer: Wayne Enterprises. Contact: bruce@waynecorp.com. "
                    "Payment overdue as of February 15, 2024. Status: OVERDUE."
                ),
                content_hash=content_hash("QuickBooks Invoice: INV-2024-002 amount $4,500.00..."),
                fetched_at=datetime.now(timezone.utc),
            ),
            LLMExtractionResult(
                entities=[
                    LLMEntityCandidate(
                        name="Wayne Enterprises",
                        entity_type="customer",
                        email="bruce@waynecorp.com",
                        metadata={
                            "industry": "Technology / Defense",
                            "account_manager": "Lucius Fox",
                        },
                    )
                ],
                commitments=[
                    LLMCommitmentCandidate(
                        description="Follow up on overdue payment for INV-2024-002",
                        related_entity_name="Wayne Enterprises",
                        due_date=datetime(2024, 2, 20, 12, 0, tzinfo=timezone.utc),
                        confidence=0.90,
                    )
                ],
            ),
        ),
        (
            RawItem(
                id=make_id("drive", "doc_globaltech_contract"),
                source="drive",
                source_item_id="doc_globaltech_contract",
                source_url="https://drive.google.com/file/d/doc_globaltech_contract/view",
                date=datetime(2024, 2, 10, 9, 15, tzinfo=timezone.utc),
                owner="procurement@internal.com",
                content=(
                    "Vendor Master Agreement with Global Tech Supplies. "
                    "Supplier contact: orders@globaltech.io, phone (555) 876-5432. "
                    "Terms: Net 30 for all hardware component orders. "
                    "Global Tech Supplies agrees to provide quarterly SLA audit reports."
                ),
                content_hash=content_hash("Vendor Master Agreement with Global Tech Supplies..."),
                fetched_at=datetime.now(timezone.utc),
            ),
            LLMExtractionResult(
                entities=[
                    LLMEntityCandidate(
                        name="Global Tech Supplies",
                        entity_type="supplier",
                        email="orders@globaltech.io",
                        phone="(555) 876-5432",
                        metadata={"category": "Hardware & Electronics", "rating": "Preferred"},
                    )
                ],
                commitments=[
                    LLMCommitmentCandidate(
                        description="Provide quarterly SLA audit reports",
                        related_entity_name="Global Tech Supplies",
                        due_date=datetime(2024, 3, 31, 23, 59, 59, tzinfo=timezone.utc),
                        confidence=0.92,
                    )
                ],
            ),
        ),
        (
            RawItem(
                id=make_id("gmail", "msg_apex_dispatch"),
                source="gmail",
                source_item_id="msg_apex_dispatch",
                source_url="https://mail.google.com/mail/u/0/#inbox/msg_apex_dispatch",
                date=datetime(2024, 2, 18, 16, 45, tzinfo=timezone.utc),
                owner="dispatch@apexlogistics.com",
                content=(
                    "Apex Logistics Dispatch Update.\n"
                    "Carrier partner for Acme Corp shipments. "
                    "Contact: dispatch@apexlogistics.com, (555) 432-1098. "
                    "Invoice INV-2024-003 for $8,250.00 generated for freight services."
                ),
                content_hash=content_hash("Apex Logistics Dispatch Update..."),
                fetched_at=datetime.now(timezone.utc),
            ),
            LLMExtractionResult(
                entities=[
                    LLMEntityCandidate(
                        name="Apex Logistics",
                        entity_type="supplier",
                        email="dispatch@apexlogistics.com",
                        phone="(555) 432-1098",
                        metadata={"service": "Freight & Freight Forwarding"},
                    )
                ],
                relationships=[
                    LLMRelationshipCandidate(
                        from_name="Apex Logistics",
                        to_name="Acme Corp",
                        rel_type="supplies",
                    )
                ],
            ),
        ),
    ]

    for item, mock_res in sample_items:
        client = FakeLLMClient(default_result=mock_res)
        processor = MemoryProcessor(db, llm_client=client)
        processor.process_item(item)

    print(f"Database seeded successfully at {db_path}!")


if __name__ == "__main__":
    seed_database()
