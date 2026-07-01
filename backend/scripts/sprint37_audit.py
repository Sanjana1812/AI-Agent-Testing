"""Sprint 3.7 verification harness for selector resolution engine."""

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
    for module in (
        "app.services.planner.selector_ranker",
        "app.services.planner.selector_validator",
        "app.services.planner.selector_resolver",
    ):
        try:
            __import__(module)
            findings["passed"].append(f"Import OK: {module}")
        except Exception as exc:
            findings["failed"].append(f"Import failed {module}: {exc}")
    return findings


def audit_selector_ranker() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.planner.selector_ranker import CONFIDENCE_BY_TYPE, SelectorType
    from app.services.planner.selector_resolver import build_candidates as resolver_candidates

    if CONFIDENCE_BY_TYPE[SelectorType.DATA_TESTID] == 100 and CONFIDENCE_BY_TYPE[SelectorType.TAG] == 20:
        findings["passed"].append("Confidence scores configured")

    ranked = resolver_candidates(
        {
            "data-testid": "cta-primary",
            "id": "cta",
            "href": "/services",
            "text": "View Services",
            "selector": "button",
            "tag": "button",
        }
    )
    if ranked and ranked[0].selector == '[data-testid="cta-primary"]':
        findings["passed"].append("Highest-confidence selector chosen first")
    else:
        findings["failed"].append(f"Expected data-testid first, got {ranked[0].selector if ranked else None}")
    return findings


def audit_selector_validator() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.planner.selector_validator import is_generic_selector, validate_selector

    for generic in ("button", "a", "section", "form", "footer", "nav, [role='navigation']"):
        if is_generic_selector(generic):
            findings["passed"].append(f"Generic rejected: {generic}")
        else:
            findings["failed"].append(f"Should reject generic selector: {generic}")

    valid, _ = validate_selector("a[href='/services']")
    if valid:
        findings["passed"].append("Specific selector accepted")
    else:
        findings["failed"].append("Specific selector should be accepted")

    used = {"a[href='/services']"}
    valid_dup, reason = validate_selector("a[href='/services']", used_selectors=used)
    if not valid_dup and reason:
        findings["passed"].append("Duplicate selector rejected")
    return findings


def audit_plan_resolution() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.planner.context_index import ContextIndex
    from app.services.planner.intent_classifier import IntentType
    from app.services.planner.journey_builder import build_validated_journey
    from app.services.planner.memory import PlannerMemory
    from app.services.planner.selector_validator import is_generic_selector

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
    }
    index = ContextIndex(context)
    plan = build_validated_journey("check the flow", IntentType.FLOW, index)

    click_steps = [step for step in plan if step.get("action") == "click"]
    if click_steps and all(step.get("selector") for step in click_steps):
        findings["passed"].append("Every click has a resolved selector")
    else:
        findings["failed"].append("Click steps missing resolved selectors")

    if not any(is_generic_selector(step.get("selector")) for step in click_steps):
        findings["passed"].append("No click uses generic selector")
    else:
        findings["failed"].append("Generic selector found on click step")

    selectors = [step.get("selector", "").lower() for step in plan if step.get("selector")]
    if len(selectors) == len(set(selectors)):
        findings["passed"].append("Duplicate selectors prevented in resolved plan")
    else:
        findings["warnings"].append("Duplicate selectors present after resolution")

    memory = PlannerMemory()
    first_click = click_steps[0]
    if not memory.can_use_selector(first_click.get("selector"), action="click"):
        findings["failed"].append("Memory should allow first selector use")
    memory.record_step(first_click)
    if memory.can_use_selector(first_click.get("selector"), action="click"):
        findings["failed"].append("Memory should block repeated selector click")
    else:
        findings["passed"].append("Planner memory tracks selectors")

    if any(step.get("selector_confidence") for step in click_steps):
        findings["passed"].append("Selector confidence metadata attached")
    return findings


def audit_backward_compat() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.schemas import PlanStep, RunTestResponse

    step_fields = set(PlanStep.model_fields.keys())
    if {"selector_strategy", "selector_confidence", "selector_type"}.issubset(step_fields):
        findings["passed"].append("Optional selector metadata fields added to PlanStep")

    required = {"id", "goal", "status", "ai_plan", "ai_plan_source", "steps", "failures", "summary"}
    if required.issubset(set(RunTestResponse.model_fields.keys())):
        findings["passed"].append("RunTestResponse core schema unchanged")

    import inspect
    from app.services.playwright_runner import _execute_sync

    source = inspect.getsource(_execute_sync)
    if "selector_resolver" not in source and "SelectorResolver" not in source:
        findings["passed"].append("Playwright runner untouched")
    else:
        findings["failed"].append("Playwright runner references selector resolver")
    return findings


def main() -> None:
    all_findings = {}

    section("1. MODULE IMPORTS")
    all_findings["modules"] = audit_modules()
    print(json.dumps(all_findings["modules"], indent=2))

    section("2. SELECTOR RANKER")
    all_findings["ranker"] = audit_selector_ranker()
    print(json.dumps(all_findings["ranker"], indent=2))

    section("3. SELECTOR VALIDATOR")
    all_findings["validator"] = audit_selector_validator()
    print(json.dumps(all_findings["validator"], indent=2))

    section("4. PLAN RESOLUTION")
    all_findings["plan"] = audit_plan_resolution()
    print(json.dumps(all_findings["plan"], indent=2))

    section("5. BACKWARD COMPATIBILITY")
    all_findings["compat"] = audit_backward_compat()
    print(json.dumps(all_findings["compat"], indent=2))

    failed = sum(len(v.get("failed", [])) for v in all_findings.values())
    print(f"\n{'=' * 60}\nTOTAL FAILURES: {failed}\n{'=' * 60}")


if __name__ == "__main__":
    main()
