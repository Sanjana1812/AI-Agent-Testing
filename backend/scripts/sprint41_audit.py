"""Sprint 4.1 verification harness — AI Website Analysis & Journey Planning."""

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
        "metadata": {"title": "Acme Cloud Platform", "current_url": "https://acme.test"},
        "navigation": [
            {"text": "Features", "href": "/features", "selector": "a[href='/features']", "priority": 80},
            {"text": "Pricing", "href": "/pricing", "selector": "a[href='/pricing']", "priority": 90},
            {"text": "Docs", "href": "/docs", "selector": "a[href='/docs']", "priority": 70},
            {"text": "Contact", "href": "/contact", "selector": "a[href='/contact']", "priority": 60},
        ],
        "buttons": [{"text": "Start Free Trial", "selector": "button.trial", "priority": 95, "classification": "CTA"}],
        "forms": [],
        "sections": [{"heading": "Ship faster", "semantic_type": "hero", "priority": 85}],
        "headings": [{"text": "Ship faster", "level": 1}],
        "footer": [],
        "links": [],
        "components": [],
    }


def audit_website_analysis_engine() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.website_analysis import WebsiteAnalysis, analyze_website
    from app.services.website_analysis.classifier import classify_website_type
    from app.services.website_analysis.risk_engine import compute_high_risk_areas, compute_testing_priority

    context = _sample_saas_context()
    analysis = analyze_website(context, goal="check pricing flow")

    required = {
        "website_type",
        "business_domain",
        "business_purpose",
        "primary_goal",
        "target_audience",
        "critical_user_journeys",
        "recommended_test_flow",
        "high_risk_areas",
        "testing_priority",
        "confidence",
        "reasoning",
    }
    data = analysis.to_dict()
    if required.issubset(data.keys()):
        findings["passed"].append("WebsiteAnalysis model contains all required fields")
    else:
        findings["failed"].append(f"Missing analysis fields: {required - set(data.keys())}")

    if analysis.website_type == "SaaS":
        findings["passed"].append("SaaS website classified correctly")
    else:
        findings["failed"].append(f"Expected SaaS classification, got {analysis.website_type}")

    if "Pricing" in analysis.testing_priority:
        findings["passed"].append("Risk engine prioritizes pricing for SaaS")
    else:
        findings["failed"].append(f"SaaS testing priority unexpected: {analysis.testing_priority}")

    if "Screenshot" in analysis.recommended_test_flow:
        findings["passed"].append("Recommended flow ends with screenshot step")
    else:
        findings["failed"].append("Recommended flow missing screenshot")

    hospital_blob_context = {
        "metadata": {"title": "City Hospital", "current_url": "https://hospital.test"},
        "navigation": [
            {"text": "Doctors", "href": "/doctors", "selector": "a.doctors", "priority": 80},
            {"text": "Appointment", "href": "/appointment", "selector": "a.appt", "priority": 90},
        ],
        "buttons": [],
        "forms": [],
        "sections": [],
        "headings": [],
        "footer": [],
        "links": [],
        "components": [],
    }
    hospital_type, _, _ = classify_website_type(hospital_blob_context)
    if hospital_type == "Hospital":
        findings["passed"].append("Hospital website classified correctly")
    else:
        findings["failed"].append(f"Expected Hospital, got {hospital_type}")

    from app.services.website_context.json_builder import empty_context

    empty_analysis = analyze_website(empty_context())
    if empty_analysis.website_type == "Unknown" and empty_analysis.confidence == 0.0:
        findings["passed"].append("Empty context yields honest Unknown analysis")
    else:
        findings["failed"].append(
            f"Empty context should be Unknown/0.0, got {empty_analysis.website_type}/{empty_analysis.confidence}"
        )

    risks = compute_high_risk_areas("Ecommerce")
    if "Checkout payment" in risks:
        findings["passed"].append("Ecommerce high-risk areas generated")
    else:
        findings["failed"].append("Ecommerce risk areas missing checkout")

    if isinstance(analysis, WebsiteAnalysis):
        findings["passed"].append("Strongly typed WebsiteAnalysis returned")

    return findings


def audit_planner_integration() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.ai_planner import generate_test_plan
    from app.services.website_analysis import analyze_website

    context = _sample_saas_context()
    analysis = analyze_website(context, goal="explore pricing and features")

    async def _run() -> dict:
        return await generate_test_plan("https://acme.test", "explore pricing and features", context, analysis)

    plan_data = asyncio.run(_run())
    metadata = plan_data.get("metadata", {})

    if plan_data.get("plan"):
        findings["passed"].append("Planner returns plan with website analysis")
    else:
        findings["failed"].append("Planner returned empty plan")

    for field in (
        "website_type",
        "business_domain",
        "primary_goal",
        "recommended_test_flow",
        "high_risk_areas",
        "testing_priority",
        "analysis_confidence",
    ):
        if field in metadata:
            findings["passed"].append(f"Planner metadata includes {field}")
        else:
            findings["failed"].append(f"Planner metadata missing {field}")

    if metadata.get("planner_version") == "4.1.0":
        findings["passed"].append("Planner version bumped to 4.1.0")
    else:
        findings["failed"].append(f"Unexpected planner version: {metadata.get('planner_version')}")

    if plan_data.get("website_analysis"):
        findings["passed"].append("Planner returns website_analysis payload")

    from app.services.planner.plan_presentation import build_journey_summary

    journey = metadata.get("generated_journey") or []
    expected = build_journey_summary(plan_data["plan"], base_url="https://acme.test")
    if journey == expected:
        findings["passed"].append("generated_journey matches executable plan")
    else:
        findings["failed"].append(f"Journey mismatch: {journey} != {expected}")

    if metadata.get("analysis_reasoning"):
        findings["passed"].append("Planner metadata includes analysis_reasoning")
    else:
        findings["failed"].append("Planner metadata missing analysis_reasoning")

    return findings


def audit_analysis_journey_builder() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.website_analysis import analyze_website
    from app.services.website_analysis.journey_builder import try_build_analysis_journey

    context = _sample_saas_context()
    analysis = analyze_website(context)
    plan = try_build_analysis_journey(analysis, context, intent="flow")

    if plan and len(plan) >= 4:
        findings["passed"].append("Analysis-aware journey produces executable plan")
    else:
        findings["warnings"].append("Analysis journey not built for sample context (may fall back later)")

    if plan and plan[-1].get("action") == "capture":
        findings["passed"].append("Analysis journey ends with capture")
    elif plan:
        findings["failed"].append("Analysis journey missing capture step")

    return findings


def audit_api_compatibility() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.schemas import PlannerMetadata, RunTestResponse

    core = {
        "id", "goal", "status", "title", "url", "http_status", "duration_ms",
        "screenshot", "ai_plan", "ai_plan_source", "steps", "failures", "summary",
    }
    if core.issubset(set(RunTestResponse.model_fields.keys())):
        findings["passed"].append("RunTestResponse core contract preserved")

    optional_new = {
        "website_type", "business_domain", "primary_goal", "target_audience",
        "recommended_test_flow", "high_risk_areas", "testing_priority", "analysis_confidence",
        "analysis_reasoning",
    }
    meta_fields = set(PlannerMetadata.model_fields.keys())
    if optional_new.issubset(meta_fields):
        findings["passed"].append("PlannerMetadata extended with optional analysis fields")
    else:
        findings["failed"].append(f"Missing metadata fields: {optional_new - meta_fields}")

    sample = PlannerMetadata(
        planner_source="semantic_planner",
        planner_version="4.1.0",
        context_version="2.1",
        generated_at="2026-01-01T00:00:00Z",
        validation_score=90.0,
        planning_time_ms=10,
        website_type="SaaS",
        analysis_confidence=0.88,
    )
    if sample.website_type == "SaaS":
        findings["passed"].append("Optional analysis metadata validates")

    return findings


def audit_execution_production() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    bootstrap = BACKEND / "app" / "services" / "playwright_bootstrap.py"
    if bootstrap.exists():
        findings["passed"].append("Playwright bootstrap module present")
    else:
        findings["failed"].append("playwright_bootstrap.py missing")

    runner = (BACKEND / "app" / "services" / "playwright_runner.py").read_text(encoding="utf-8")
    if "launch_chromium" in runner and "ensure_playwright_browsers" in runner:
        findings["passed"].append("Runner uses Playwright bootstrap")
    else:
        findings["failed"].append("Runner missing Playwright bootstrap integration")

    assertion_engine = (BACKEND / "app" / "services" / "assertions" / "assertion_engine.py").read_text(encoding="utf-8")
    if "run_final_assertions" in assertion_engine and "assert_selector_visible" in (
        BACKEND / "app" / "services" / "assertions" / "element_assertion.py"
    ).read_text(encoding="utf-8"):
        findings["passed"].append("Assertion engine supports selector clicks and final journey checks")
    else:
        findings["failed"].append("Assertion engine missing production assertion hooks")

    journey_assertion = BACKEND / "app" / "services" / "assertions" / "journey_assertion.py"
    if journey_assertion.exists():
        findings["passed"].append("Journey assertion module present")
    else:
        findings["failed"].append("journey_assertion.py missing")

    from app.services.playwright_bootstrap import ensure_playwright_browsers

    if ensure_playwright_browsers():
        findings["passed"].append("Chromium launches successfully")
    else:
        findings["failed"].append("Chromium launch probe failed")

    return findings


def main() -> None:
    all_findings = {}

    section("1. WEBSITE ANALYSIS ENGINE")
    all_findings["analysis"] = audit_website_analysis_engine()
    print(json.dumps(all_findings["analysis"], indent=2))

    section("2. ANALYSIS JOURNEY BUILDER")
    all_findings["journey"] = audit_analysis_journey_builder()
    print(json.dumps(all_findings["journey"], indent=2))

    section("3. PLANNER INTEGRATION")
    all_findings["planner"] = audit_planner_integration()
    print(json.dumps(all_findings["planner"], indent=2))

    section("4. API COMPATIBILITY")
    all_findings["api"] = audit_api_compatibility()
    print(json.dumps(all_findings["api"], indent=2))

    section("5. EXECUTION PRODUCTION")
    all_findings["execution"] = audit_execution_production()
    print(json.dumps(all_findings["execution"], indent=2))

    failed = sum(len(v.get("failed", [])) for v in all_findings.values())
    print(f"\n{'=' * 60}\nTOTAL FAILURES: {failed}\n{'=' * 60}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
