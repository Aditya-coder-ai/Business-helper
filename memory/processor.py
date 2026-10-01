"""Idempotent ingestion processor transforming Layer 1 RawItems into Business Memory."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from actiondesk.schema import RawItem
from actiondesk.store import Store
from memory.database import MemoryDatabase
from memory.extractor.deterministic import DeterministicExtractor
from memory.extractor.llm_client import FakeLLMClient, LLMClient
from memory.models import (
    BusinessEvent,
    Commitment,
    Communication,
    Invoice,
    Order,
    Product,
    Provenance,
    Relationship,
)
from memory.repository import MemoryRepository
from memory.resolution.resolver import EntityResolver, make_entity_id


def make_deterministic_key(
    source: str,
    source_item_id: str,
    record_type: str,
    suffix: str = "",
) -> str:
    """Generate deterministic 24-character hexadecimal key for idempotent inserts."""
    payload = f"{source}:{source_item_id}:{record_type}:{suffix}".strip(":")
    return hashlib.sha256(payload.encode()).hexdigest()[:24]


class MemoryProcessor:
    """Pipelines RawItems from ingestion store into normalized business memory."""

    def __init__(
        self,
        db: MemoryDatabase,
        llm_client: LLMClient | None = None,
    ) -> None:
        self.db = db
        self.repo = MemoryRepository(db)
        self.resolver = EntityResolver(self.repo)
        self.llm_client = llm_client or FakeLLMClient()

    def process_item(self, item: RawItem) -> dict[str, Any]:
        """Process a single RawItem within an atomic database transaction.

        If extraction or validation fails, the transaction is rolled back leaving
        prior database state pristine.
        """
        # 1. Deterministic Extraction
        det = DeterministicExtractor.extract(item.content)

        # 2. Semantic Extraction with LLM (validated via Pydantic)
        context = {
            "source": item.source,
            "source_item_id": item.source_item_id,
            "owner": item.owner,
            "date": item.date.isoformat(),
        }
        semantic = self.llm_client.extract_semantics(item.content, context=context)

        # 3. Atomic Database Persistence
        with self.db.transaction():
            created_entities: list[str] = []
            created_events: list[str] = []
            created_relationships: list[str] = []
            created_commitments: list[str] = []

            # A. Record Communication
            comm_id = make_deterministic_key(item.source, item.source_item_id, "comm")
            comm_type = (
                "email"
                if item.source == "gmail"
                else ("document" if item.source == "drive" else "accounting")
            )
            subject = item.content.splitlines()[0][:100] if item.content else item.source_url
            comm = Communication(
                id=comm_id,
                raw_item_id=item.id,
                type=comm_type,
                sender=item.owner,
                recipients=det.emails,
                subject=subject,
                content=item.content,
                timestamp=item.date,
                metadata={
                    "source_url": item.source_url,
                    "content_hash": item.content_hash,
                },
            )
            self.repo.insert_communication(comm)

            # Record Provenance for Communication
            prov_comm_id = make_deterministic_key(item.source, item.source_item_id, "prov", comm_id)
            self.repo.insert_provenance(
                Provenance(
                    id=prov_comm_id,
                    fact_id=comm_id,
                    fact_type="communication",
                    raw_item_id=item.id,
                    source=item.source,
                    source_item_id=item.source_item_id,
                    source_date=item.date,
                    extraction_method="deterministic",
                    confidence=1.0,
                    created_at=datetime.now(timezone.utc),
                )
            )

            # B. Resolve Entities (Customers, Suppliers, Employees)
            resolved_customer_id: str | None = None
            resolved_supplier_id: str | None = None

            # Primary customer candidate from owner/email or QB
            primary_email = det.emails[0] if det.emails else item.owner
            primary_name = item.owner.split("@")[0] if "@" in item.owner else item.owner

            if primary_email or primary_name:
                cust_decision = self.resolver.resolve_customer(
                    name=primary_name or "Unknown Customer",
                    email=primary_email,
                    phone=det.phones[0] if det.phones else "",
                    company=det.quickbooks_ids.get("customer_id", ""),
                    source=item.source,
                    timestamp=item.date,
                )
                resolved_customer_id = cust_decision.entity_id
                created_entities.append(resolved_customer_id)

                prov_cust_id = make_deterministic_key(
                    item.source, item.source_item_id, "prov", resolved_customer_id
                )
                self.repo.insert_provenance(
                    Provenance(
                        id=prov_cust_id,
                        fact_id=resolved_customer_id,
                        fact_type="customer",
                        raw_item_id=item.id,
                        source=item.source,
                        source_item_id=item.source_item_id,
                        source_date=item.date,
                        extraction_method="resolution",
                        confidence=cust_decision.confidence,
                        created_at=datetime.now(timezone.utc),
                    )
                )

            # Handle additional semantic entities
            for ent in semantic.entities:
                if ent.entity_type == "customer":
                    dec = self.resolver.resolve_customer(
                        name=ent.name,
                        email=ent.email,
                        phone=ent.phone,
                        company=ent.company,
                        source=item.source,
                        timestamp=item.date,
                        metadata=ent.metadata,
                    )
                    created_entities.append(dec.entity_id)
                    if not resolved_customer_id:
                        resolved_customer_id = dec.entity_id
                elif ent.entity_type == "supplier":
                    dec = self.resolver.resolve_supplier(
                        name=ent.name,
                        email=ent.email,
                        phone=ent.phone,
                        company=ent.company,
                        source=item.source,
                        timestamp=item.date,
                        metadata=ent.metadata,
                    )
                    created_entities.append(dec.entity_id)
                    resolved_supplier_id = dec.entity_id
                elif ent.entity_type == "product":
                    p_id = make_entity_id("product", ent.name)
                    self.repo.upsert_product(
                        Product(
                            id=p_id,
                            canonical_name=ent.name,
                            name=ent.name,
                            supplier_id=resolved_supplier_id,
                            metadata=ent.metadata,
                            created_at=item.date,
                            updated_at=item.date,
                        )
                    )
                    created_entities.append(p_id)

            # C. Invoices
            for idx, inv_no in enumerate(det.invoice_numbers or [""]):
                if not inv_no and not det.amounts and "invoice" not in item.content.lower():
                    continue
                inv_key = inv_no or f"inv-{idx}"
                inv_id = make_deterministic_key(
                    item.source, item.source_item_id, "invoice", inv_key
                )
                amt = det.amounts[0].amount if det.amounts else 0.0
                curr = det.amounts[0].currency if det.amounts else "USD"
                due = det.dates[0] if det.dates else None

                inv = Invoice(
                    id=inv_id,
                    canonical_name=f"Invoice {inv_no or inv_id[:8]}",
                    invoice_number=inv_no,
                    customer_id=resolved_customer_id,
                    supplier_id=resolved_supplier_id,
                    issue_date=item.date,
                    due_date=due,
                    amount=amt,
                    currency=curr,
                    status="draft" if item.source != "quickbooks" else "sent",
                    source_raw_item_id=item.id,
                    created_at=item.date,
                    updated_at=item.date,
                )
                self.repo.upsert_invoice(inv)
                created_entities.append(inv_id)

                # Invoice event
                inv_event_id = make_deterministic_key(
                    item.source, item.source_item_id, "event", f"inv-created-{inv_id}"
                )
                self.repo.insert_event(
                    BusinessEvent(
                        id=inv_event_id,
                        type="INVOICE_CREATED",
                        entity_id=inv_id,
                        timestamp=item.date,
                        raw_item_id=item.id,
                        metadata={"amount": amt, "invoice_number": inv_no},
                    )
                )
                created_events.append(inv_event_id)

                # Relationship Customer -> Invoice
                if resolved_customer_id:
                    rel_id = make_deterministic_key(
                        item.source, item.source_item_id, "rel", f"{resolved_customer_id}-{inv_id}"
                    )
                    self.repo.insert_relationship(
                        Relationship(
                            id=rel_id,
                            from_id=resolved_customer_id,
                            to_id=inv_id,
                            rel_type="has",
                            created_at=item.date,
                        )
                    )
                    created_relationships.append(rel_id)

                # Provenance
                prov_inv_id = make_deterministic_key(
                    item.source, item.source_item_id, "prov", inv_id
                )
                self.repo.insert_provenance(
                    Provenance(
                        id=prov_inv_id,
                        fact_id=inv_id,
                        fact_type="invoice",
                        raw_item_id=item.id,
                        source=item.source,
                        source_item_id=item.source_item_id,
                        source_date=item.date,
                        extraction_method="deterministic",
                        confidence=0.95,
                        created_at=datetime.now(timezone.utc),
                    )
                )

            # D. Orders
            if "order" in item.content.lower() or item.source == "quickbooks":
                order_id = make_deterministic_key(item.source, item.source_item_id, "order")
                order_amt = det.amounts[0].amount if det.amounts else 0.0
                order_curr = det.amounts[0].currency if det.amounts else "USD"
                order = Order(
                    id=order_id,
                    canonical_name=f"Order {order_id[:8]}",
                    customer_id=resolved_customer_id,
                    order_date=item.date,
                    status="completed" if item.source == "quickbooks" else "pending",
                    total_amount=order_amt,
                    currency=order_curr,
                    source_raw_item_id=item.id,
                    created_at=item.date,
                    updated_at=item.date,
                )
                self.repo.upsert_order(order)
                created_entities.append(order_id)

                order_event_id = make_deterministic_key(
                    item.source, item.source_item_id, "event", f"order-created-{order_id}"
                )
                self.repo.insert_event(
                    BusinessEvent(
                        id=order_event_id,
                        type="ORDER_CREATED",
                        entity_id=order_id,
                        timestamp=item.date,
                        raw_item_id=item.id,
                        metadata={"total_amount": order_amt},
                    )
                )
                created_events.append(order_event_id)

                if resolved_customer_id:
                    rel_ord_id = make_deterministic_key(
                        item.source,
                        item.source_item_id,
                        "rel",
                        f"{resolved_customer_id}-{order_id}",
                    )
                    self.repo.insert_relationship(
                        Relationship(
                            id=rel_ord_id,
                            from_id=resolved_customer_id,
                            to_id=order_id,
                            rel_type="places",
                            created_at=item.date,
                        )
                    )
                    created_relationships.append(rel_ord_id)

            # E. Communication Interaction Event
            if resolved_customer_id:
                event_type = (
                    "EMAIL_RECEIVED"
                    if item.source == "gmail"
                    else "CUSTOMER_INTERACTION"
                )
                ev_id = make_deterministic_key(
                    item.source, item.source_item_id, "event", f"{event_type}-{comm_id}"
                )
                self.repo.insert_event(
                    BusinessEvent(
                        id=ev_id,
                        type=event_type,
                        entity_id=resolved_customer_id,
                        timestamp=item.date,
                        raw_item_id=item.id,
                        metadata={"subject": subject},
                    )
                )
                created_events.append(ev_id)

            # F. Commitments
            for idx, c_cand in enumerate(semantic.commitments):
                target_entity = resolved_customer_id or make_entity_id(
                    "customer", c_cand.related_entity_name
                )
                commit_id = make_deterministic_key(
                    item.source, item.source_item_id, "commit", f"{idx}:{c_cand.description[:20]}"
                )
                self.repo.upsert_commitment(
                    Commitment(
                        id=commit_id,
                        description=c_cand.description,
                        owner=c_cand.owner or item.owner,
                        related_entity=target_entity,
                        due_date=c_cand.due_date,
                        status="OPEN",
                        confidence=c_cand.confidence,
                        source_raw_item_id=item.id,
                        created_at=item.date,
                        updated_at=item.date,
                    )
                )
                created_commitments.append(commit_id)

            # G. Explicit Semantic Relationships
            for rel_cand in semantic.relationships:
                from_id = make_entity_id("customer", rel_cand.from_name)
                to_id = make_entity_id("customer", rel_cand.to_name)

                # Ensure both endpoints exist as entities (FK safety)
                for eid, ename in [(from_id, rel_cand.from_name), (to_id, rel_cand.to_name)]:
                    if not self.repo.get_entity_raw(eid):
                        self.repo.upsert_entity(
                            id_=eid,
                            entity_type="customer",
                            canonical_name=ename,
                            created_at=item.date,
                            updated_at=item.date,
                        )

                rel_id = make_deterministic_key(
                    item.source,
                    item.source_item_id,
                    "rel",
                    f"{from_id}-{to_id}-{rel_cand.rel_type}",
                )
                self.repo.insert_relationship(
                    Relationship(
                        id=rel_id,
                        from_id=from_id,
                        to_id=to_id,
                        rel_type=rel_cand.rel_type,
                        created_at=item.date,
                    )
                )
                created_relationships.append(rel_id)

            return {
                "raw_item_id": item.id,
                "entities": created_entities,
                "events": created_events,
                "relationships": created_relationships,
                "commitments": created_commitments,
            }

    def process_all_from_store(
        self,
        store: Store,
        source: str | None = None,
    ) -> int:
        """Iterate all raw items in the Layer 1 store and process idempotently."""
        items_data = store.all_items(source=source)
        count = 0
        for row in items_data:
            from dateutil.parser import parse as dtparse

            item = RawItem(
                id=row["id"],
                source=row["source"],
                source_item_id=row["source_item_id"],
                source_url=row.get("source_url", ""),
                date=dtparse(row["date"]),
                owner=row.get("owner", ""),
                content=row.get("content", ""),
                content_hash=row["content_hash"],
                fetched_at=dtparse(row["fetched_at"]),
            )
            self.process_item(item)
            count += 1
        return count
