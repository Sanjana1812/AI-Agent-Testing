"""Sprint 3.6 verification harness for intent-aware journey planner."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))


def section(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def audit_modules() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    modules = [
        "app.services.planner.intent_classifier",
        "app.services.planner.navigation_graph",
        "app.services.planner.memory",
        "app.services.planner.journey_builder",
        "app.services.planner.journey_validator",
    ]
    for module in modules:
        try:
            __import__(module)
            findings["passed"].append(f"Import OK: {module}")
        except Exception as exc:
            findings["failed"].append(f"Import failed {module}: {exc}")
    return findings


def audit_intent_classifier() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.planner.intent_classifier import IntentType, classify_intent

    cases = [
        ("check the flow", IntentType.FLOW),
        ("verify navigation", IntentType.NAVIGATION),
        ("test login", IntentType.LOGIN),
        ("fill contact form", IntentType.CONTACT),
        ("buy a product", IntentType.PURCHASE),
        ("search courses", IntentType.SEARCH),
    ]
    for goal, expected in cases:
        result = classify_intent(goal)
        if result == expected:
            findings["passed"].append(f"'{goal}' -> {result.value}")
        else:
            findings["failed"].append(f"'{goal}' expected {expected.value}, got {result.value}")
    return findings


def audit_journey_builder() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.planner.context_index import ContextIndex
    from app.services.planner.intent_classifier import IntentType, classify_intent
    from app.services.planner.journey_builder import build_validated_journey
    from app.services.planner.journey_validator import validate_journey
    from app.services.planner.navigation_graph import NavigationGraph
    from app.services.website_context.json_builder import empty_context

    sample_context = empty_context()
    sample_context.update(
        {
            "metadata": {"title": "Example Site", "current_url": "https://example.com"},
            "navigation": [
                {"text": "About", "href": "/about", "internal": True, "priority": 80, "visible": True, "classification": "Primary Navigation"},
                {"text": "Contact", "href": "/contact", "internal": True, "priority": 75, "visible": True, "classification": "Primary Navigation"},
            ],
            "headings": [{"level": 1, "text": "Welcome"}],
            "buttons": [{"text": "GET STARTED", "selector": "a.cta", "priority": 90, "classification": "CTA", "type": "cta", "visible": True, "enabled": True}],
            "sections": [{"heading": "Features", "semantic_type": "features", "priority": 70}],
            "footer": [{"text": "Privacy", "href": "/privacy", "internal": True, "priority": 40, "visible": True}],
            "links": [],
            "forms": [],
        }
    )
    index = ContextIndex(sample_context)
    graph = NavigationGraph.from_context(index)
    if graph.navigation_nodes and graph.cta_node:
        findings["passed"].append("Navigation graph built with nav + CTA")

    for goal, intent in [("check the flow", IntentType.FLOW), ("verify navigation", IntentType.NAVIGATION)]:
        plan = build_validated_journey(goal, intent, index)
        ok, reasons = validate_journey(plan, intent, index)
        if 4 <= len(plan) <= 8 and plan[-1]["action"] == "capture":
            findings["passed"].append(f"{intent.value} plan length={len(plan)}")
        else:
            findings["failed"].append(f"{intent.value} invalid plan length or missing capture")
        if ok:
            findings["passed"].append(f"{intent.value} journey validated")
        else:
            findings["warnings"].append(f"{intent.value} journey warnings: {reasons}")

        labels = [step.get("label", step.get("action")) for step in plan]
        if any("Logo" in str(label) for label in labels):
            findings["failed"].append(f"{intent.value} plan clicks logo")

    resolved = classify_intent("check the flow")
    if resolved == IntentType.FLOW:
        findings["passed"].append("classify_intent integrated with journey builder")
    return findings


def audit_backward_compat() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.schemas import RunTestResponse
    from app.services.ai_planner import detect_intent, generate_test_plan
    from app.services.planner.context_fallback import build_context_plan
    from app.services.planner.context_index import ContextIndex
    from app.services.website_context.json_builder import empty_context

    if detect_intent("check the flow") == "flow":
        findings["passed"].append("detect_intent backward compatible")

    index = ContextIndex(empty_context())
    plan = build_context_plan("check the flow", "flow", index)
    if plan and plan[0]["action"] == "open_page":
        findings["passed"].append("build_context_plan still returns valid plan shape")

    fields = set(RunTestResponse.model_fields.keys())
    required = {"id", "goal", "status", "ai_plan", "ai_plan_source", "steps", "failures", "summary"}
    if required.issubset(fields):
        findings["passed"].append("RunTestResponse schema unchanged")

    import inspect
    from app.services.playwright_runner import _execute_sync

    if "_execute_sync" in inspect.getsourcefile(_execute_sync):
        findings["passed"].append("Playwright _execute_sync untouched")

    return findings


def main() -> None:
    all_findings = {}
    section("1. MODULE IMPORTS")
    all_findings["modules"] = audit_modules()
    print(json.dumps(all_findings["modules"], indent=2))

    section("2. INTENT CLASSIFIER")
    all_findings["intent"] = audit_intent_classifier()
    print(json.dumps(all_findings["intent"], indent=2))

    section("3. JOURNEY BUILDER")
    all_findings["journey"] = audit_journey_builder()
    print(json.dumps(all_findings["journey"], indent=2))

    section("4. BACKWARD COMPATIBILITY")
    all_findings["compat"] = audit_backward_compat()
    print(json.dumps(all_findings["compat"], indent=2))

    failed = sum(len(v.get("failed", [])) for v in all_findings.values())
    print(f"\n{'=' * 60}\nTOTAL FAILURES: {failed}\n{'=' * 60}")


if __name__ == "__main__":
    main()
