"""Sprint 5.2 — Replanning reason templates (deterministic, no LLM)."""

from __future__ import annotations

REPLAN_REASON_TEMPLATES: dict[str, str] = {
    "navigation_unavailable": (
        "Original step '{original}' is unavailable at runtime. "
        "Replacing with semantically related destination '{replacement}' from site navigation."
    ),
    "selector_exhausted": (
        "Selectors for '{original}' could not be resolved. "
        "Switching to alternative navigation target '{replacement}'."
    ),
    "priority_flow_shift": (
        "Runtime observation shows '{original}' is not reachable. "
        "Continuing via strategy-aligned path '{replacement}'."
    ),
}
