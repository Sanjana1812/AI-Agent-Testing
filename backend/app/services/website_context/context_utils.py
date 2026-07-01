"""Shared helpers for Website Context completeness checks."""

from __future__ import annotations

from app.services.planner.context_index import ContextIndex
from app.services.website_context.json_builder import WebsiteContext


def is_context_empty(context: WebsiteContext | None) -> bool:
    """Return True when no meaningful structure was extracted from the page."""
    if not context:
        return True
    index = ContextIndex(context)
    summary = index.summary()
    structural = (
        summary.get("navigation_count", 0)
        + summary.get("button_count", 0)
        + summary.get("form_count", 0)
        + summary.get("section_count", 0)
        + summary.get("heading_count", 0)
        + summary.get("link_count", 0)
    )
    title = (context.get("metadata") or {}).get("title", "")
    return structural == 0 and not str(title).strip()
