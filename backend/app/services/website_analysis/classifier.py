"""Website archetype classifier from structured context (Sprint 4.1)."""

from __future__ import annotations

import re
from typing import Any

from app.services.planner.context_index import ContextIndex
from app.services.website_analysis.prompts import (
    AUDIENCE_BY_TYPE,
    DOMAIN_BY_TYPE,
    GOAL_BY_TYPE,
    PURPOSE_BY_TYPE,
    WEBSITE_TYPE_KEYWORDS,
)
from app.services.website_context.json_builder import WebsiteContext

SKIP_LABELS = frozenset({"home", "homepage", "logo", "skip to content"})


def _has_login_form(index: ContextIndex) -> bool:
    if index.has_password_field():
        return True
    return any(
        str(form.get("classification", "")).lower() == "login"
        for form in index.context.get("forms", [])
    )


def _normalize(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value).strip())


def _build_signal_blob(context: WebsiteContext) -> str:
    parts: list[str] = []
    metadata = context.get("metadata", {})
    parts.append(_normalize(metadata.get("title")).lower())
    parts.append(_normalize(metadata.get("meta_description")).lower())

    for collection in ("navigation", "buttons", "headings", "footer", "links"):
        for item in context.get(collection, [])[:12]:
            if isinstance(item, dict):
                parts.append(_normalize(item.get("text")).lower())
                parts.append(_normalize(item.get("heading")).lower())

    for form in context.get("forms", [])[:4]:
        parts.append(_normalize(form.get("classification")).lower())
        for field in form.get("fields", [])[:6]:
            if isinstance(field, dict):
                parts.append(_normalize(field.get("label")).lower())
                parts.append(_normalize(field.get("name")).lower())

    return " ".join(part for part in parts if part)


def _score_types(blob: str) -> dict[str, int]:
    scores: dict[str, int] = {key: 0 for key in WEBSITE_TYPE_KEYWORDS}
    for website_type, keywords in WEBSITE_TYPE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in blob:
                scores[website_type] += 2 if " " in keyword else 1
    return scores


def _structural_boost(scores: dict[str, int], index: ContextIndex) -> None:
    if _has_login_form(index):
        scores["Authentication Portal"] += 3
    if any("pricing" in _normalize(button.get("text")).lower() for button in index.usable_buttons()):
        scores["SaaS"] += 2
    if any(
        token in _normalize(button.get("text")).lower()
        for button in index.usable_buttons()
        for token in ("cart", "checkout", "shop", "buy")
    ):
        scores["Ecommerce"] += 3
    if any("appointment" in _normalize(link.get("text")).lower() for link in index.context.get("navigation", [])):
        scores["Hospital"] += 3
    if any("project" in _normalize(link.get("text")).lower() for link in index.context.get("navigation", [])):
        scores["Portfolio"] += 2
    if len(index.context.get("forms", [])) >= 2 and scores["Contact / Lead Generation"] < 2:
        scores["Contact / Lead Generation"] += 1


def classify_website_type(context: WebsiteContext) -> tuple[str, float, str]:
    index = ContextIndex(context)
    blob = _build_signal_blob(context)
    scores = _score_types(blob)
    _structural_boost(scores, index)

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    best_type, best_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0

    if best_score == 0:
        if len(index.context.get("navigation", [])) >= 4:
            best_type = "Marketing Website"
        else:
            best_type = "Business Website"
        confidence = 0.45
        reasoning = "Limited semantic signals — classified from navigation density and page structure."
        return best_type, confidence, reasoning

    margin = best_score - second_score
    confidence = min(0.95, 0.55 + (best_score * 0.05) + (margin * 0.04))
    matched = [kw for kw in WEBSITE_TYPE_KEYWORDS.get(best_type, ()) if kw in blob][:4]
    reasoning = (
        f"Classified as {best_type} based on "
        f"{', '.join(matched) if matched else 'structural patterns'} "
        f"with navigation/forms/button signals."
    )
    return best_type, round(confidence, 2), reasoning


def classify_context(context: WebsiteContext) -> dict[str, Any]:
    website_type, confidence, reasoning = classify_website_type(context)
    return {
        "website_type": website_type,
        "business_domain": DOMAIN_BY_TYPE.get(website_type, "General Business"),
        "business_purpose": PURPOSE_BY_TYPE.get(website_type, "Present information"),
        "primary_goal": GOAL_BY_TYPE.get(website_type, "Explore the website"),
        "target_audience": AUDIENCE_BY_TYPE.get(website_type, "General visitors"),
        "confidence": confidence,
        "reasoning": reasoning,
    }
