"""Sprint 3.9.1 verification harness for production UX polish."""

from __future__ import annotations

import asyncio
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
        "app.services.planner.plan_presentation",
        "app.services.failures.failure_messages",
    ):
        try:
            __import__(module)
            findings["passed"].append(f"Import OK: {module}")
        except Exception as exc:
            findings["failed"].append(f"Import failed {module}: {exc}")
    return findings


def audit_planner_source() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.planner.plan_presentation import normalize_planner_source, planner_source_display

    if normalize_planner_source("semantic_planner") == "semantic_planner":
        findings["passed"].append("Semantic planner source normalized")
    else:
        findings["failed"].append("Semantic planner source normalization failed")

    if planner_source_display("semantic_planner") == "AI Planner":
        findings["passed"].append("Semantic planner displays as AI Planner")
    else:
        findings["failed"].append("Semantic planner should display as AI Planner")

    if planner_source_display("fallback") == "Fallback":
        findings["passed"].append("Fallback displays only for fallback source")
    else:
        findings["failed"].append("Fallback label incorrect")
    return findings


def audit_human_readable_steps() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.planner.plan_presentation import humanize_step_label, is_generic_label, polish_plan_labels

    label = humanize_step_label({"action": "click", "text": "Pricing", "target": "link"})
    if "Pricing" in label and not is_generic_label(label):
        findings["passed"].append("Click step uses destination label")

    hero = humanize_step_label(
        {"action": "verify_visible", "target": "hero", "label": 'Verify Hero Section "Skip to"'},
        default_page_name="Homepage",
    )
    polished = polish_plan_labels(
        [{"action": "verify_visible", "target": "hero", "label": 'Verify Hero Section "Skip to"'}],
        base_url="https://example.com",
    )
    if polished[0]["label"] and "Skip to" not in polished[0]["label"]:
        findings["passed"].append("Accessibility hero labels sanitized")
    else:
        findings["failed"].append(f"Hero label should not include skip links: {polished[0]['label']}")

    plan = polish_plan_labels(
        [
            {"action": "open_page"},
            {"action": "click", "text": "Features", "target": "link", "href": "/features"},
            {"action": "verify_visible", "target": "hero", "label": 'Verify Hero "Features"'},
            {"action": "capture"},
        ],
        base_url="https://github.com",
    )
    if all(not is_generic_label(step["label"]) or step["action"] == "capture" for step in plan):
        findings["passed"].append("Polished plan avoids generic labels")
    else:
        findings["failed"].append("Generic labels remain in polished plan")
    return findings


def audit_planner_confidence() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.planner.plan_metadata import PLANNER_VERSION, build_plan_metadata
    from app.services.planner.plan_presentation import compute_planner_confidence

    confidence, label = compute_planner_confidence(
        [{"selector_confidence": 95}, {"selector_confidence": 90}],
        validation_score=92,
    )
    if confidence >= 90 and label == "High Confidence":
        findings["passed"].append("Planner confidence computed from selector scores")
    else:
        findings["failed"].append(f"Unexpected confidence: {confidence} {label}")

    metadata = build_plan_metadata(
        planner_source="semantic_planner",
        planning_time_ms=10,
        validation_score=90,
        planner_confidence=confidence,
        planner_confidence_label=label,
    )
    if metadata.get("planner_confidence") and metadata.get("planner_version") == "4.1.0":
        findings["passed"].append("Planner metadata exposes confidence")
    else:
        findings["failed"].append("Planner metadata missing confidence fields")
    return findings


def audit_reasoning_and_website_summary() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.planner.plan_presentation import build_planner_reasoning, build_website_analysis
    from app.services.website_context.json_builder import empty_context

    context = empty_context()
    context["metadata"] = {"title": "Acme Pricing"}
    context["navigation"] = [
        {"text": "Pricing", "href": "/pricing", "visible": True, "classification": "Navigation", "priority": 90},
        {"text": "Features", "href": "/features", "visible": True, "classification": "Navigation", "priority": 85},
    ]
    context["sections"] = [{"heading": "Plans", "semantic_type": "pricing", "priority": 80}]
    plan = [
        {"action": "open_page"},
        {"action": "click", "text": "Pricing", "href": "/pricing"},
        {"action": "capture"},
    ]

    reasoning = build_planner_reasoning(
        context=context,
        intent="navigation",
        plan=plan,
        base_url="https://acme.test",
        planner_strategy="Semantic Journey Builder",
    )
    if reasoning.get("primary_navigation") and reasoning.get("generated_journey"):
        findings["passed"].append("Planner reasoning metadata generated")
    else:
        findings["failed"].append("Planner reasoning metadata incomplete")

    analysis = build_website_analysis(context)
    for key in ("navigation_links", "sections", "context_version", "hero_sections"):
        if key in analysis:
            findings["passed"].append(f"Website analysis includes {key}")
        else:
            findings["failed"].append(f"Website analysis missing {key}")
    return findings


def audit_failure_messages() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.failures.failure_enricher import enrich_failures
    from app.services.failures.failure_messages import humanize_failure_message

    message = humanize_failure_message(
        {"type": "element_not_found", "target": "link", "expected_element": "Click Pricing"},
    )
    if "navigation element" in message.lower():
        findings["passed"].append("Failure message humanized for missing navigation")
    else:
        findings["failed"].append(f"Unexpected failure message: {message}")

    result = {
        "url": "https://example.com",
        "title": "Example",
        "ai_plan_source": "semantic_planner",
        "ai_plan": [{"action": "click", "label": 'Click "Pricing"', "target": "link"}],
        "steps": [{"id": "1", "status": "failed", "assertions": []}],
        "failures": [
            {
                "type": "timeout",
                "message": "Timed out while executing 'click:Pricing'.",
                "severity": "medium",
                "expected_element": 'Click "Pricing"',
            }
        ],
    }
    enriched = enrich_failures(result, {"navigation_links": 2})
    if enriched and enriched[0].get("user_message"):
        findings["passed"].append("Failure enricher attaches user_message")
    else:
        findings["failed"].append("Failure enricher missing user_message")
    return findings


def audit_schema_compat() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.schemas import ExecutionFailure, PlannerMetadata, RunTestResponse

    if "user_message" in ExecutionFailure.model_fields:
        findings["passed"].append("ExecutionFailure supports user_message")
    else:
        findings["failed"].append("ExecutionFailure missing user_message")

    meta_fields = PlannerMetadata.model_fields
    for field in ("planner_confidence", "detected_website_type", "generated_journey"):
        if field in meta_fields:
            findings["passed"].append(f"PlannerMetadata includes {field}")
        else:
            findings["failed"].append(f"PlannerMetadata missing {field}")

    if "website_context_summary" in RunTestResponse.model_fields:
        findings["passed"].append("RunTestResponse exposes website_context_summary")
    else:
        findings["failed"].append("RunTestResponse missing website_context_summary")

    required = {"id", "goal", "status", "ai_plan", "ai_plan_source", "steps", "failures", "summary"}
    if required.issubset(set(RunTestResponse.model_fields.keys())):
        findings["passed"].append("RunTestResponse core schema unchanged")
    return findings


def audit_generate_test_plan() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.ai_planner import generate_test_plan

    context = {
        "metadata": {"title": "Demo Site", "current_url": "https://demo.test"},
        "navigation": [
            {
                "text": "Pricing",
                "href": "/pricing",
                "selector": 'a[href="/pricing"]',
                "visible": True,
                "classification": "Navigation",
                "priority": 90,
            }
        ],
        "headings": [{"level": 1, "text": "Welcome"}],
        "buttons": [
            {
                "text": "Pricing",
                "href": "/pricing",
                "selector": 'a[href="/pricing"]',
                "priority": 95,
                "classification": "CTA",
                "type": "cta",
                "visible": True,
                "enabled": True,
                "tag": "a",
            }
        ],
        "sections": [{"heading": "Features", "semantic_type": "features", "priority": 70, "tag": "section"}],
        "footer": [],
        "links": [],
        "forms": [],
        "components": [],
    }

    data = asyncio.run(generate_test_plan("https://demo.test", "check the flow", context))
    if data.get("source") != "fallback":
        findings["passed"].append("Successful semantic plan no longer labeled fallback")
    else:
        findings["failed"].append("Semantic planner still returns fallback source")

    labels = [step.get("label", "") for step in data.get("plan", [])]
    if labels and all("Click Link" not in label for label in labels):
        findings["passed"].append("Generated plan uses readable labels")
    else:
        findings["failed"].append(f"Generic labels found: {labels}")

    metadata = data.get("metadata", {})
    if metadata.get("planner_confidence") and metadata.get("generated_journey"):
        findings["passed"].append("generate_test_plan attaches presentation metadata")
    else:
        findings["failed"].append("Presentation metadata missing from generate_test_plan")
    return findings


def main() -> None:
    all_findings = {}

    section("1. MODULE IMPORTS")
    all_findings["modules"] = audit_modules()
    print(json.dumps(all_findings["modules"], indent=2))

    section("2. PLANNER SOURCE LABELS")
    all_findings["source"] = audit_planner_source()
    print(json.dumps(all_findings["source"], indent=2))

    section("3. HUMAN-READABLE STEPS")
    all_findings["steps"] = audit_human_readable_steps()
    print(json.dumps(all_findings["steps"], indent=2))

    section("4. PLANNER CONFIDENCE")
    all_findings["confidence"] = audit_planner_confidence()
    print(json.dumps(all_findings["confidence"], indent=2))

    section("5. REASONING & WEBSITE SUMMARY")
    all_findings["reasoning"] = audit_reasoning_and_website_summary()
    print(json.dumps(all_findings["reasoning"], indent=2))

    section("6. FAILURE REPORTING")
    all_findings["failures"] = audit_failure_messages()
    print(json.dumps(all_findings["failures"], indent=2))

    section("7. SCHEMA COMPATIBILITY")
    all_findings["schema"] = audit_schema_compat()
    print(json.dumps(all_findings["schema"], indent=2))

    section("8. GENERATE TEST PLAN")
    all_findings["planner"] = audit_generate_test_plan()
    print(json.dumps(all_findings["planner"], indent=2))

    failed = sum(len(v.get("failed", [])) for v in all_findings.values())
    print(f"\n{'=' * 60}\nTOTAL FAILURES: {failed}\n{'=' * 60}")


if __name__ == "__main__":
    main()
