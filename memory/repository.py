"""Repository layer for normalized relational operations on Business Memory."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from memory.database import MemoryDatabase
from memory.models import (
    BusinessEvent,
    Commitment,
    Communication,
    Customer,
    DerivedFact,
    Employee,
    Invoice,
    Order,
    Product,
    Provenance,
    Relationship,
    ResolutionRecord,
    Supplier,
)


def _dt_to_iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt is not None else None


def _iso_to_dt(val: str | None) -> datetime | None:
    if not val:
        return None
    from dateutil.parser import parse as dtparse

    return dtparse(val)


class MemoryRepository:
    """Encapsulates data access and relational queries for all memory tables."""

    def __init__(self, db: MemoryDatabase) -> None:
        self.db = db

    # ------------------------------------------------------------------ Entities (Base)
    def upsert_entity(
        self,
        id_: str,
        entity_type: str,
        canonical_name: str,
        status: str = "active",
        metadata: dict[str, Any] | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        meta_json = json.dumps(metadata or {})
        c_at = _dt_to_iso(created_at)
        u_at = _dt_to_iso(updated_at)
        self.db.execute(
            """
            INSERT INTO entities (id, entity_type, canonical_name, status,
                                  metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, COALESCE(?, datetime('now')), COALESCE(?, datetime('now')))
            ON CONFLICT(id) DO UPDATE SET
                canonical_name = excluded.canonical_name,
                status         = excluded.status,
                metadata       = excluded.metadata,
                updated_at     = excluded.updated_at
            """,
            (id_, entity_type, canonical_name, status, meta_json, c_at, u_at),
        )

    def get_entity_raw(self, id_: str) -> dict[str, Any] | None:
        cur = self.db.execute("SELECT * FROM entities WHERE id = ?", (id_,))
        row = cur.fetchone()
        return dict(row) if row else None

    # ------------------------------------------------------------------ Customer
    def upsert_customer(self, customer: Customer) -> None:
        self.upsert_entity(
            id_=customer.id,
            entity_type="customer",
            canonical_name=customer.canonical_name,
            status=customer.status,
            metadata=customer.metadata,
            created_at=customer.created_at,
            updated_at=customer.updated_at,
        )
        self.db.execute(
            """
            INSERT INTO customers (id, email, phone, company, first_seen, last_interaction)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                email            = excluded.email,
                phone            = excluded.phone,
                company          = excluded.company,
                first_seen       = COALESCE(customers.first_seen, excluded.first_seen),
                last_interaction = excluded.last_interaction
            """,
            (
                customer.id,
                customer.email,
                customer.phone,
                customer.company,
                _dt_to_iso(customer.first_seen),
                _dt_to_iso(customer.last_interaction),
            ),
        )

    def get_customer(self, customer_id: str) -> Customer | None:
        cur = self.db.execute(
            """
            SELECT e.id, e.entity_type, e.canonical_name, e.status, e.metadata,
                   e.created_at, e.updated_at,
                   c.email, c.phone, c.company, c.first_seen, c.last_interaction
            FROM entities e
            JOIN customers c ON e.id = c.id
            WHERE e.id = ?
            """,
            (customer_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return Customer(
            id=row["id"],
            canonical_name=row["canonical_name"],
            status=row["status"],
            metadata=json.loads(row["metadata"]),
            created_at=_iso_to_dt(row["created_at"]) or datetime.now(),
            updated_at=_iso_to_dt(row["updated_at"]) or datetime.now(),
            email=row["email"],
            phone=row["phone"],
            company=row["company"],
            first_seen=_iso_to_dt(row["first_seen"]),
            last_interaction=_iso_to_dt(row["last_interaction"]),
        )

    # ------------------------------------------------------------------ Supplier
    def upsert_supplier(self, supplier: Supplier) -> None:
        self.upsert_entity(
            id_=supplier.id,
            entity_type="supplier",
            canonical_name=supplier.canonical_name,
            status=supplier.status,
            metadata=supplier.metadata,
            created_at=supplier.created_at,
            updated_at=supplier.updated_at,
        )
        self.db.execute(
            """
            INSERT INTO suppliers (id, email, phone, company, last_interaction)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                email            = excluded.email,
                phone            = excluded.phone,
                company          = excluded.company,
                last_interaction = excluded.last_interaction
            """,
            (
                supplier.id,
                supplier.email,
                supplier.phone,
                supplier.company,
                _dt_to_iso(supplier.last_interaction),
            ),
        )

    def get_supplier(self, supplier_id: str) -> Supplier | None:
        cur = self.db.execute(
            """
            SELECT e.id, e.entity_type, e.canonical_name, e.status, e.metadata,
                   e.created_at, e.updated_at,
                   s.email, s.phone, s.company, s.last_interaction
            FROM entities e
            JOIN suppliers s ON e.id = s.id
            WHERE e.id = ?
            """,
            (supplier_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return Supplier(
            id=row["id"],
            canonical_name=row["canonical_name"],
            status=row["status"],
            metadata=json.loads(row["metadata"]),
            created_at=_iso_to_dt(row["created_at"]) or datetime.now(),
            updated_at=_iso_to_dt(row["updated_at"]) or datetime.now(),
            email=row["email"],
            phone=row["phone"],
            company=row["company"],
            last_interaction=_iso_to_dt(row["last_interaction"]),
        )

    # ------------------------------------------------------------------ Product
    def upsert_product(self, product: Product) -> None:
        self.upsert_entity(
            id_=product.id,
            entity_type="product",
            canonical_name=product.canonical_name or product.name,
            status=product.status,
            metadata=product.metadata,
            created_at=product.created_at,
            updated_at=product.updated_at,
        )
        self.db.execute(
            """
            INSERT INTO products (id, name, sku, category, price, supplier_id, stock)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name        = excluded.name,
                sku         = excluded.sku,
                category    = excluded.category,
                price       = excluded.price,
                supplier_id = excluded.supplier_id,
                stock       = excluded.stock
            """,
            (
                product.id,
                product.name,
                product.sku,
                product.category,
                product.price,
                product.supplier_id,
                product.stock,
            ),
        )

    def get_product(self, product_id: str) -> Product | None:
        cur = self.db.execute(
            """
            SELECT e.id, e.entity_type, e.canonical_name, e.status, e.metadata,
                   e.created_at, e.updated_at,
                   p.name, p.sku, p.category, p.price, p.supplier_id, p.stock
            FROM entities e
            JOIN products p ON e.id = p.id
            WHERE e.id = ?
            """,
            (product_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return Product(
            id=row["id"],
            canonical_name=row["canonical_name"],
            status=row["status"],
            metadata=json.loads(row["metadata"]),
            created_at=_iso_to_dt(row["created_at"]) or datetime.now(),
            updated_at=_iso_to_dt(row["updated_at"]) or datetime.now(),
            name=row["name"],
            sku=row["sku"],
            category=row["category"],
            price=float(row["price"]),
            supplier_id=row["supplier_id"],
            stock=int(row["stock"]),
        )

    # ------------------------------------------------------------------ Order
    def upsert_order(self, order: Order) -> None:
        self.upsert_entity(
            id_=order.id,
            entity_type="order",
            canonical_name=order.canonical_name or f"Order {order.id[:8]}",
            status=order.status,
            metadata=order.metadata,
            created_at=order.created_at,
            updated_at=order.updated_at,
        )
        self.db.execute(
            """
            INSERT INTO orders (id, customer_id, order_date, status,
                                total_amount, currency, source_raw_item_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                customer_id        = excluded.customer_id,
                order_date         = excluded.order_date,
                status             = excluded.status,
                total_amount       = excluded.total_amount,
                currency           = excluded.currency,
                source_raw_item_id = excluded.source_raw_item_id
            """,
            (
                order.id,
                order.customer_id,
                _dt_to_iso(order.order_date),
                order.status,
                order.total_amount,
                order.currency,
                order.source_raw_item_id,
            ),
        )

    def get_order(self, order_id: str) -> Order | None:
        cur = self.db.execute(
            """
            SELECT e.id, e.entity_type, e.canonical_name, e.status, e.metadata,
                   e.created_at, e.updated_at,
                   o.customer_id, o.order_date, o.total_amount, o.currency,
                   o.source_raw_item_id
            FROM entities e
            JOIN orders o ON e.id = o.id
            WHERE e.id = ?
            """,
            (order_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return Order(
            id=row["id"],
            canonical_name=row["canonical_name"],
            status=row["status"],
            metadata=json.loads(row["metadata"]),
            created_at=_iso_to_dt(row["created_at"]) or datetime.now(),
            updated_at=_iso_to_dt(row["updated_at"]) or datetime.now(),
            customer_id=row["customer_id"],
            order_date=_iso_to_dt(row["order_date"]) or datetime.now(),
            total_amount=float(row["total_amount"]),
            currency=row["currency"],
            source_raw_item_id=row["source_raw_item_id"],
        )

    # ------------------------------------------------------------------ Invoice
    def upsert_invoice(self, invoice: Invoice) -> None:
        canon_name = (
            invoice.canonical_name
            or f"Invoice {invoice.invoice_number or invoice.id[:8]}"
        )
        self.upsert_entity(
            id_=invoice.id,
            entity_type="invoice",
            canonical_name=canon_name,
            status=invoice.status,
            metadata=invoice.metadata,
            created_at=invoice.created_at,
            updated_at=invoice.updated_at,
        )
        self.db.execute(
            """
            INSERT INTO invoices (id, invoice_number, customer_id, supplier_id,
                                  issue_date, due_date, amount, currency, status,
                                  payment_date, source_raw_item_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                invoice_number     = excluded.invoice_number,
                customer_id        = excluded.customer_id,
                supplier_id        = excluded.supplier_id,
                issue_date         = excluded.issue_date,
                due_date           = excluded.due_date,
                amount             = excluded.amount,
                currency           = excluded.currency,
                status             = excluded.status,
                payment_date       = excluded.payment_date,
                source_raw_item_id = excluded.source_raw_item_id
            """,
            (
                invoice.id,
                invoice.invoice_number,
                invoice.customer_id,
                invoice.supplier_id,
                _dt_to_iso(invoice.issue_date),
                _dt_to_iso(invoice.due_date),
                invoice.amount,
                invoice.currency,
                invoice.status,
                _dt_to_iso(invoice.payment_date),
                invoice.source_raw_item_id,
            ),
        )

    def get_invoice(self, invoice_id: str) -> Invoice | None:
        cur = self.db.execute(
            """
            SELECT e.id, e.entity_type, e.canonical_name, e.status, e.metadata,
                   e.created_at, e.updated_at,
                   i.invoice_number, i.customer_id, i.supplier_id, i.issue_date,
                   i.due_date, i.amount, i.currency, i.payment_date,
                   i.source_raw_item_id
            FROM entities e
            JOIN invoices i ON e.id = i.id
            WHERE e.id = ?
            """,
            (invoice_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return Invoice(
            id=row["id"],
            canonical_name=row["canonical_name"],
            status=row["status"],
            metadata=json.loads(row["metadata"]),
            created_at=_iso_to_dt(row["created_at"]) or datetime.now(),
            updated_at=_iso_to_dt(row["updated_at"]) or datetime.now(),
            invoice_number=row["invoice_number"],
            customer_id=row["customer_id"],
            supplier_id=row["supplier_id"],
            issue_date=_iso_to_dt(row["issue_date"]) or datetime.now(),
            due_date=_iso_to_dt(row["due_date"]),
            amount=float(row["amount"]),
            currency=row["currency"],
            payment_date=_iso_to_dt(row["payment_date"]),
            source_raw_item_id=row["source_raw_item_id"],
        )

    # ------------------------------------------------------------------ Employee
    def upsert_employee(self, employee: Employee) -> None:
        self.upsert_entity(
            id_=employee.id,
            entity_type="employee",
            canonical_name=employee.canonical_name or employee.name,
            status=employee.status,
            metadata=employee.metadata,
            created_at=employee.created_at,
            updated_at=employee.updated_at,
        )
        self.db.execute(
            """
            INSERT INTO employees (id, name, email, role, department, status)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name       = excluded.name,
                email      = excluded.email,
                role       = excluded.role,
                department = excluded.department,
                status     = excluded.status
            """,
            (
                employee.id,
                employee.name,
                employee.email,
                employee.role,
                employee.department,
                employee.status,
            ),
        )

    def get_employee(self, employee_id: str) -> Employee | None:
        cur = self.db.execute(
            """
            SELECT e.id, e.entity_type, e.canonical_name, e.status, e.metadata,
                   e.created_at, e.updated_at,
                   emp.name, emp.email, emp.role, emp.department, emp.status as emp_status
            FROM entities e
            JOIN employees emp ON e.id = emp.id
            WHERE e.id = ?
            """,
            (employee_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return Employee(
            id=row["id"],
            canonical_name=row["canonical_name"],
            status=row["status"],
            metadata=json.loads(row["metadata"]),
            created_at=_iso_to_dt(row["created_at"]) or datetime.now(),
            updated_at=_iso_to_dt(row["updated_at"]) or datetime.now(),
            name=row["name"],
            email=row["email"],
            role=row["role"],
            department=row["department"],
        )

    # ------------------------------------------------------------------ Communication
    def insert_communication(self, comm: Communication) -> None:
        self.db.execute(
            """
            INSERT OR IGNORE INTO communications (id, raw_item_id, type, sender, recipients,
                                                  subject, content, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                comm.id,
                comm.raw_item_id,
                comm.type,
                comm.sender,
                json.dumps(comm.recipients),
                comm.subject,
                comm.content,
                _dt_to_iso(comm.timestamp),
                json.dumps(comm.metadata),
            ),
        )

    def get_communications_for_entity(self, entity_id: str) -> list[Communication]:
        cur = self.db.execute(
            """
            SELECT DISTINCT c.*
            FROM communications c
            JOIN business_events e ON e.raw_item_id = c.raw_item_id
            WHERE e.entity_id = ?
            ORDER BY c.timestamp DESC
            """,
            (entity_id,),
        )
        results: list[Communication] = []
        for r in cur.fetchall():
            results.append(
                Communication(
                    id=r["id"],
                    raw_item_id=r["raw_item_id"],
                    type=r["type"],
                    sender=r["sender"],
                    recipients=json.loads(r["recipients"] or "[]"),
                    subject=r["subject"],
                    content=r["content"],
                    timestamp=_iso_to_dt(r["timestamp"]) or datetime.now(),
                    metadata=json.loads(r["metadata"] or "{}"),
                )
            )
        return results

    # ------------------------------------------------------------------ BusinessEvent
    def insert_event(self, event: BusinessEvent) -> None:
        self.db.execute(
            """
            INSERT OR IGNORE INTO business_events (id, type, entity_id, timestamp,
                                                  raw_item_id, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                event.id,
                event.type,
                event.entity_id,
                _dt_to_iso(event.timestamp),
                event.raw_item_id,
                json.dumps(event.metadata),
            ),
        )

    def get_events_for_entity(self, entity_id: str) -> list[BusinessEvent]:
        cur = self.db.execute(
            "SELECT * FROM business_events WHERE entity_id = ? ORDER BY timestamp DESC",
            (entity_id,),
        )
        return [
            BusinessEvent(
                id=r["id"],
                type=r["type"],
                entity_id=r["entity_id"],
                timestamp=_iso_to_dt(r["timestamp"]) or datetime.now(),
                raw_item_id=r["raw_item_id"],
                metadata=json.loads(r["metadata"] or "{}"),
            )
            for r in cur.fetchall()
        ]

    # ------------------------------------------------------------------ Commitment
    def upsert_commitment(self, commit: Commitment) -> None:
        self.db.execute(
            """
            INSERT INTO commitments (id, description, owner, related_entity, due_date,
                                    status, confidence, source_event_id, source_raw_item_id,
                                    created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                description = excluded.description,
                owner       = excluded.owner,
                due_date    = excluded.due_date,
                status      = excluded.status,
                confidence  = excluded.confidence,
                updated_at  = excluded.updated_at
            """,
            (
                commit.id,
                commit.description,
                commit.owner,
                commit.related_entity,
                _dt_to_iso(commit.due_date),
                commit.status,
                commit.confidence,
                commit.source_event_id,
                commit.source_raw_item_id,
                _dt_to_iso(commit.created_at),
                _dt_to_iso(commit.updated_at),
            ),
        )

    def get_commitments_for_entity(self, entity_id: str) -> list[Commitment]:
        cur = self.db.execute(
            "SELECT * FROM commitments WHERE related_entity = ? ORDER BY due_date ASC",
            (entity_id,),
        )
        return [
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
                created_at=_iso_to_dt(r["created_at"]) or datetime.now(),
                updated_at=_iso_to_dt(r["updated_at"]) or datetime.now(),
            )
            for r in cur.fetchall()
        ]

    def get_commitment(self, commit_id: str) -> Commitment | None:
        cur = self.db.execute("SELECT * FROM commitments WHERE id = ?", (commit_id,))
        r = cur.fetchone()
        if not r:
            return None
        return Commitment(
            id=r["id"],
            description=r["description"],
            owner=r["owner"],
            related_entity=r["related_entity"],
            due_date=_iso_to_dt(r["due_date"]),
            status=r["status"],
            confidence=float(r["confidence"]),
            source_event_id=r["source_event_id"],
            source_raw_item_id=r["source_raw_item_id"],
            created_at=_iso_to_dt(r["created_at"]) or datetime.now(),
            updated_at=_iso_to_dt(r["updated_at"]) or datetime.now(),
        )

    # ------------------------------------------------------------------ Relationship
    def insert_relationship(self, rel: Relationship) -> None:
        self.db.execute(
            """
            INSERT OR IGNORE INTO relationships (id, from_id, to_id, rel_type,
                                                provenance_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                rel.id,
                rel.from_id,
                rel.to_id,
                rel.rel_type,
                rel.provenance_id,
                _dt_to_iso(rel.created_at),
            ),
        )

    def get_relationships_for_entity(self, entity_id: str) -> list[Relationship]:
        cur = self.db.execute(
            """
            SELECT * FROM relationships
            WHERE from_id = ? OR to_id = ?
            ORDER BY created_at DESC
            """,
            (entity_id, entity_id),
        )
        return [
            Relationship(
                id=r["id"],
                from_id=r["from_id"],
                to_id=r["to_id"],
                rel_type=r["rel_type"],
                provenance_id=r["provenance_id"],
                created_at=_iso_to_dt(r["created_at"]) or datetime.now(),
            )
            for r in cur.fetchall()
        ]

    # ------------------------------------------------------------------ Provenance
    def insert_provenance(self, prov: Provenance) -> None:
        self.db.execute(
            """
            INSERT OR IGNORE INTO provenances (id, fact_id, fact_type, raw_item_id, source,
                                               source_item_id, source_date, extraction_method,
                                               confidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                prov.id,
                prov.fact_id,
                prov.fact_type,
                prov.raw_item_id,
                prov.source,
                prov.source_item_id,
                _dt_to_iso(prov.source_date),
                prov.extraction_method,
                prov.confidence,
                _dt_to_iso(prov.created_at),
            ),
        )

    def get_provenance_for_fact(self, fact_id: str) -> list[Provenance]:
        cur = self.db.execute(
            "SELECT * FROM provenances WHERE fact_id = ? ORDER BY created_at DESC", (fact_id,)
        )
        return [
            Provenance(
                id=r["id"],
                fact_id=r["fact_id"],
                fact_type=r["fact_type"],
                raw_item_id=r["raw_item_id"],
                source=r["source"],
                source_item_id=r["source_item_id"],
                source_date=_iso_to_dt(r["source_date"]) or datetime.now(),
                extraction_method=r["extraction_method"],
                confidence=float(r["confidence"]),
                created_at=_iso_to_dt(r["created_at"]) or datetime.now(),
            )
            for r in cur.fetchall()
        ]

    # ------------------------------------------------------------------ Derived Facts
    def insert_derived_fact(self, df: DerivedFact) -> None:
        self.db.execute(
            """
            INSERT OR IGNORE INTO derived_facts (id, fact_id, claim, confidence, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (df.id, df.fact_id, df.claim, df.confidence, _dt_to_iso(df.created_at)),
        )
        for raw_id in df.evidence_raw_item_ids:
            evidence_id = f"{df.id}:{raw_id}"
            self.db.execute(
                """
                INSERT OR IGNORE INTO derived_fact_evidence (id, derived_fact_id, raw_item_id)
                VALUES (?, ?, ?)
                """,
                (evidence_id, df.id, raw_id),
            )

    def get_derived_facts_for_entity(self, entity_id: str) -> list[DerivedFact]:
        cur = self.db.execute(
            "SELECT * FROM derived_facts WHERE fact_id = ? ORDER BY created_at DESC", (entity_id,)
        )
        results: list[DerivedFact] = []
        for r in cur.fetchall():
            cur_ev = self.db.execute(
                "SELECT raw_item_id FROM derived_fact_evidence WHERE derived_fact_id = ?",
                (r["id"],),
            )
            ev_ids = [ev_row[0] for ev_row in cur_ev.fetchall()]
            results.append(
                DerivedFact(
                    id=r["id"],
                    fact_id=r["fact_id"],
                    claim=r["claim"],
                    confidence=float(r["confidence"]),
                    evidence_raw_item_ids=ev_ids,
                    created_at=_iso_to_dt(r["created_at"]) or datetime.now(),
                )
            )
        return results

    # ------------------------------------------------------------------ Resolution Record
    def insert_resolution_record(self, record: ResolutionRecord) -> None:
        self.db.execute(
            """
            INSERT INTO resolution_records (id, candidate_entity, matched_entity, confidence,
                                           matching_reasons, source, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.id,
                record.candidate_entity,
                record.matched_entity,
                record.confidence,
                json.dumps(record.matching_reasons),
                record.source,
                _dt_to_iso(record.timestamp),
            ),
        )

    # ------------------------------------------------------------------ Candidates
    def find_customers_by_email_or_phone_or_company(
        self,
        email: str | None = None,
        phone: str | None = None,
        company: str | None = None,
        canonical_name: str | None = None,
    ) -> list[Customer]:
        clauses: list[str] = []
        params: list[Any] = []
        if email:
            clauses.append("c.email = ?")
            params.append(email.strip().lower())
        if phone:
            clauses.append("c.phone = ?")
            params.append(phone.strip())
        if company:
            clauses.append("LOWER(c.company) = ?")
            params.append(company.strip().lower())
        if canonical_name:
            c_name = canonical_name.strip().lower()
            clauses.append("LOWER(e.canonical_name) = ?")
            params.append(c_name)
            first_word = c_name.split()[0] if c_name else ""
            if len(first_word) >= 3:
                clauses.append("LOWER(e.canonical_name) LIKE ?")
                params.append(f"%{first_word}%")

        if not clauses:
            return []

        query = f"""
            SELECT e.id, e.entity_type, e.canonical_name, e.status, e.metadata,
                   e.created_at, e.updated_at,
                   c.email, c.phone, c.company, c.first_seen, c.last_interaction
            FROM entities e
            JOIN customers c ON e.id = c.id
            WHERE {" OR ".join(clauses)}
        """
        cur = self.db.execute(query, tuple(params))
        results: list[Customer] = []
        for row in cur.fetchall():
            results.append(
                Customer(
                    id=row["id"],
                    canonical_name=row["canonical_name"],
                    status=row["status"],
                    metadata=json.loads(row["metadata"]),
                    created_at=_iso_to_dt(row["created_at"]) or datetime.now(),
                    updated_at=_iso_to_dt(row["updated_at"]) or datetime.now(),
                    email=row["email"],
                    phone=row["phone"],
                    company=row["company"],
                    first_seen=_iso_to_dt(row["first_seen"]),
                    last_interaction=_iso_to_dt(row["last_interaction"]),
                )
            )
        return results

    def find_suppliers_by_email_or_phone_or_company(
        self,
        email: str | None = None,
        phone: str | None = None,
        company: str | None = None,
        canonical_name: str | None = None,
    ) -> list[Supplier]:
        clauses: list[str] = []
        params: list[Any] = []
        if email:
            clauses.append("s.email = ?")
            params.append(email.strip().lower())
        if phone:
            clauses.append("s.phone = ?")
            params.append(phone.strip())
        if company:
            clauses.append("LOWER(s.company) = ?")
            params.append(company.strip().lower())
        if canonical_name:
            c_name = canonical_name.strip().lower()
            clauses.append("LOWER(e.canonical_name) = ?")
            params.append(c_name)
            first_word = c_name.split()[0] if c_name else ""
            if len(first_word) >= 3:
                clauses.append("LOWER(e.canonical_name) LIKE ?")
                params.append(f"%{first_word}%")

        if not clauses:
            return []

        query = f"""
            SELECT e.id, e.entity_type, e.canonical_name, e.status, e.metadata,
                   e.created_at, e.updated_at,
                   s.email, s.phone, s.company, s.last_interaction
            FROM entities e
            JOIN suppliers s ON e.id = s.id
            WHERE {" OR ".join(clauses)}
        """
        cur = self.db.execute(query, tuple(params))
        results: list[Supplier] = []
        for row in cur.fetchall():
            results.append(
                Supplier(
                    id=row["id"],
                    canonical_name=row["canonical_name"],
                    status=row["status"],
                    metadata=json.loads(row["metadata"]),
                    created_at=_iso_to_dt(row["created_at"]) or datetime.now(),
                    updated_at=_iso_to_dt(row["updated_at"]) or datetime.now(),
                    email=row["email"],
                    phone=row["phone"],
                    company=row["company"],
                    last_interaction=_iso_to_dt(row["last_interaction"]),
                )
            )
        return results
