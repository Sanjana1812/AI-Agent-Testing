"""Sprint 4.2 verification harness — AI Diagnosis & Root Cause Analysis."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))


def section(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def _mock_evidence_package() -> dict:
    return {
        "run_id": "run-42",
        "execution_summary": {
            "total_steps": 4,
            "passed_steps": 2,
            "failed_steps": 1,
            "health": "FAIL",
        },
        "website_analysis": {
            "website_type": "E-commerce",
            "business_domain": "e-commerce",
            "confidence": 0.72,
            "high_risk_areas": ["Checkout", "Cart"],
        },
        "testing_strategy": {
            "testing_strategy": "Validate shopping and checkout flows",
            "execution_priority": ["Shop", "Cart", "Checkout"],
            "testing_priority": ["Shop", "Cart", "Checkout"],
            "strategy_reasoning": "Prioritize revenue paths.",
        },
        "execution_timeline": [
            {"id": "1", "step": "open_page:Homepage", "status": "passed", "duration_ms": 100},
            {
                "id": "2",
                "step": 'click:Show/Hide shortcuts shift + alt + Z',
                "status": "failed",
                "duration_ms": 200,
                "assertions": [],
            },
        ],
        "planner_metadata": {
            "website_type": "E-commerce",
            "planner_confidence": 0.68,
            "generated_journey": ["Homepage", "Show/Hide shortcuts shift + alt + Z"],
            "planner_source": "strategy",
        },
        "coverage_report": {
            "estimated_coverage_percent": 35.0,
            "areas": [
                {"area": "Checkout", "status": "not_tested", "reason": "Not reached"},
                {"area": "Navigation", "status": "tested", "reason": "Homepage loaded"},
            ],
        },
        "assertions": [],
        "failure_evidence": [
            {
                "step_number": 2,
                "step_name": 'click:Show/Hide shortcuts shift + alt + Z',
                "action": "click",
                "failure_type": "element_not_found",
                "selector_attempted": "button.accessibility-shortcut",
                "selector_alternatives": ["[aria-label*='shortcut']"],
                "exception": "Element not found",
                "current_url": "https://shop.example.com/",
                "page_title": "Example Shop",
                "console_errors": [],
                "network_errors": [],
            }
        ],
        "final_url": "https://shop.example.com/",
        "page_title": "Example Shop",
        "http_status": 200,
    }


def audit_diagnosis_modules() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    modules = [
        "models",
        "failure_classifier",
        "root_cause_analyzer",
        "severity_engine",
        "recommendation_engine",
        "ownership_engine",
        "complexity_engine",
        "confidence_engine",
        "diagnosis_builder",
        "diagnosis_validator",
        "prompts",
    ]
    for module in modules:
        path = BACKEND / "app" / "services" / "diagnosis" / f"{module}.py"
        if path.exists():
            findings["passed"].append(f"{module}.py present")
        else:
            findings["failed"].append(f"{module}.py missing")
    return findings


def audit_diagnosis_report() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.diagnosis import build_diagnosis_report
    from app.services.diagnosis.diagnosis_validator import DiagnosisReportValidator

    evidence = _mock_evidence_package()
    report = build_diagnosis_report(
        evidence,
        goal="Verify shopping cart and checkout work",
    )
    if not report:
        findings["failed"].append("build_diagnosis_report returned None for failed run")
        return findings

    required = {
        "failure_type",
        "root_cause",
        "severity",
        "confidence",
        "confidence_label",
        "business_impact",
        "recommendation",
        "developer_action",
        "qa_action",
        "next_steps",
        "supporting_evidence",
        "reasoning",
        "alternative_hypotheses",
        "ownership",
        "fix_complexity",
        "estimated_fix_time",
        "diagnosis_version",
    }
    missing = required - set(report.keys())
    if missing:
        findings["failed"].append(f"Diagnosis report missing keys: {sorted(missing)}")
    else:
        findings["passed"].append("Diagnosis report contains all required fields")

    validation = DiagnosisReportValidator().validate(report)
    if validation.valid:
        findings["passed"].append("Diagnosis report passes validator")
    else:
        findings["failed"].extend(validation.errors)

    if report.get("failure_type") == "TEST_DESIGN":
        findings["passed"].append("Accessibility shortcut classified as TEST_DESIGN")
    else:
        findings["failed"].append(
            f"Expected TEST_DESIGN for shortcut interaction, got {report.get('failure_type')}"
        )

    if report.get("supporting_evidence"):
        findings["passed"].append("Supporting evidence populated from structured inputs")
    else:
        findings["failed"].append("Supporting evidence empty")

    if "planner" in report.get("qa_action", "").lower() or report.get("ownership") == "Planner":
        findings["passed"].append("Ownership/actions reference planner for test-design failures")
    else:
        findings["warnings"].append("Planner ownership not explicit in QA action")

    return findings


def audit_api_integration() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.schemas import RunTestResponse

    fields = RunTestResponse.model_fields
    if "diagnosis_report" in fields:
        findings["passed"].append("RunTestResponse exposes optional diagnosis_report")
    else:
        findings["failed"].append("RunTestResponse missing diagnosis_report")

    source = (BACKEND / "app" / "routers" / "run.py").read_text(encoding="utf-8")
    if "build_diagnosis_report" in source:
        findings["passed"].append("run router builds diagnosis_report after evidence_package")
    else:
        findings["failed"].append("run router does not call build_diagnosis_report")

    return findings


def audit_success_run_no_diagnosis() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.diagnosis import build_diagnosis_report

    evidence = _mock_evidence_package()
    evidence["execution_summary"] = {
        "total_steps": 3,
        "passed_steps": 3,
        "failed_steps": 0,
        "health": "PASS",
    }
    evidence["failure_evidence"] = []
    report = build_diagnosis_report(evidence, goal="smoke test")
    if report is None:
        findings["passed"].append("No diagnosis report for successful runs")
    else:
        findings["failed"].append("Diagnosis report should be None when run passes")
    return findings


def main() -> None:
    all_findings: dict[str, dict] = {}
    section("1. Diagnosis modules")
    all_findings["modules"] = audit_diagnosis_modules()
    section("2. Diagnosis report")
    all_findings["report"] = audit_diagnosis_report()
    section("3. API integration")
    all_findings["api"] = audit_api_integration()
    section("4. Success run behavior")
    all_findings["success"] = audit_success_run_no_diagnosis()

    print(json.dumps(all_findings, indent=2))
    failed = sum(len(v.get("failed", [])) for v in all_findings.values())
    if failed:
        print(f"\nFAILED: {failed} issue(s)")
        sys.exit(1)
    print("\nSprint 4.2 audit passed.")


if __name__ == "__main__":
    main()
