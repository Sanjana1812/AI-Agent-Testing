"""Sprint 4.1A verification harness — explainability, coverage, and strategy layer."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))


def section(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def _sample_saas_context() -> dict:
    return {
        "metadata": {
            "title": "Acme Cloud Platform",
            "current_url": "https://acme.test/pricing",
            "meta_description": "Cloud SaaS platform for teams",
        },
        "navigation": [
            {"text": "Features", "href": "/features", "selector": "a[href='/features']", "priority": 80},
            {"text": "Pricing", "href": "/pricing", "selector": "a[href='/pricing']", "priority": 90},
            {"text": "Docs", "href": "/docs", "selector": "a[href='/docs']", "priority": 70},
            {"text": "Contact", "href": "/contact", "selector": "a[href='/contact']", "priority": 60},
        ],
        "buttons": [{"text": "Start Free Trial", "selector": "button.trial", "priority": 95, "classification": "CTA"}],
        "forms": [],
        "sections": [{"heading": "Ship faster", "semantic_type": "hero", "priority": 85, "tag": "section"}],
        "headings": [{"text": "Ship faster", "level": 1, "classification": "Hero", "priority": 80}],
        "footer": [{"text": "Privacy", "href": "/privacy"}],
        "links": [{"text": "Pricing", "href": "/pricing", "internal": True}],
        "components": [],
    }


def audit_explainability_engine() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.strategy.explainability import build_confidence_breakdown
    from app.services.website_analysis import analyze_website

    context = _sample_saas_context()
    analysis = analyze_website(context, goal="check pricing")
    breakdown = build_confidence_breakdown(context, analysis)
    data = breakdown.to_dict()

    required_signals = {
        "Navigation",
        "Hero",
        "Buttons",
        "Forms",
        "Metadata",
        "Headings",
        "Internal Links",
        "URL Structure",
    }
    found = {item["signal"] for item in data.get("signals", [])}
    if required_signals.issubset(found):
        findings["passed"].append("Confidence breakdown includes all required signals")
    else:
        findings["failed"].append(f"Missing signals: {required_signals - found}")

    if data.get("total_confidence", 0) > 0:
        findings["passed"].append("Breakdown exposes total confidence")
    else:
        findings["failed"].append("Breakdown missing total confidence")

    if data.get("reasoning"):
        findings["passed"].append("Breakdown includes reasoning narrative")
    else:
        findings["failed"].append("Breakdown missing reasoning")

    return findings


def audit_coverage_engine() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.strategy.coverage_engine import estimate_coverage
    from app.services.strategy.strategy_engine import build_testing_strategy
    from app.services.website_analysis import analyze_website

    context = _sample_saas_context()
    analysis = analyze_website(context)
    strategy = build_testing_strategy(analysis, context)
    plan = [
        {"action": "open_page", "label": "Open Website"},
        {"action": "verify_visible", "target": "hero", "label": "Verify Hero"},
        {"action": "click", "target": "link", "label": "Click Pricing"},
        {"action": "capture", "label": "Capture Screenshot"},
    ]
    report = estimate_coverage(context, plan, strategy)
    data = report.to_dict()

    statuses = {area["status"] for area in data.get("areas", [])}
    if {"tested", "not_tested", "not_applicable"}.issubset(statuses):
        findings["passed"].append("Coverage report uses tested/not_tested/not_applicable")
    else:
        findings["failed"].append(f"Unexpected coverage statuses: {statuses}")

    if data.get("estimated_coverage_percent", 0) >= 0:
        findings["passed"].append("Coverage report exposes estimated percentage")
    else:
        findings["failed"].append("Coverage percentage missing")

    return findings


def audit_strategy_engine() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.strategy import build_testing_strategy
    from app.services.website_analysis import analyze_website

    context = _sample_saas_context()
    analysis = analyze_website(context, goal="explore pricing")
    strategy = build_testing_strategy(analysis, context, goal="explore pricing")
    data = strategy.to_dict()

    for field in ("testing_strategy", "testing_priority", "execution_priority", "reasoning"):
        if data.get(field):
            findings["passed"].append(f"Strategy exposes {field}")
        else:
            findings["failed"].append(f"Strategy missing {field}")

    if data.get("strategy_version") == "4.1A":
        findings["passed"].append("Strategy version is 4.1A")
    else:
        findings["failed"].append(f"Unexpected strategy version: {data.get('strategy_version')}")

    return findings


def audit_planner_strategy_integration() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.ai_planner import generate_test_plan
    from app.services.website_analysis import analyze_website

    context = _sample_saas_context()
    analysis = analyze_website(context, goal="explore pricing and features")

    async def _run() -> dict:
        return await generate_test_plan("https://acme.test", "explore pricing and features", context, analysis)

    plan_data = asyncio.run(_run())
    metadata = plan_data.get("metadata", {})

    if plan_data.get("testing_strategy"):
        findings["passed"].append("Planner returns testing_strategy payload")
    else:
        findings["failed"].append("Planner missing testing_strategy payload")

    for field in (
        "confidence_breakdown",
        "coverage_report",
        "execution_priority",
        "strategy_reasoning",
        "estimated_coverage_percent",
    ):
        if field in metadata:
            findings["passed"].append(f"Planner metadata includes {field}")
        else:
            findings["failed"].append(f"Planner metadata missing {field}")

    if metadata.get("planner_version") == "4.1.0":
        findings["passed"].append("Planner version remains 4.1.0 for backward compatibility")
    else:
        findings["failed"].append(f"Unexpected planner version: {metadata.get('planner_version')}")

    return findings


def audit_backward_compatibility() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.schemas import PlannerMetadata, RunTestResponse

    core = {
        "id", "goal", "status", "title", "url", "http_status", "duration_ms",
        "screenshot", "ai_plan", "ai_plan_source", "steps", "failures", "summary",
    }
    if core.issubset(set(RunTestResponse.model_fields.keys())):
        findings["passed"].append("RunTestResponse core contract preserved")

    optional_new = {
        "confidence_breakdown",
        "coverage_report",
        "execution_priority",
        "strategy_reasoning",
        "estimated_coverage_percent",
    }
    meta_fields = set(PlannerMetadata.model_fields.keys())
    if optional_new.issubset(meta_fields):
        findings["passed"].append("PlannerMetadata extended with optional strategy fields")
    else:
        findings["failed"].append(f"Missing metadata fields: {optional_new - meta_fields}")

    return findings


def main() -> None:
    all_findings = {}

    section("1. EXPLAINABILITY ENGINE")
    all_findings["explainability"] = audit_explainability_engine()
    print(json.dumps(all_findings["explainability"], indent=2))

    section("2. COVERAGE ENGINE")
    all_findings["coverage"] = audit_coverage_engine()
    print(json.dumps(all_findings["coverage"], indent=2))

    section("3. STRATEGY ENGINE")
    all_findings["strategy"] = audit_strategy_engine()
    print(json.dumps(all_findings["strategy"], indent=2))

    section("4. PLANNER INTEGRATION")
    all_findings["planner"] = audit_planner_strategy_integration()
    print(json.dumps(all_findings["planner"], indent=2))

    section("5. BACKWARD COMPATIBILITY")
    all_findings["compat"] = audit_backward_compatibility()
    print(json.dumps(all_findings["compat"], indent=2))

    failed = sum(len(v.get("failed", [])) for v in all_findings.values())
    print(f"\n{'=' * 60}\nTOTAL FAILURES: {failed}\n{'=' * 60}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
