"""Business-aware journey templates and plan conversion (Sprint 4.1)."""

from __future__ import annotations

import logging
import re

from app.services.planner.context_index import ContextIndex
from app.services.planner.display_labels import click_link_label, verify_hero_label
from app.services.planner.journey_validator import MAX_STEPS, MIN_STEPS, validate_journey
from app.services.planner.memory import PlannerMemory
from app.services.planner.navigation_graph import NavigationGraph
from app.services.planner.selector_resolver import resolve_plan_selectors
from app.services.planner.intent_classifier import IntentType, intent_from_legacy
from app.services.website_analysis.models import WebsiteAnalysis
from app.services.website_analysis.prompts import FLOW_ALIASES, JOURNEY_TEMPLATES
from app.services.website_context.json_builder import WebsiteContext

logger = logging.getLogger(__name__)


def _normalize(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value).strip())


def _step(
    action: str,
    *,
    target: str | None = None,
    selector: str | None = None,
    label: str | None = None,
    text: str | None = None,
    ms: int | None = None,
) -> dict:
    entry: dict = {"action": action}
    if target:
        entry["target"] = target
    if selector:
        entry["selector"] = selector
    if label:
        entry["label"] = label
    if text is not None:
        entry["text"] = text
    if ms is not None:
        entry["ms"] = ms
    return entry


def build_recommended_flow(website_type: str) -> list[str]:
    return list(JOURNEY_TEMPLATES.get(website_type, JOURNEY_TEMPLATES["Business Website"]))


def build_critical_journeys(website_type: str, recommended_flow: list[str]) -> list[str]:
    journeys = [f"Primary: {' → '.join(step for step in recommended_flow if step != 'Screenshot')}"]
    if website_type == "Ecommerce":
        journeys.append("Conversion: Search → Product → Cart → Checkout")
    elif website_type == "SaaS":
        journeys.append("Evaluation: Features → Pricing → Sign Up")
    elif website_type == "Hospital":
        journeys.append("Care access: Doctors → Appointment → Contact")
    elif website_type == "Portfolio":
        journeys.append("Engagement: Projects → About → Contact")
    return journeys[:3]


def _aliases_for_step(step_name: str) -> tuple[str, ...]:
    key = step_name.lower()
    if key in FLOW_ALIASES:
        return FLOW_ALIASES[key]
    return (key,)


def _find_nav_node(index: ContextIndex, graph: NavigationGraph, step_name: str):
    aliases = _aliases_for_step(step_name)
    for link in index.ranked_nav_links(exclude_logo=True):
        text = _normalize(link.get("text")).lower()
        if not text or text in {"home", "homepage"}:
            continue
        if any(alias in text for alias in aliases):
            return link
    for node in graph.navigation_nodes:
        text = _normalize(node.label).lower()
        if any(alias in text for alias in aliases):
            return {
                "text": node.label,
                "selector": node.selector,
                "href": node.href,
                "classification": node.classification,
            }
    for button in index.usable_buttons():
        text = _normalize(button.get("text")).lower()
        if any(alias in text for alias in aliases):
            return button
    return None


def _finalize(plan: list[dict]) -> list[dict]:
    body = [step for step in plan if step.get("action") != "capture"]
    if not body or body[0].get("action") != "open_page":
        body.insert(0, _step("open_page", label="Open Website"))
    if len(body) > MAX_STEPS - 1:
        body = [body[0], *body[-(MAX_STEPS - 2) :]]
    body.append(_step("capture", label="Capture Screenshot"))
    return body[:MAX_STEPS]


def build_plan_from_analysis(
    analysis: WebsiteAnalysis,
    index: ContextIndex,
    *,
    graph: NavigationGraph | None = None,
) -> list[dict]:
    """Convert a recommended business flow into executable planner steps."""
    graph = graph or NavigationGraph.from_context(index)
    memory = PlannerMemory()
    plan: list[dict] = [_step("open_page", label="Open Website")]

    if index.has_hero():
        plan.append(_step("verify_visible", target="hero", label=verify_hero_label()))
    elif index.hero_heading() and index.hero_heading().get("text"):
        heading_text = index.hero_heading()["text"]
        plan.append(_step("verify_text", text=heading_text, label=verify_hero_label(heading_text)))

    for step_name in analysis.recommended_test_flow:
        normalized = _normalize(step_name)
        if normalized.lower() in {"homepage", "screenshot", "home"}:
            continue

        node = _find_nav_node(index, graph, normalized)
        if node is None:
            continue

        selector = node.get("selector") if isinstance(node, dict) else getattr(node, "selector", None)
        label_text = node.get("text") if isinstance(node, dict) else getattr(node, "label", normalized)
        if not selector:
            continue

        if normalized.lower() in {"search", "cart", "checkout", "appointment", "login", "sign up"}:
            action = "click"
        else:
            action = "click"

        if action == "click" and not memory.can_click_link(
            selector=selector,
            label=label_text,
            href=node.get("href") if isinstance(node, dict) else getattr(node, "href", None),
            classification=node.get("classification") if isinstance(node, dict) else getattr(node, "classification", None),
        ):
            continue

        plan.append(
            _step(
                action,
                target="link" if action == "click" else "button",
                selector=selector,
                label=click_link_label(label_text),
            )
        )
        memory.record_step(plan[-1])

        if len(plan) >= MAX_STEPS - 2:
            break

    if len(plan) < MIN_STEPS - 1:
        for node in graph.primary_nav_destinations(limit=4):
            if not node.selector:
                continue
            if not memory.can_click_link(
                selector=node.selector,
                label=node.label,
                href=node.href,
                classification=node.classification,
            ):
                continue
            plan.append(
                _step(
                    "click",
                    target="link",
                    selector=node.selector,
                    label=click_link_label(node.label),
                )
            )
            memory.record_step(plan[-1])
            if len(plan) >= MIN_STEPS:
                break

    if len(plan) < MIN_STEPS - 1:
        cta = graph.cta_node
        if cta and memory.can_click_cta(selector=cta.selector, label=cta.label, classification=cta.classification):
            plan.append(
                _step(
                    "click",
                    target="button",
                    selector=cta.selector,
                    label=click_link_label(cta.label),
                )
            )

    plan.append(_step("wait", ms=800))
    return resolve_plan_selectors(_finalize(plan), index)


def try_build_analysis_journey(
    analysis: WebsiteAnalysis,
    context: WebsiteContext,
    *,
    intent: IntentType | str,
) -> list[dict] | None:
    """Build and validate a business-aware journey; return None if invalid."""
    index = ContextIndex(context)
    if isinstance(intent, str):
        resolved = intent_from_legacy(intent)
    else:
        resolved = intent

    plan = build_plan_from_analysis(analysis, index)
    if len(plan) < MIN_STEPS:
        logger.info("[WebsiteAnalysis] Analysis journey too short (%d steps)", len(plan))
        return None

    valid, reasons = validate_journey(plan, resolved, index)
    if not valid:
        logger.info("[WebsiteAnalysis] Analysis journey rejected: %s", reasons)
        return None

    logger.info(
        "[WebsiteAnalysis] Using business-aware journey for %s (%d steps)",
        analysis.website_type,
        len(plan),
    )
    return plan
