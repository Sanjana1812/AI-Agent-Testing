"""Merge raw DOM extraction with classification and priority into semantic context."""

from __future__ import annotations

import copy
import logging

from app.services.planner.semantic_filter import filter_context
from app.services.website_context.element_classifier import (
    classify_anchor_link,
    classify_button,
    classify_footer_link,
    classify_form,
    classify_heading,
    classify_nav_link,
    classify_section,
    infer_button_type,
)
from app.services.website_context.hero_detector import detect_hero_heading, detect_hero_section
from app.services.website_context.json_builder import WebsiteContext
from app.services.website_context.priority_engine import (
    score_button,
    score_classification,
    score_form,
    score_nav_link,
    score_section,
)

logger = logging.getLogger(__name__)


def enrich(context: WebsiteContext) -> WebsiteContext:
    """
    Enrich raw Website Context with classification, semantic types, and priority scores.

    Original fields are preserved for backward compatibility.
    """
    enriched: WebsiteContext = copy.deepcopy(context)

    for index, heading in enumerate(enriched.get("headings", [])):
        classification = classify_heading(heading, index=index)
        heading["classification"] = classification
        heading["priority"] = score_classification(classification, text=heading.get("text", ""))

    for link in enriched.get("navigation", []):
        classification = classify_nav_link(link)
        link["classification"] = classification
        link["priority"] = score_nav_link(link, classification)

    for button in enriched.get("buttons", []):
        classification = classify_button(button)
        button["classification"] = classification
        button["type"] = infer_button_type(button, classification)
        button["enabled"] = not button.get("disabled", False)
        button["priority"] = score_button(button, classification)

    for form in enriched.get("forms", []):
        classification = classify_form(form)
        form["classification"] = classification
        form["required"] = sum(1 for field in form.get("fields", []) if field.get("required"))
        form["priority"] = score_form(form, classification)

    for index, section in enumerate(enriched.get("sections", [])):
        semantic_type = classify_section(section, index=index)
        section["semantic_type"] = semantic_type
        section["priority"] = score_section(semantic_type)

    for link in enriched.get("footer", []):
        link.setdefault("section", "footer")
        classification = classify_footer_link(link)
        link["classification"] = classification
        link["priority"] = score_nav_link(link, classification)

    for link in enriched.get("links", []):
        classification = classify_anchor_link(link)
        link["classification"] = classification
        link["priority"] = score_nav_link(link, classification)

    for component in enriched.get("components", []):
        component["classification"] = str(component.get("type", "component")).replace("_", " ").title()
        component["priority"] = int(component.get("importance", 50))

    hero_section = detect_hero_section(enriched)
    if hero_section:
        sections = enriched.get("sections", [])
        replaced = False
        for section in sections:
            if section.get("semantic_type") == "hero" or section.get("heading") == hero_section.get("heading"):
                section.update(hero_section)
                replaced = True
                break
        if not replaced:
            sections.insert(0, hero_section)
            enriched["sections"] = sections

    hero_heading = detect_hero_heading(enriched)
    if hero_heading:
        headings = enriched.get("headings", [])
        if not any(h.get("level") == 1 for h in headings):
            headings.insert(0, hero_heading)
            enriched["headings"] = headings

    enriched = filter_context(enriched)

    logger.debug(
        "[ContextEnricher] Enriched context — nav=%d buttons=%d forms=%d sections=%d components=%d",
        len(enriched.get("navigation", [])),
        len(enriched.get("buttons", [])),
        len(enriched.get("forms", [])),
        len(enriched.get("sections", [])),
        len(enriched.get("components", [])),
    )
    return enriched
