"""Sprint 4.1B verification harness — Evidence Foundation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))


def section(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def _mock_result() -> dict:
    return {
        "id": "run-123",
        "url": "https://example.com/contact",
        "title": "Example Contact",
        "http_status": 200,
        "duration_ms": 4200,
        "screenshot": "/storage/screenshots/run-123.png",
        "browser": "Chromium (headless)",
        "viewport": "1280×720",
        "summary": {"total_steps": 4, "passed_steps": 3, "failed_steps": 1, "health": "FAIL"},
        "ai_plan_metadata": {
            "planner_version": "4.1.0",
            "context_version": "2.1",
            "testing_strategy": "Validate contact pathways",
            "confidence_breakdown": {"signals": [{"signal": "Navigation", "contribution": 0.12}]},
            "coverage_report": {"estimated_coverage_percent": 72.0, "areas": []},
        },
        "ai_plan": [
            {"action": "open_page", "label": "Open Homepage"},
            {"action": "click", "selector": "a.contact", "label": 'Click "Contact"'},
        ],
        "steps": [
            {"id": "1", "step": "open_page:Open Homepage", "status": "passed", "duration_ms": 120, "assertions": []},
            {
                "id": "2",
                "step": "click:Contact",
                "status": "failed",
                "duration_ms": 340,
                "assertions": [
                    {
                        "type": "element_visible",
                        "expected": "visible",
                        "actual": "hidden",
                        "passed": False,
                        "reason": "Selector not visible",
                    }
                ],
            },
        ],
        "failures": [
            {
                "type": "element_not_found",
                "message": "Selector not found: a.contact",
                "severity": "medium",
                "selector": "a.contact",
            }
        ],
    }


def audit_evidence_modules() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    modules = [
        "collector",
        "snapshot",
        "console",
        "network",
        "dom_capture",
        "serializer",
        "models",
    ]
    for module in modules:
        path = BACKEND / "app" / "services" / "evidence" / f"{module}.py"
        if path.exists():
            findings["passed"].append(f"{module}.py present")
        else:
            findings["failed"].append(f"{module}.py missing")
    return findings


def audit_evidence_package() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.evidence import EvidenceCollector, build_evidence_package
    from app.services.evidence.models import EvidencePackage, FailureEvidence

    required = {
        "run_id",
        "execution_summary",
        "website_analysis",
        "testing_strategy",
        "execution_timeline",
        "planner_metadata",
        "explainability_records",
        "coverage_report",
        "assertions",
        "screenshot",
        "final_url",
        "page_title",
        "http_status",
        "failure_evidence",
        "console_logs",
        "network_logs",
        "dom_snapshot",
    }

    package_dict = build_evidence_package(
        _mock_result(),
        website_analysis={"website_type": "Business Website"},
        testing_strategy={"testing_strategy": "Validate contact pathways", "strategy_version": "4.1A"},
        execution_evidence={
            "console_logs": [{"type": "error", "text": "TypeError: x is undefined"}],
            "network_logs": [{"event": "http_error", "status": 404, "url": "https://example.com/missing.js"}],
            "failure_records": [
                {
                    "step_number": 2,
                    "step_name": "click:Contact",
                    "action": "click",
                    "timestamp": "2026-01-01T00:00:00Z",
                    "selector_attempted": "a.contact",
                    "failure_type": "element_not_found",
                    "exception": "Selector not found",
                    "dom_snapshot": {"title": "Example Contact"},
                }
            ],
        },
    )

    missing = required - set(package_dict.keys())
    if missing:
        findings["failed"].append(f"EvidencePackage missing fields: {sorted(missing)}")
    else:
        findings["passed"].append("EvidencePackage contains all required fields")

    if package_dict.get("failure_evidence"):
        findings["passed"].append("FailureEvidence attached")
    else:
        findings["failed"].append("FailureEvidence missing")

    if package_dict.get("console_logs"):
        findings["passed"].append("Console logs collected")
    else:
        findings["failed"].append("Console logs missing")

    if package_dict.get("network_logs"):
        findings["passed"].append("Network logs collected")
    else:
        findings["failed"].append("Network logs missing")

    if package_dict.get("dom_snapshot"):
        findings["passed"].append("DOM snapshot captured")
    else:
        findings["failed"].append("DOM snapshot missing")

    if package_dict.get("screenshot"):
        findings["passed"].append("Screenshot linked")
    else:
        findings["failed"].append("Screenshot missing")

    if package_dict.get("explainability_records"):
        findings["passed"].append("Explainability attached")
    else:
        findings["failed"].append("Explainability missing")

    if package_dict.get("coverage_report"):
        findings["passed"].append("Coverage attached")
    else:
        findings["failed"].append("Coverage missing")

    if package_dict.get("planner_metadata"):
        findings["passed"].append("Planner metadata attached")
    else:
        findings["failed"].append("Planner metadata missing")

    collector = EvidenceCollector()
    package = collector.build_package(_mock_result())
    if isinstance(package, EvidencePackage):
        findings["passed"].append("EvidenceCollector returns typed EvidencePackage")

    failure = FailureEvidence(
        step_number=2,
        step_name="click:Contact",
        action="click",
        timestamp="2026-01-01T00:00:00Z",
        current_url="https://example.com",
        page_title="Example",
        selector_attempted="a.contact",
        failure_type="element_not_found",
        exception="Selector not found",
    )
    if failure.to_dict().get("execution_context") is None:
        findings["passed"].append("FailureEvidence model serializes")

    return findings


def audit_legacy_compatibility() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.evidence import collect_evidence_for_run

    packages = collect_evidence_for_run(_mock_result(), website_context={"navigation": []})
    if len(packages) == 1:
        findings["passed"].append("Sprint 4.0 legacy per-failure packages preserved")
    else:
        findings["failed"].append(f"Expected 1 legacy package, got {len(packages)}")

    from app.schemas import RunTestResponse

    if "evidence_package" in RunTestResponse.model_fields:
        findings["passed"].append("Optional evidence_package on API response")
    else:
        findings["failed"].append("evidence_package missing from RunTestResponse")

    runner = (BACKEND / "app" / "services" / "playwright_runner.py").read_text(encoding="utf-8")
    if "ExecutionEvidenceBuffer" in runner and "_execute_sync" in runner:
        findings["passed"].append("Execution evidence buffer wired into runner")
    else:
        findings["failed"].append("Execution evidence buffer not wired")

    return findings


def main() -> None:
    all_findings = {}

    section("1. EVIDENCE MODULES")
    all_findings["modules"] = audit_evidence_modules()
    print(json.dumps(all_findings["modules"], indent=2))

    section("2. EVIDENCE PACKAGE")
    all_findings["package"] = audit_evidence_package()
    print(json.dumps(all_findings["package"], indent=2))

    section("3. BACKWARD COMPATIBILITY")
    all_findings["compat"] = audit_legacy_compatibility()
    print(json.dumps(all_findings["compat"], indent=2))

    failed = sum(len(v.get("failed", [])) for v in all_findings.values())
    print(f"\n{'=' * 60}\nTOTAL FAILURES: {failed}\n{'=' * 60}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
