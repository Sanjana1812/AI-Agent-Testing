"""Presentation-layer polish for planner output — no planning logic changes."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from app.services.planner.context_index import ContextIndex
from app.services.planner.semantic_filter import is_ignored_label
from app.services.website_context.json_builder import WebsiteContext

GENERIC_LABELS = frozenset(
    {
        "open website",
        "open page",
        "click link",
        "click button",
        "verify section",
        "verify main content",
        "verify hero section",
        "verify element visible",
        "capture screenshot",
        "scroll page",
    }
)

WEBSITE_TYPE_HINTS = (
    ("login", "Authentication Portal"),
    ("signup", "Registration Portal"),
    ("pricing", "Pricing / SaaS Website"),
    ("contact", "Contact / Lead Generation Website"),
    ("shop", "E-Commerce Website"),
    ("cart", "E-Commerce Website"),
    ("dashboard", "Application Dashboard"),
    ("docs", "Documentation Website"),
    ("blog", "Content / Blog Website"),
)


def _normalize(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value).strip())


def is_generic_label(label: str | None) -> bool:
    normalized = _normalize(label).lower()
    if not normalized:
        return True
    if normalized in GENERIC_LABELS:
        return True
    if normalized in {"click link", "verify section", "click button"}:
        return True
    return False


def sanitize_hero_label(label: str | None) -> str | None:
    if not label:
        return label
    match = re.search(r'"([^"]+)"', label)
    hero_text = match.group(1) if match else label
    if is_ignored_label(hero_text) or hero_text.lower().startswith("skip"):
        return None
    if match:
        return f'Verify Hero "{hero_text}"'
    if "hero" in label.lower():
        return label
    return label


def _page_name_from_url(url: str | None) -> str:
    if not url:
        return "Page"
    path = urlparse(url).path.rstrip("/") or "/"
    if path == "/":
        return "Homepage"
    segment = path.split("/")[-1].replace("-", " ").replace("_", " ").title()
    return f"{segment} Page"


def humanize_step_label(step: dict, *, default_page_name: str = "Homepage") -> str:
    if step.get("label") and not is_generic_label(step["label"]):
        label = str(step["label"])
        if step.get("target") == "hero" or "hero" in label.lower():
            sanitized = sanitize_hero_label(label)
            if sanitized:
                return sanitized
        return label

    action = step.get("action", "")
    target = step.get("target")
    text = step.get("text")
    href = step.get("href")

    if action == "open_page":
        return f"Open {default_page_name}"
    if action == "capture":
        return "Capture Final Screenshot"
    if action == "wait":
        return f"Wait {step.get('ms', 1000)}ms for Page Stabilization"
    if action == "click":
        if text:
            return f'Click "{text}"'
        if step.get("label") and '"' in str(step["label"]):
            return str(step["label"])
        if href:
            name = _page_name_from_url(href)
            return f'Navigate to {name}'
        return "Click Primary Action"
    if action == "verify_visible":
        if target == "hero":
            if text:
                return f'Verify Hero "{text}"'
            return f"Verify {default_page_name} Hero"
        if target == "footer":
            return "Verify Footer"
        if target == "form":
            return "Verify Contact Form"
        if target == "navigation":
            return "Verify Navigation Bar"
        if text:
            return f'Verify "{text}" Visible'
        return "Verify Page Content Loaded"
    if action == "verify_text" and text:
        return f'Verify Text "{text}"'
    if action == "verify_form":
        return "Verify Form Fields"
    if action == "scroll":
        return "Scroll to Main Content"
    if action == "fill" and text:
        return f'Fill "{text}"'
    return _normalize(step.get("label")) or action.replace("_", " ").title()


def polish_plan_labels(plan: list[dict], *, base_url: str | None = None) -> list[dict]:
    polished: list[dict] = []
    current_page = _page_name_from_url(base_url)
    for step in plan:
        entry = dict(step)
        if step.get("context_url"):
            current_page = _page_name_from_url(step["context_url"])
        label = humanize_step_label(entry, default_page_name=current_page)
        if step.get("target") == "hero" or (
            step.get("action") in {"verify_visible", "verify_text"} and "hero" in label.lower()
        ):
            sanitized = sanitize_hero_label(label)
            if sanitized:
                label = sanitized
            else:
                label = f"Verify {current_page} Loaded"
        entry["label"] = label
        polished.append(entry)
    return polished


def compute_planner_confidence(plan: list[dict], *, validation_score: float) -> tuple[float, str]:
    selector_scores = [
        float(step["selector_confidence"])
        for step in plan
        if step.get("selector_confidence") is not None
    ]
    if selector_scores:
        selector_avg = sum(selector_scores) / len(selector_scores)
        combined = round((validation_score * 0.4) + (selector_avg * 0.6), 1)
    else:
        combined = round(float(validation_score), 1)

    if combined >= 90:
        return combined, "High Confidence"
    if combined >= 75:
        return combined, "Medium Confidence"
    return combined, "Low Confidence"


def detect_website_type(context: WebsiteContext, intent: str | None = None) -> str:
    metadata = context.get("metadata", {})
    title = _normalize(metadata.get("title")).lower()
    blob = title
    for nav in context.get("navigation", [])[:8]:
        blob += " " + _normalize(nav.get("text")).lower()
    if intent:
        blob += f" {intent.lower()}"

    for keyword, label in WEBSITE_TYPE_HINTS:
        if keyword in blob:
            return label

    if context.get("forms") and any(f.get("classification") == "Login" for f in context.get("forms", [])):
        return "Authentication Portal"
    if len(context.get("navigation", [])) >= 4:
        return "Marketing Website"
    return "Business Website"


def build_primary_navigation(context: WebsiteContext, *, limit: int = 4) -> list[str]:
    index = ContextIndex(context)
    labels: list[str] = []
    for link in index.ranked_nav_links(exclude_logo=True):
        text = _normalize(link.get("text"))
        if not text or is_ignored_label(text):
            continue
        if text not in labels:
            labels.append(text.title() if text.islower() else text)
        if len(labels) >= limit:
            break
    return labels


def build_journey_summary(plan: list[dict], *, base_url: str | None = None) -> list[str]:
    journey: list[str] = [_page_name_from_url(base_url) or "Homepage"]
    for step in plan:
        if step.get("action") != "click":
            continue
        label = humanize_step_label(step)
        match = re.search(r'"([^"]+)"', label)
        if match:
            journey.append(match.group(1))
        elif step.get("href"):
            journey.append(_page_name_from_url(step["href"]))
    if plan and plan[-1].get("action") == "capture":
        journey.append("Screenshot")
    return journey


def build_planner_reasoning(
    *,
    context: WebsiteContext,
    intent: str,
    plan: list[dict],
    base_url: str | None = None,
    planner_strategy: str,
) -> dict[str, Any]:
    return {
        "detected_website_type": detect_website_type(context, intent),
        "detected_intent": intent.replace("_", " ").title(),
        "primary_navigation": build_primary_navigation(context),
        "planner_strategy": planner_strategy,
        "generated_journey": build_journey_summary(plan, base_url=base_url),
    }


def build_website_analysis(context: WebsiteContext, *, context_extracted: bool | None = None) -> dict[str, Any]:
    index = ContextIndex(context)
    hero_sections = len(index.ranked_sections(semantic_type="hero"))
    extracted = context_extracted if context_extracted is not None else bool(
        len(context.get("navigation", []))
        + len(index.usable_buttons())
        + len(context.get("forms", []))
        + len(context.get("sections", []))
    )
    return {
        "context_extracted": extracted,
        "pages_crawled": 1 if extracted else 0,
        "navigation_links": len(context.get("navigation", [])),
        "buttons": len(index.usable_buttons()),
        "forms": len(context.get("forms", [])),
        "sections": len(context.get("sections", [])),
        "detected_components": len(context.get("components", [])),
        "hero_sections": hero_sections or (1 if index.has_hero() else 0),
        "context_version": "2.1",
        "page_title": context.get("metadata", {}).get("title", ""),
        "extraction_error": context.get("metadata", {}).get("extraction_error"),
        "target_url": context.get("metadata", {}).get("current_url"),
    }


def normalize_planner_source(source: str) -> str:
    lowered = source.lower()
    if lowered in {"fallback", "minimal_fallback"}:
        return "fallback"
    if lowered in {"semantic_planner", "journey_builder", "planner"}:
        return "semantic_planner"
    return source


def planner_source_display(source: str) -> str:
    normalized = normalize_planner_source(source)
    if normalized == "fallback":
        return "Fallback"
    return "AI Planner"


def is_minimal_fallback_plan(plan: list[dict]) -> bool:
    if len(plan) > 6:
        return False
    if any(step.get("action") == "click" for step in plan):
        return False
    return any(step.get("action") == "wait" and step.get("ms") == 800 for step in plan)
