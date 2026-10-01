"""FastAPI application exposing Business Memory Service as JSON endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from memory.database import MemoryDatabase
from memory.service import MemoryService

app = FastAPI(
    title="Business Memory API",
    version="0.1.0",
    description="Layer 2 — Entity-Centric Business Memory",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazy-init singleton
_db: MemoryDatabase | None = None
_svc: MemoryService | None = None


def get_service() -> MemoryService:
    """Return or create the MemoryService singleton."""
    global _db, _svc  # noqa: PLW0603
    if _svc is None:
        _db = MemoryDatabase(Path("memory.db"))
        _svc = MemoryService(_db)
    return _svc


def _model_dict(obj: Any) -> dict[str, Any]:
    """Convert a Pydantic model or dict to a JSON-safe dict."""
    if hasattr(obj, "model_dump"):
        d: dict[str, Any] = obj.model_dump(mode="json")
        return d
    if isinstance(obj, dict):
        return obj
    return {"value": str(obj)}


# ------------------------------------------------------------------ Entities
@app.get("/api/entities")
def list_entities(
    entity_type: str | None = Query(None),
    q: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    svc = get_service()
    if q:
        items = svc.search_business_memory(q, entity_type=entity_type, limit=limit)
    else:
        items = svc.list_entities(entity_type=entity_type, limit=limit, offset=offset)
    return {"entities": items, "count": len(items)}


@app.get("/api/entities/{entity_id}")
def get_entity(entity_id: str) -> dict[str, Any]:
    svc = get_service()
    # Try each entity type
    for getter in [
        svc.get_customer,
        svc.get_supplier,
        svc.get_product,
        svc.get_order,
        svc.get_invoice,
        svc.get_employee,
    ]:
        result = getter(entity_id)
        if result:
            return _model_dict(result)
    # Fallback to raw entity
    raw = svc.repo.get_entity_raw(entity_id)
    if raw:
        return raw
    raise HTTPException(status_code=404, detail="Entity not found")


# ------------------------------------------------------------------ Timeline
@app.get("/api/entities/{entity_id}/timeline")
def get_timeline(entity_id: str) -> dict[str, Any]:
    svc = get_service()
    timeline = svc.get_entity_timeline(entity_id)
    return {"entity_id": entity_id, "timeline": timeline}


# ------------------------------------------------------------------ Relationships
@app.get("/api/entities/{entity_id}/relationships")
def get_relationships(entity_id: str) -> dict[str, Any]:
    svc = get_service()
    rels = svc.get_entity_relationships(entity_id)
    return {"entity_id": entity_id, "relationships": rels}


# ------------------------------------------------------------------ Communications
@app.get("/api/entities/{entity_id}/communications")
def get_communications(entity_id: str) -> dict[str, Any]:
    svc = get_service()
    comms = svc.repo.get_communications_for_entity(entity_id)
    return {
        "entity_id": entity_id,
        "communications": [_model_dict(c) for c in comms],
    }


# ------------------------------------------------------------------ Commitments
@app.get("/api/entities/{entity_id}/commitments")
def get_entity_commitments(entity_id: str) -> dict[str, Any]:
    svc = get_service()
    commits = svc.repo.get_commitments_for_entity(entity_id)
    return {
        "entity_id": entity_id,
        "commitments": [_model_dict(c) for c in commits],
    }


@app.get("/api/commitments/open")
def get_open_commitments() -> dict[str, Any]:
    svc = get_service()
    commits = svc.get_open_commitments()
    return {"commitments": [_model_dict(c) for c in commits]}


# ------------------------------------------------------------------ Invoices
@app.get("/api/invoices/overdue")
def get_overdue_invoices() -> dict[str, Any]:
    svc = get_service()
    invoices = svc.get_overdue_invoices()
    return {"invoices": [_model_dict(i) for i in invoices]}


# ------------------------------------------------------------------ Events
@app.get("/api/events/recent")
def get_recent_events(
    limit: int = Query(50, ge=1, le=500),
) -> dict[str, Any]:
    svc = get_service()
    events = svc.get_recent_events(limit=limit)
    return {"events": [_model_dict(e) for e in events]}


# ------------------------------------------------------------------ Provenance
@app.get("/api/provenance/{fact_id}")
def get_provenance(fact_id: str) -> dict[str, Any]:
    svc = get_service()
    evidence = svc.get_source_evidence(fact_id)
    return {
        "fact_id": fact_id,
        "provenance": [_model_dict(p) for p in evidence],
    }
