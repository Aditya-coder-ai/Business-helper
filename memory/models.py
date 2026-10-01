"""Normalized domain models for Entity-Centric Business Memory."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

EntityType = Literal[
    "customer",
    "supplier",
    "product",
    "order",
    "invoice",
    "employee",
]

BusinessEventType = Literal[
    "ORDER_CREATED",
    "ORDER_UPDATED",
    "INVOICE_CREATED",
    "INVOICE_PAID",
    "INVOICE_OVERDUE",
    "EMAIL_RECEIVED",
    "EMAIL_SENT",
    "CUSTOMER_INTERACTION",
    "COMMITMENT_CREATED",
    "COMMITMENT_COMPLETED",
    "PRODUCT_PRICE_CHANGED",
    "INVENTORY_CHANGED",
    "SUPPLIER_CHANGE",
]

CommitmentStatus = Literal[
    "OPEN",
    "COMPLETED",
    "OVERDUE",
    "CANCELLED",
    "UNKNOWN",
]

RelationType = Literal[
    "places",
    "has",
    "supplies",
    "owns",
    "mentions",
    "relates_to",
    "extracted_from",
]


def utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


class BaseEntity(BaseModel):
    """Common fields for all business entities."""

    id: str = Field(..., min_length=1)
    entity_type: EntityType
    canonical_name: str = Field(..., min_length=1)
    status: str = "active"
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Customer(BaseEntity):
    """Customer entity with contact details and touchpoints."""

    entity_type: Literal["customer"] = "customer"
    email: str = ""
    phone: str = ""
    company: str = ""
    first_seen: datetime | None = None
    last_interaction: datetime | None = None


class Supplier(BaseEntity):
    """Supplier entity with contact info and interaction recency."""

    entity_type: Literal["supplier"] = "supplier"
    email: str = ""
    phone: str = ""
    company: str = ""
    last_interaction: datetime | None = None


class Product(BaseEntity):
    """Catalog product linked to a supplier and inventory level."""

    entity_type: Literal["product"] = "product"
    name: str = ""
    sku: str = ""
    category: str = ""
    price: float = 0.0
    supplier_id: str | None = None
    stock: int = 0


class Order(BaseEntity):
    """Sales order associated with a customer and raw provenance."""

    entity_type: Literal["order"] = "order"
    customer_id: str | None = None
    order_date: datetime = Field(default_factory=utc_now)
    status: str = "pending"
    total_amount: float = 0.0
    currency: str = "USD"
    source_raw_item_id: str = ""


class Invoice(BaseEntity):
    """Billing invoice tracking status, dates, and amounts."""

    entity_type: Literal["invoice"] = "invoice"
    invoice_number: str = ""
    customer_id: str | None = None
    supplier_id: str | None = None
    issue_date: datetime = Field(default_factory=utc_now)
    due_date: datetime | None = None
    amount: float = 0.0
    currency: str = "USD"
    status: str = "draft"
    payment_date: datetime | None = None
    source_raw_item_id: str = ""


class Employee(BaseEntity):
    """Internal employee profile."""

    entity_type: Literal["employee"] = "employee"
    name: str = ""
    email: str = ""
    role: str = ""
    department: str = ""
    status: str = "active"


class Communication(BaseModel):
    """Message or document ingested from raw sources."""

    id: str = Field(..., min_length=1)
    raw_item_id: str = Field(..., min_length=1)
    type: str = "email"
    sender: str = ""
    recipients: list[str] = Field(default_factory=list)
    subject: str = ""
    content: str = ""
    timestamp: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BusinessEvent(BaseModel):
    """Discrete state change or interaction event."""

    id: str = Field(..., min_length=1)
    type: BusinessEventType
    entity_id: str = Field(..., min_length=1)
    timestamp: datetime = Field(default_factory=utc_now)
    raw_item_id: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class Commitment(BaseModel):
    """Actionable promise, obligation, or deadline extracted from communications."""

    id: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    owner: str = ""
    related_entity: str = Field(..., min_length=1)
    due_date: datetime | None = None
    status: CommitmentStatus = "OPEN"
    confidence: float = 1.0
    source_event_id: str | None = None
    source_raw_item_id: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Relationship(BaseModel):
    """Directed relational link between two business entities."""

    id: str = Field(..., min_length=1)
    from_id: str = Field(..., min_length=1)
    to_id: str = Field(..., min_length=1)
    rel_type: RelationType
    provenance_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class Provenance(BaseModel):
    """Audit trail tracking the origin and confidence of any stored fact."""

    id: str = Field(..., min_length=1)
    fact_id: str = Field(..., min_length=1)
    fact_type: str = Field(..., min_length=1)
    raw_item_id: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1)
    source_item_id: str = Field(..., min_length=1)
    source_date: datetime = Field(default_factory=utc_now)
    extraction_method: str = "deterministic"
    confidence: float = 1.0
    created_at: datetime = Field(default_factory=utc_now)


class DerivedFact(BaseModel):
    """Synthesized business conclusion substantiated by multiple raw items."""

    id: str = Field(..., min_length=1)
    fact_id: str = Field(..., min_length=1)
    claim: str = Field(..., min_length=1)
    confidence: float = 1.0
    evidence_raw_item_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class ResolutionRecord(BaseModel):
    """Audit log of entity resolution matches, candidates, and confidences."""

    id: str = Field(..., min_length=1)
    candidate_entity: str = Field(..., min_length=1)
    matched_entity: str = Field(..., min_length=1)
    confidence: float
    matching_reasons: list[str] = Field(default_factory=list)
    source: str = ""
    timestamp: datetime = Field(default_factory=utc_now)
