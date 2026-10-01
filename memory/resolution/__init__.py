"""Entity resolution system evaluating identity signals and managing confidence-based merges."""

from __future__ import annotations

from memory.resolution.resolver import EntityResolver, ResolutionDecision

__all__ = ["EntityResolver", "ResolutionDecision"]
