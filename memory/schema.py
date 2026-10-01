"""Relational database schema for Entity-Centric Business Memory.

Postgres Migration Boundary:
---------------------------
The schema defined here currently uses SQLite-compatible DDL (WAL mode, PRAGMA foreign_keys=ON,
ISO-8601 UTC text timestamps, JSON text for metadata/recipients/matching_reasons).

To migrate to PostgreSQL:
1. Engine: Swap sqlite3 with SQLAlchemy / psycopg3 / asyncpg pooled connection.
2. Timestamps: Replace TEXT timestamp columns with TIMESTAMPTZ.
3. Semi-structured: Replace TEXT metadata/recipients/matching_reasons with JSONB.
4. Auto-increment / UUIDs: Replace deterministic hashes with UUID / ULID or BIGSERIAL.
5. Idempotent Upserts: Translate `INSERT INTO ... ON CONFLICT DO UPDATE` to PostgreSQL.
6. Full-Text Search: Replace LIKE/sub-select search with PostgreSQL `tsvector` + GIN.

All raw queries and schema definitions remain strictly encapsulated in this package.
"""

from __future__ import annotations

DDL_STATEMENTS: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS entities (
        id              TEXT PRIMARY KEY,
        entity_type     TEXT NOT NULL,
        canonical_name  TEXT NOT NULL,
        status          TEXT NOT NULL DEFAULT 'active',
        metadata        TEXT NOT NULL DEFAULT '{}',
        created_at      TEXT NOT NULL,
        updated_at      TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS customers (
        id                TEXT PRIMARY KEY REFERENCES entities(id) ON DELETE CASCADE,
        email             TEXT NOT NULL DEFAULT '',
        phone             TEXT NOT NULL DEFAULT '',
        company           TEXT NOT NULL DEFAULT '',
        first_seen        TEXT,
        last_interaction  TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS suppliers (
        id                TEXT PRIMARY KEY REFERENCES entities(id) ON DELETE CASCADE,
        email             TEXT NOT NULL DEFAULT '',
        phone             TEXT NOT NULL DEFAULT '',
        company           TEXT NOT NULL DEFAULT '',
        last_interaction  TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS products (
        id           TEXT PRIMARY KEY REFERENCES entities(id) ON DELETE CASCADE,
        name         TEXT NOT NULL DEFAULT '',
        sku          TEXT NOT NULL DEFAULT '',
        category     TEXT NOT NULL DEFAULT '',
        price        REAL NOT NULL DEFAULT 0.0,
        supplier_id  TEXT REFERENCES entities(id) ON DELETE SET NULL,
        stock        INTEGER NOT NULL DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS orders (
        id                  TEXT PRIMARY KEY REFERENCES entities(id) ON DELETE CASCADE,
        customer_id         TEXT REFERENCES entities(id) ON DELETE SET NULL,
        order_date          TEXT NOT NULL,
        status              TEXT NOT NULL DEFAULT 'pending',
        total_amount        REAL NOT NULL DEFAULT 0.0,
        currency            TEXT NOT NULL DEFAULT 'USD',
        source_raw_item_id  TEXT NOT NULL DEFAULT ''
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS invoices (
        id                  TEXT PRIMARY KEY REFERENCES entities(id) ON DELETE CASCADE,
        invoice_number      TEXT NOT NULL DEFAULT '',
        customer_id         TEXT REFERENCES entities(id) ON DELETE SET NULL,
        supplier_id         TEXT REFERENCES entities(id) ON DELETE SET NULL,
        issue_date          TEXT NOT NULL,
        due_date            TEXT,
        amount              REAL NOT NULL DEFAULT 0.0,
        currency            TEXT NOT NULL DEFAULT 'USD',
        status              TEXT NOT NULL DEFAULT 'draft',
        payment_date        TEXT,
        source_raw_item_id  TEXT NOT NULL DEFAULT ''
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS employees (
        id          TEXT PRIMARY KEY REFERENCES entities(id) ON DELETE CASCADE,
        name        TEXT NOT NULL DEFAULT '',
        email       TEXT NOT NULL DEFAULT '',
        role        TEXT NOT NULL DEFAULT '',
        department  TEXT NOT NULL DEFAULT '',
        status      TEXT NOT NULL DEFAULT 'active'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS communications (
        id           TEXT PRIMARY KEY,
        raw_item_id  TEXT NOT NULL,
        type         TEXT NOT NULL DEFAULT 'email',
        sender       TEXT NOT NULL DEFAULT '',
        recipients   TEXT NOT NULL DEFAULT '[]',
        subject      TEXT NOT NULL DEFAULT '',
        content      TEXT NOT NULL DEFAULT '',
        timestamp    TEXT NOT NULL,
        metadata     TEXT NOT NULL DEFAULT '{}'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS business_events (
        id           TEXT PRIMARY KEY,
        type         TEXT NOT NULL,
        entity_id    TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
        timestamp    TEXT NOT NULL,
        raw_item_id  TEXT NOT NULL DEFAULT '',
        metadata     TEXT NOT NULL DEFAULT '{}'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS commitments (
        id                  TEXT PRIMARY KEY,
        description         TEXT NOT NULL,
        owner               TEXT NOT NULL DEFAULT '',
        related_entity      TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
        due_date            TEXT,
        status              TEXT NOT NULL DEFAULT 'OPEN',
        confidence          REAL NOT NULL DEFAULT 1.0,
        source_event_id     TEXT REFERENCES business_events(id) ON DELETE SET NULL,
        source_raw_item_id  TEXT NOT NULL DEFAULT '',
        created_at          TEXT NOT NULL,
        updated_at          TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS provenances (
        id                 TEXT PRIMARY KEY,
        fact_id            TEXT NOT NULL,
        fact_type          TEXT NOT NULL,
        raw_item_id        TEXT NOT NULL,
        source             TEXT NOT NULL,
        source_item_id     TEXT NOT NULL,
        source_date        TEXT NOT NULL,
        extraction_method  TEXT NOT NULL DEFAULT 'deterministic',
        confidence         REAL NOT NULL DEFAULT 1.0,
        created_at         TEXT NOT NULL,
        UNIQUE(fact_id, raw_item_id, extraction_method)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS relationships (
        id             TEXT PRIMARY KEY,
        from_id        TEXT NOT NULL,
        to_id          TEXT NOT NULL,
        rel_type       TEXT NOT NULL,
        provenance_id  TEXT REFERENCES provenances(id) ON DELETE SET NULL,
        created_at     TEXT NOT NULL,
        UNIQUE(from_id, to_id, rel_type)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS derived_facts (
        id          TEXT PRIMARY KEY,
        fact_id     TEXT NOT NULL,
        claim       TEXT NOT NULL,
        confidence  REAL NOT NULL DEFAULT 1.0,
        created_at  TEXT NOT NULL,
        UNIQUE(fact_id, claim)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS derived_fact_evidence (
        id               TEXT PRIMARY KEY,
        derived_fact_id  TEXT NOT NULL REFERENCES derived_facts(id) ON DELETE CASCADE,
        raw_item_id      TEXT NOT NULL,
        UNIQUE(derived_fact_id, raw_item_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS resolution_records (
        id                TEXT PRIMARY KEY,
        candidate_entity  TEXT NOT NULL,
        matched_entity    TEXT NOT NULL,
        confidence        REAL NOT NULL,
        matching_reasons  TEXT NOT NULL DEFAULT '[]',
        source            TEXT NOT NULL DEFAULT '',
        timestamp         TEXT NOT NULL
    )
    """,
    # Indexes
    "CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type)",
    "CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(canonical_name)",
    "CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email)",
    "CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone)",
    "CREATE INDEX IF NOT EXISTS idx_suppliers_email ON suppliers(email)",
    "CREATE INDEX IF NOT EXISTS idx_invoices_customer ON invoices(customer_id)",
    "CREATE INDEX IF NOT EXISTS idx_invoices_supplier ON invoices(supplier_id)",
    "CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status)",
    "CREATE INDEX IF NOT EXISTS idx_invoices_due ON invoices(due_date)",
    "CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id)",
    "CREATE INDEX IF NOT EXISTS idx_products_supplier ON products(supplier_id)",
    "CREATE INDEX IF NOT EXISTS idx_relationships_from ON relationships(from_id)",
    "CREATE INDEX IF NOT EXISTS idx_relationships_to ON relationships(to_id)",
    (
        "CREATE INDEX IF NOT EXISTS idx_events_entity_time "
        "ON business_events(entity_id, timestamp DESC)"
    ),
    "CREATE INDEX IF NOT EXISTS idx_events_raw ON business_events(raw_item_id)",
    "CREATE INDEX IF NOT EXISTS idx_commitments_entity ON commitments(related_entity, status)",
    "CREATE INDEX IF NOT EXISTS idx_commitments_raw ON commitments(source_raw_item_id)",
    "CREATE INDEX IF NOT EXISTS idx_provenance_fact ON provenances(fact_id)",
    "CREATE INDEX IF NOT EXISTS idx_provenance_raw ON provenances(raw_item_id)",
    "CREATE INDEX IF NOT EXISTS idx_communications_raw ON communications(raw_item_id)",
    # Triggers for referential cleanup
    """
    CREATE TRIGGER IF NOT EXISTS trg_delete_entity_relationships
    AFTER DELETE ON entities
    BEGIN
        DELETE FROM relationships WHERE from_id = OLD.id OR to_id = OLD.id;
    END;
    """,
    """
    CREATE TRIGGER IF NOT EXISTS trg_delete_comm_relationships
    AFTER DELETE ON communications
    BEGIN
        DELETE FROM relationships WHERE from_id = OLD.id OR to_id = OLD.id;
    END;
    """,
    """
    CREATE TRIGGER IF NOT EXISTS trg_delete_commit_relationships
    AFTER DELETE ON commitments
    BEGIN
        DELETE FROM relationships WHERE from_id = OLD.id OR to_id = OLD.id;
    END;
    """,
]
