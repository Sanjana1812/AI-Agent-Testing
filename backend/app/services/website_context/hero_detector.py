"""Intelligent hero section detection for production websites."""

from __future__ import annotations

from typing import Any

from app.services.website_context.json_builder import WebsiteContext


def _score_section(section: dict, *, index: int) -> float:
    score = float(section.get("priority", 0))
    viewport_top = float(section.get("viewport_top", 9999))
    viewport_area = float(section.get("viewport_area", 0))
    buttons = int(section.get("buttons_count", 0))
    links = int(section.get("links_count", 0))
    heading = (section.get("heading") or "").lower()
    class_name = (section.get("class_name") or "").lower()
    element_id = (section.get("id") or "").lower()
    role = (section.get("role") or "").lower()
    blob = f"{heading} {class_name} {element_id}"

    if index == 0:
        score += 25
    if viewport_top <= 120:
        score += 30
    if viewport_area >= 50_000:
        score += 20
    if role == "banner" or "hero" in blob or "banner" in blob or "landing" in blob:
        score += 35
    if section.get("tag") == "header" and heading:
        score += 10
    if buttons + links >= 1:
        score += 8
    if "footer" in blob:
        score -= 40
    return score


def detect_hero_section(context: WebsiteContext) -> dict | None:
    """Choose the true landing hero from sections and headings."""
    sections = list(context.get("sections", []))
    if not sections:
        headings = context.get("headings", [])
        for heading in headings:
            if heading.get("level") == 1 and heading.get("text"):
                return {
                    "heading": heading["text"],
                    "semantic_type": "hero",
                    "priority": heading.get("priority", 80),
                    "tag": "section",
                }
        return None

    ranked = sorted(
        enumerate(sections),
        key=lambda pair: _score_section(pair[1], index=pair[0]),
        reverse=True,
    )
    hero = dict(ranked[0][1])
    hero["semantic_type"] = "hero"
    hero["priority"] = max(int(hero.get("priority", 0)), 90)
    return hero


def detect_hero_heading(context: WebsiteContext) -> dict | None:
    headings = context.get("headings", [])
    for heading in headings:
        if heading.get("level") == 1 and heading.get("text"):
            return heading

    hero = detect_hero_section(context)
    if hero and hero.get("heading"):
        return {"level": 1, "text": hero["heading"], "classification": "Hero", "priority": hero.get("priority", 90)}

    return headings[0] if headings else None
