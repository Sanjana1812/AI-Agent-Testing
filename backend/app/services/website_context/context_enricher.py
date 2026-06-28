"""Merge raw DOM extraction with classification and priority into semantic context."""

from __future__ import annotations

import copy
import logging

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

    logger.debug(
        "[ContextEnricher] Enriched context — nav=%d buttons=%d forms=%d sections=%d",
        len(enriched.get("navigation", [])),
        len(enriched.get("buttons", [])),
        len(enriched.get("forms", [])),
        len(enriched.get("sections", [])),
    )
    return enriched
