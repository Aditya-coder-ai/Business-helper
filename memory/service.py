"""Business Memory Service API — stable interface hiding DB details from Layer 3+."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from memory.database import MemoryDatabase
from memory.models import (
    BusinessEvent,
    Commitment,
    Customer,
    Employee,
    Invoice,
    Order,
    Product,
    Provenance,
    Supplier,
)
from memory.repository import MemoryRepository


class MemoryService:
    """High-level read API over the normalized business memory store."""

    def __init__(self, db: MemoryDatabase) -> None:
        self.db = db
        self.repo = MemoryRepository(db)

    # ------------------------------------------------------------------ Entity Getters
    def get_customer(self, customer_id: str) -> Customer | None:
        return self.repo.get_customer(customer_id)

    def get_supplier(self, supplier_id: str) -> Supplier | None:
        return self.repo.get_supplier(supplier_id)

    def get_product(self, product_id: str) -> Product | None:
        return self.repo.get_product(product_id)

    def get_order(self, order_id: str) -> Order | None:
        return self.repo.get_order(order_id)

    def get_invoice(self, invoice_id: str) -> Invoice | None:
        return self.repo.get_invoice(invoice_id)

    def get_employee(self, employee_id: str) -> Employee | None:
        return self.repo.get_employee(employee_id)

    # ------------------------------------------------------------------ Timeline
    def get_entity_timeline(
        self, entity_id: str
    ) -> list[dict[str, Any]]:
        """Chronological timeline of events, orders, invoices, communications, commitments."""
        timeline: list[dict[str, Any]] = []

        # Events
        for ev in self.repo.get_events_for_entity(entity_id):
            timeline.append({
                "kind": "event",
                "id": ev.id,
                "type": ev.type,
                "timestamp": ev.timestamp.isoformat(),
                "raw_item_id": ev.raw_item_id,
                "metadata": ev.metadata,
            })

        # Communications
        for comm in self.repo.get_communications_for_entity(entity_id):
            timeline.append({
                "kind": "communication",
                "id": comm.id,
                "type": comm.type,
                "subject": comm.subject,
                "sender": comm.sender,
                "timestamp": comm.timestamp.isoformat(),
                "raw_item_id": comm.raw_item_id,
            })

        # Commitments
        for c in self.repo.get_commitments_for_entity(entity_id):
            timeline.append({
                "kind": "commitment",
                "id": c.id,
                "description": c.description,
                "status": c.status,
                "due_date": c.due_date.isoformat() if c.due_date else None,
                "timestamp": c.created_at.isoformat(),
                "confidence": c.confidence,
            })

        # Orders where customer_id = entity_id
        cur = self.db.execute(
            "SELECT id FROM orders WHERE customer_id = ?", (entity_id,)
        )
        for row in cur.fetchall():
            order = self.repo.get_order(row["id"])
            if order:
                timeline.append({
                    "kind": "order",
                    "id": order.id,
                    "status": order.status,
                    "total_amount": order.total_amount,
                    "currency": order.currency,
                    "timestamp": order.order_date.isoformat(),
                })

        # Invoices where customer_id = entity_id
        cur = self.db.execute(
            "SELECT id FROM invoices WHERE customer_id = ? OR supplier_id = ?",
            (entity_id, entity_id),
        )
        for row in cur.fetchall():
            inv = self.repo.get_invoice(row["id"])
            if inv:
                timeline.append({
                    "kind": "invoice",
                    "id": inv.id,
                    "invoice_number": inv.invoice_number,
                    "amount": inv.amount,
                    "currency": inv.currency,
                    "status": inv.status,
                    "timestamp": inv.issue_date.isoformat(),
                })

        # Sort chronologically (newest first)
        timeline.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return timeline

    # ------------------------------------------------------------------ Relationships
    def get_entity_relationships(
        self, entity_id: str
    ) -> list[dict[str, Any]]:
        rels = self.repo.get_relationships_for_entity(entity_id)
        result: list[dict[str, Any]] = []
        for r in rels:
            other_id = r.to_id if r.from_id == entity_id else r.from_id
            other_entity = self.repo.get_entity_raw(other_id)
            result.append({
                "id": r.id,
                "from_id": r.from_id,
                "to_id": r.to_id,
                "rel_type": r.rel_type,
                "other_entity_id": other_id,
                "other_entity_name": (
                    other_entity["canonical_name"] if other_entity else "Unknown"
                ),
                "other_entity_type": (
                    other_entity["entity_type"] if other_entity else "unknown"
                ),
                "created_at": r.created_at.isoformat(),
            })
        return result

    # ------------------------------------------------------------------ Commitments
    def get_open_commitments(self) -> list[Commitment]:
        cur = self.db.execute(
            "SELECT * FROM commitments WHERE status = 'OPEN' ORDER BY due_date ASC"
        )
        results: list[Commitment] = []
        for r in cur.fetchall():
            from memory.repository import _iso_to_dt

            results.append(
                Commitment(
                    id=r["id"],
                    description=r["description"],
                    owner=r["owner"],
                    related_entity=r["related_entity"],
                    due_date=_iso_to_dt(r["due_date"]),
                    status=r["status"],
                    confidence=float(r["confidence"]),
                    source_event_id=r["source_event_id"],
                    source_raw_item_id=r["source_raw_item_id"],
                    created_at=_iso_to_dt(r["created_at"]) or datetime.now(timezone.utc),
                    updated_at=_iso_to_dt(r["updated_at"]) or datetime.now(timezone.utc),
                )
            )
        return results

    # ------------------------------------------------------------------ Overdue Invoices
    def get_overdue_invoices(self) -> list[Invoice]:
        now_iso = datetime.now(timezone.utc).isoformat()
        cur = self.db.execute(
            """
            SELECT i.id FROM invoices i
            WHERE i.due_date IS NOT NULL
              AND i.due_date < ?
              AND i.status NOT IN ('paid', 'cancelled')
            ORDER BY i.due_date ASC
            """,
            (now_iso,),
        )
        results: list[Invoice] = []
        for row in cur.fetchall():
            inv = self.repo.get_invoice(row["id"])
            if inv:
                results.append(inv)
        return results

    # ------------------------------------------------------------------ Recent Events
    def get_recent_events(self, limit: int = 50) -> list[BusinessEvent]:
        cur = self.db.execute(
            "SELECT * FROM business_events ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )
        from memory.repository import _iso_to_dt

        return [
            BusinessEvent(
                id=r["id"],
                type=r["type"],
                entity_id=r["entity_id"],
                timestamp=_iso_to_dt(r["timestamp"]) or datetime.now(timezone.utc),
                raw_item_id=r["raw_item_id"],
                metadata=json.loads(r["metadata"] or "{}"),
            )
            for r in cur.fetchall()
        ]

    # ------------------------------------------------------------------ Search
    def search_business_memory(
        self,
        query: str,
        entity_type: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Structured search across entities. Optional type filter."""
        clauses = ["LOWER(canonical_name) LIKE ?"]
        params: list[Any] = [f"%{query.lower()}%"]

        if entity_type:
            clauses.append("entity_type = ?")
            params.append(entity_type)

        sql = f"""
            SELECT id, entity_type, canonical_name, status, metadata,
                   created_at, updated_at
            FROM entities
            WHERE {" AND ".join(clauses)}
            ORDER BY updated_at DESC
            LIMIT ?
        """
        params.append(limit)
        cur = self.db.execute(sql, tuple(params))
        return [dict(row) for row in cur.fetchall()]

    # ------------------------------------------------------------------ Source Evidence
    def get_source_evidence(self, fact_id: str) -> list[Provenance]:
        """Return provenance chain for a fact — answers 'Why does the system believe this?'"""
        return self.repo.get_provenance_for_fact(fact_id)

    # ------------------------------------------------------------------ Entity List
    def list_entities(
        self,
        entity_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        if entity_type:
            cur = self.db.execute(
                """
                SELECT id, entity_type, canonical_name, status, metadata,
                       created_at, updated_at
                FROM entities
                WHERE entity_type = ?
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
                """,
                (entity_type, limit, offset),
            )
        else:
            cur = self.db.execute(
                """
                SELECT id, entity_type, canonical_name, status, metadata,
                       created_at, updated_at
                FROM entities
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )
        return [dict(row) for row in cur.fetchall()]
