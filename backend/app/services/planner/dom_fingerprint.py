"""Lightweight DOM fingerprint from Website Context (ignores dynamic IDs)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.services.website_context.json_builder import WebsiteContext


def _heading_text(context: WebsiteContext, level: int, limit: int = 3) -> list[str]:
    texts: list[str] = []
    for heading in context.get("headings", []):
        if heading.get("level") == level and heading.get("text"):
            texts.append(str(heading["text"]).strip())
        if len(texts) >= limit:
            break
    return texts


def fingerprint_from_context(context: WebsiteContext) -> dict[str, Any]:
    """Build a stable fingerprint snapshot from enriched Website Context."""
    metadata = context.get("metadata", {})
    navigation = sorted(
        str(item.get("text", "")).strip().lower()
        for item in context.get("navigation", [])
        if item.get("text")
    )
    buttons = sorted(
        str(item.get("text", "")).strip().lower()
        for item in context.get("buttons", [])
        if item.get("text")
    )[:12]

    return {
        "title": str(metadata.get("title", "")).strip().lower(),
        "h1": _heading_text(context, 1, limit=1),
        "h2": _heading_text(context, 2, limit=3),
        "navigation_items": navigation[:12],
        "button_texts": buttons,
        "form_count": len(context.get("forms", [])),
        "section_count": len(context.get("sections", [])),
    }


def fingerprint_hash(fingerprint: dict[str, Any]) -> str:
    payload = json.dumps(fingerprint, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def hero_heading_text(context: WebsiteContext) -> str | None:
    headings = context.get("headings", [])
    for heading in headings:
        if heading.get("level") == 1 and heading.get("text"):
            return str(heading["text"]).strip()
    return headings[0].get("text") if headings else None


def significantly_changed(previous: dict[str, Any], current: dict[str, Any]) -> bool:
    """Return True when the page fingerprint changed in a meaningful way."""
    if previous.get("title") != current.get("title"):
        return True
    if previous.get("h1") != current.get("h1"):
        return True
    if previous.get("form_count") != current.get("form_count"):
        return True
    if abs(int(previous.get("section_count", 0)) - int(current.get("section_count", 0))) >= 2:
        return True

    prev_h2 = set(previous.get("h2", []))
    curr_h2 = set(current.get("h2", []))
    if prev_h2 and curr_h2 and prev_h2 != curr_h2:
        return True

    prev_nav = set(previous.get("navigation_items", []))
    curr_nav = set(current.get("navigation_items", []))
    if prev_nav and curr_nav:
        overlap = len(prev_nav & curr_nav) / max(len(prev_nav), 1)
        if overlap < 0.5:
            return True

    return fingerprint_hash(previous) != fingerprint_hash(current)
