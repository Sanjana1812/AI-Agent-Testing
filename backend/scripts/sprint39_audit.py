"""Sprint 3.9 verification harness for production hardening."""

from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))


def section(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def audit_modules() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    for module in (
        "app.services.planner.semantic_filter",
        "app.services.wait_strategy",
        "app.services.self_healing",
        "app.services.website_context.hero_detector",
        "app.services.website_context.components_parser",
    ):
        try:
            __import__(module)
            findings["passed"].append(f"Import OK: {module}")
        except Exception as exc:
            findings["failed"].append(f"Import failed {module}: {exc}")
    return findings


def audit_semantic_filter() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.planner.semantic_filter import filter_context, is_decorative_element, is_ignored_label

    blocked = ("Skip to content", "Privacy Policy", "Facebook", "mailto:support@test.com", "")
    for label in blocked:
        if is_ignored_label(label) or is_decorative_element({"text": label, "visible": True}):
            findings["passed"].append(f"Filtered low-value label: {label or '<empty>'}")
        else:
            findings["failed"].append(f"Should filter: {label}")

    context = filter_context(
        {
            "metadata": {},
            "navigation": [
                {"text": "Services", "href": "/services", "visible": True, "classification": "Navigation"},
                {"text": "Privacy Policy", "href": "/privacy", "visible": True, "classification": "Footer"},
                {"text": "Facebook", "href": "https://facebook.com/x", "visible": True, "classification": "Navigation"},
            ],
            "buttons": [{"text": "Get Started", "visible": True, "enabled": True, "classification": "CTA"}],
            "headings": [],
            "forms": [],
            "sections": [],
            "footer": [],
            "links": [],
            "components": [],
        }
    )
    if len(context["navigation"]) == 1 and context["navigation"][0]["text"] == "Services":
        findings["passed"].append("Semantic filter keeps meaningful business actions")
    else:
        findings["failed"].append(f"Expected 1 nav link, got {len(context['navigation'])}")
    return findings


def audit_navigation_detection() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.website_context import navigation_parser

    source = inspect.getsource(navigation_parser)
    patterns = ("#nav-main", ".topbar", ".mega-menu", "data-testid", "sticky-nav")
    for pattern in patterns:
        if pattern in source:
            findings["passed"].append(f"Navigation parser supports {pattern}")
        else:
            findings["failed"].append(f"Navigation parser missing {pattern}")
    return findings


def audit_wait_strategy() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.wait_strategy import stabilize_page, wait_before_action, wait_for_dom_ready

    for fn in (wait_for_dom_ready, stabilize_page, wait_before_action):
        findings["passed"].append(f"Wait strategy function available: {fn.__name__}")

    source = inspect.getsource(stabilize_page) + inspect.getsource(__import__("app.services.wait_strategy", fromlist=["wait_for_network_idle"]).wait_for_network_idle)
    for token in ("networkidle", "hydration", "layout"):
        if token in source.lower():
            findings["passed"].append(f"Stabilization covers {token}")
        else:
            findings["failed"].append(f"Missing stabilization for {token}")
    return findings


def audit_context_extraction() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.website_context.context_service import ContextService
    from app.services.website_context.json_builder import empty_context

    ctx = empty_context()
    if "components" in ctx:
        findings["passed"].append("WebsiteContext includes components collection")

    parsers = ContextService.PARSERS
    if "components" in parsers:
        findings["passed"].append("Components parser registered in ContextService")
    else:
        findings["failed"].append("Components parser not registered")

    import app.services.website_context.components_parser as components_module

    source = inspect.getsource(components_module)
    for component in ("search_bar", "modal", "product_grid", "carousel", "login_widget"):
        if component in source:
            findings["passed"].append(f"Extracts {component}")
        else:
            findings["failed"].append(f"Missing component type: {component}")
    return findings


def audit_selector_confidence() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.planner.selector_ranker import CONFIDENCE_BY_TYPE, MIN_CONFIDENCE_THRESHOLD, SelectorType
    from app.services.planner.selector_resolver import resolve_element
    from app.services.planner.selector_validator import is_generic_selector

    if CONFIDENCE_BY_TYPE[SelectorType.DATA_TESTID] > CONFIDENCE_BY_TYPE[SelectorType.TAG]:
        findings["passed"].append("data-testid ranked above generic tag")

    for generic in ("button", "a", "section", "div", "span", "main", "article"):
        if is_generic_selector(generic):
            findings["passed"].append(f"Generic selector rejected: {generic}")
        else:
            findings["failed"].append(f"Should reject generic selector: {generic}")

    ranked = resolve_element({"data-testid": "cta-primary", "text": "Buy Now", "tag": "button"})
    if ranked and ranked.confidence >= MIN_CONFIDENCE_THRESHOLD:
        findings["passed"].append("High-confidence selector resolved")
    else:
        findings["failed"].append("Expected high-confidence selector resolution")

    weak = resolve_element({"tag": "button"})
    if weak is None:
        findings["passed"].append("Low-confidence-only element skipped")
    else:
        findings["warnings"].append("Weak-only element still resolved")
    return findings


def audit_self_healing() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.self_healing import heal_locator, _fuzzy_match

    if _fuzzy_match("View Services", "Explore Services") >= 0.65:
        findings["passed"].append("Fuzzy text match recovers similar labels")
    else:
        findings["failed"].append("Fuzzy match should recover Explore Services from View Services")

    source = inspect.getsource(heal_locator) + inspect.getsource(__import__("app.services.self_healing", fromlist=["_candidate_selectors"])._candidate_selectors)
    for token in ("selector_alternatives", "aria-label", "role"):
        if token in source:
            findings["passed"].append(f"Self-healing tries {token}")
        else:
            findings["failed"].append(f"Self-healing missing strategy: {token}")
    return findings


def audit_hero_detection() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.planner.context_index import ContextIndex
    from app.services.website_context.hero_detector import detect_hero_section

    context = {
        "metadata": {"title": "SaaS Landing"},
        "navigation": [],
        "headings": [{"level": 2, "text": "Secondary"}],
        "buttons": [],
        "forms": [],
        "sections": [
            {"heading": "Footer Links", "semantic_type": "footer", "viewport_top": 900, "viewport_area": 1000, "priority": 10},
            {"heading": "Ship faster", "semantic_type": "general", "viewport_top": 80, "viewport_area": 120000, "priority": 50, "role": "banner"},
        ],
        "footer": [],
        "links": [],
        "components": [],
    }
    hero = detect_hero_section(context)
    if hero and hero.get("heading") == "Ship faster":
        findings["passed"].append("Hero detector prefers above-fold marketing section")
    else:
        findings["failed"].append(f"Expected 'Ship faster' hero, got {hero}")

    index = ContextIndex(context)
    if index.hero_section() and index.hero_section().get("heading") == "Ship faster":
        findings["passed"].append("ContextIndex uses intelligent hero detection")
    else:
        findings["failed"].append("ContextIndex hero_section mismatch")
    return findings


def audit_planner_safety() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.planner.context_index import ContextIndex
    from app.services.planner.intent_classifier import IntentType
    from app.services.planner.journey_builder import build_validated_journey

    context = {
        "metadata": {"title": "Demo", "current_url": "https://example.com"},
        "navigation": [
            {
                "text": "View Services",
                "href": "/services",
                "selector": "a[href='/services']",
                "internal": True,
                "priority": 90,
                "visible": True,
                "classification": "Primary Navigation",
            }
        ],
        "headings": [{"level": 1, "text": "Welcome"}],
        "buttons": [
            {
                "text": "View Services",
                "href": "/services",
                "selector": "a[href='/services']",
                "priority": 95,
                "classification": "CTA",
                "type": "cta",
                "visible": True,
                "enabled": True,
                "tag": "a",
            }
        ],
        "sections": [{"heading": "Features", "semantic_type": "features", "priority": 70, "id": "features", "tag": "section"}],
        "footer": [],
        "links": [],
        "forms": [],
        "components": [],
    }
    index = ContextIndex(context)
    plan = build_validated_journey("check the flow", IntentType.FLOW, index)
    if plan:
        findings["passed"].append("Safety-validated journey still builds for meaningful flow")
    else:
        findings["failed"].append("Journey builder returned empty plan")

    unsafe_plan = [
        {"action": "open_page", "label": "Open Website"},
        {"action": "click", "target": "link", "label": "Click Skip to content", "selector": "a.skip"},
        {"action": "verify_visible", "target": "hero", "label": "Verify Hero"},
        {"action": "capture", "label": "Capture Screenshot"},
    ]
    from app.services.planner.journey_validator import validate_journey

    valid, reasons = validate_journey(unsafe_plan, IntentType.FLOW, index)
    if not valid and any("low-value" in reason.lower() or "accessibility" in reason.lower() for reason in reasons):
        findings["passed"].append("Planner safety rejects accessibility/low-value clicks")
    else:
        findings["failed"].append(f"Expected safety rejection, got valid={valid} reasons={reasons}")
    return findings


def audit_backward_compat() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.schemas import PlanStep, RunTestResponse
    from app.services.planner.plan_metadata import PLANNER_VERSION

    if PLANNER_VERSION == "3.9.1":
        findings["passed"].append("Planner version bumped to 3.9.1")
    else:
        findings["failed"].append(f"Expected planner version 3.9.1, got {PLANNER_VERSION}")

    required = {"id", "goal", "status", "ai_plan", "ai_plan_source", "steps", "failures", "summary"}
    if required.issubset(set(RunTestResponse.model_fields.keys())):
        findings["passed"].append("RunTestResponse core schema unchanged")

    step_fields = set(PlanStep.model_fields.keys())
    if "selector_alternatives" in step_fields:
        findings["passed"].append("Optional selector_alternatives field added")

    source = inspect.getsource(__import__("app.services.playwright_runner", fromlist=["_execute_sync"])._execute_sync)
    if "for index, action in enumerate(plan" in source:
        findings["passed"].append("Playwright execution loop architecture preserved")
    else:
        findings["failed"].append("Playwright execution loop changed")
    return findings


def main() -> None:
    all_findings = {}

    section("1. MODULE IMPORTS")
    all_findings["modules"] = audit_modules()
    print(json.dumps(all_findings["modules"], indent=2))

    section("2. SEMANTIC FILTERING")
    all_findings["semantic"] = audit_semantic_filter()
    print(json.dumps(all_findings["semantic"], indent=2))

    section("3. NAVIGATION DETECTION")
    all_findings["navigation"] = audit_navigation_detection()
    print(json.dumps(all_findings["navigation"], indent=2))

    section("4. WAIT STRATEGY")
    all_findings["wait"] = audit_wait_strategy()
    print(json.dumps(all_findings["wait"], indent=2))

    section("5. CONTEXT EXTRACTION")
    all_findings["context"] = audit_context_extraction()
    print(json.dumps(all_findings["context"], indent=2))

    section("6. SELECTOR CONFIDENCE")
    all_findings["selectors"] = audit_selector_confidence()
    print(json.dumps(all_findings["selectors"], indent=2))

    section("7. SELF-HEALING")
    all_findings["healing"] = audit_self_healing()
    print(json.dumps(all_findings["healing"], indent=2))

    section("8. HERO DETECTION")
    all_findings["hero"] = audit_hero_detection()
    print(json.dumps(all_findings["hero"], indent=2))

    section("9. PLANNER SAFETY")
    all_findings["safety"] = audit_planner_safety()
    print(json.dumps(all_findings["safety"], indent=2))

    section("10. BACKWARD COMPATIBILITY")
    all_findings["compat"] = audit_backward_compat()
    print(json.dumps(all_findings["compat"], indent=2))

    failed = sum(len(v.get("failed", [])) for v in all_findings.values())
    print(f"\n{'=' * 60}\nTOTAL FAILURES: {failed}\n{'=' * 60}")


if __name__ == "__main__":
    main()
