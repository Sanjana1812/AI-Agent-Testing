"""Context-aware deterministic fallback — delegates to the journey builder."""

from __future__ import annotations

from app.services.planner.context_index import ContextIndex
from app.services.planner.intent_classifier import IntentType, classify_intent, intent_from_legacy
from app.services.planner.journey_builder import build_validated_journey


def build_context_plan(goal: str, intent: str, index: ContextIndex) -> list[dict]:
    """Backward-compatible entry point for deterministic plans."""
    resolved = intent_from_legacy(intent)
    if resolved == IntentType.UNKNOWN:
        resolved = classify_intent(goal)
    return build_validated_journey(goal, resolved, index)
