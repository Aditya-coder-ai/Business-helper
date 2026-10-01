"""Injectable LLM client interface and Pydantic validation schemas for semantic extraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from memory.models import BusinessEventType, EntityType, RelationType


class LLMEntityCandidate(BaseModel):
    """Semantic entity candidate extracted via LLM."""

    name: str = Field(..., min_length=1)
    entity_type: EntityType = "customer"
    email: str = ""
    phone: str = ""
    company: str = ""
    role: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMEventCandidate(BaseModel):
    """Semantic business event candidate extracted via LLM."""

    type: BusinessEventType
    entity_name: str = Field(..., min_length=1)
    date: datetime | None = None
    details: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMCommitmentCandidate(BaseModel):
    """Semantic commitment candidate extracted via LLM."""

    description: str = Field(..., min_length=1)
    owner: str = ""
    related_entity_name: str = Field(..., min_length=1)
    due_date: datetime | None = None
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)


class LLMRelationshipCandidate(BaseModel):
    """Semantic relationship candidate between entities."""

    from_name: str = Field(..., min_length=1)
    to_name: str = Field(..., min_length=1)
    rel_type: RelationType


class LLMExtractionResult(BaseModel):
    """Validated structured output payload returned from LLM semantic inference."""

    entities: list[LLMEntityCandidate] = Field(default_factory=list)
    events: list[LLMEventCandidate] = Field(default_factory=list)
    commitments: list[LLMCommitmentCandidate] = Field(default_factory=list)
    relationships: list[LLMRelationshipCandidate] = Field(default_factory=list)


class LLMClient(ABC):
    """Abstract interface for LLM-based semantic extraction."""

    @abstractmethod
    def extract_semantics(
        self,
        text: str,
        context: dict[str, Any] | None = None,
    ) -> LLMExtractionResult:
        """Parse ambiguous business semantics from content and validate into strict schema."""
        ...


class FakeLLMClient(LLMClient):
    """Test fake for LLM client with programmable responses and fault injection."""

    def __init__(
        self,
        default_result: LLMExtractionResult | None = None,
        should_fail: bool = False,
        failure_exception: Exception | None = None,
    ) -> None:
        self.default_result = default_result or LLMExtractionResult()
        self.should_fail = should_fail
        self.failure_exception = failure_exception or RuntimeError(
            "Simulated LLM service breakdown"
        )
        self.calls: list[dict[str, Any]] = []

    def extract_semantics(
        self,
        text: str,
        context: dict[str, Any] | None = None,
    ) -> LLMExtractionResult:
        self.calls.append({"text": text, "context": context})
        if self.should_fail:
            raise self.failure_exception
        return self.default_result
