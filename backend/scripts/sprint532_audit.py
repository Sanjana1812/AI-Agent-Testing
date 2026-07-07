"""Sprint 5.3.2 verification harness — execution context integration."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))


def section(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def _sample_result() -> dict:
    return {
        "id": "audit-run-532",
        "goal": "Verify navigation and search",
        "status": "success",
        "summary": {"total_steps": 4, "passed_steps": 3, "failed_steps": 1, "health": "FAIL"},
        "ai_plan": [
            {"action": "open_page", "label": "Open Website"},
            {"action": "click", "label": "Verify Navigation"},
            {"action": "click", "label": "Verify Search"},
        ],
        "steps": [
            {"id": "1", "step": "Open Website", "status": "passed", "assertions": []},
            {"id": "2", "step": "Verify Navigation", "status": "passed", "assertions": []},
            {"id": "3", "step": "Verify Search", "status": "failed", "assertions": []},
        ],
    }


def _sample_export() -> dict:
    return {
        "execution_context": {
            "goal": "Verify navigation and search",
            "total_steps": 3,
            "skipped_steps": [{"step_name": "Verify Footer", "skip_reason": "out of scope"}],
            "replan_count": 1,
            "replan_history": [
                {
                    "original_plan": [{"label": "Verify Search"}],
                    "modified_plan": [{"label": "Verify Search"}],
                }
            ],
            "execution_intelligence_log": [
                {"decision": {"decision_type": "RETRY"}, "outcome": "retried"},
                {"decision": {"decision_type": "RECOVER"}, "outcome": "recovered"},
                {"decision": {"decision_type": "SKIP"}, "outcome": "skipped"},
                {"decision": {"decision_type": "REPLAN"}, "outcome": "replanned"},
            ],
        }
    }


def audit_execution_summary_generation() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.execution_intelligence.execution_summary import build_execution_summary

    summary = build_execution_summary(_sample_result(), execution_export=_sample_export())
    checks = {
        "execution_mode": summary.get("execution_mode") == "ADAPTIVE",
        "retry_count": summary.get("retry_count") == 1,
        "recovery_count": summary.get("recovery_count") == 1,
        "replan_count": summary.get("replan_count") == 1,
        "adaptive_decision_count": summary.get("adaptive_decision_count") == 4,
    }
    for name, ok in checks.items():
        if ok:
            findings["passed"].append(f"{name} generated correctly")
        else:
            findings["failed"].append(f"{name} incorrect in execution summary")

    if summary.get("execution_findings") and summary.get("execution_recommendations"):
        findings["passed"].append("Execution findings and recommendations generated")
    else:
        findings["failed"].append("Execution findings/recommendations missing")
    return findings


def audit_effective_plan_selection() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    runner = (BACKEND / "app" / "services" / "playwright_runner.py").read_text(encoding="utf-8")
    if "plan[:] = completed_prefix + new_tail" in runner:
        findings["passed"].append("Runner mutates plan to adapted effective plan")
    else:
        findings["failed"].append("Runner does not mutate plan after replanning")

    if "ai_plan=plan" in runner:
        findings["passed"].append("Public ai_plan uses effective plan")
    else:
        findings["failed"].append("build_result is not fed the effective plan")

    if "original_plan" not in (BACKEND / "app" / "schemas.py").read_text(encoding="utf-8"):
        findings["passed"].append("Original plan is not exposed on public API")
    else:
        findings["failed"].append("Original plan should not be publicly exposed")
    return findings


def audit_coverage_integration() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    run_router = (BACKEND / "app" / "routers" / "run.py").read_text(encoding="utf-8")
    if "effective_plan = result.get(\"ai_plan\")" in run_router and "estimate_coverage(" in run_router:
        findings["passed"].append("Coverage recomputed from effective_plan after execution")
    else:
        findings["failed"].append("Coverage integration missing effective_plan recompute")
    return findings


def audit_diagnosis_and_evaluation_integration() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    run_router = (BACKEND / "app" / "routers" / "run.py").read_text(encoding="utf-8")
    if "result[\"execution_summary\"] = build_execution_summary" in run_router:
        findings["passed"].append("Router builds execution summary")
    else:
        findings["failed"].append("Router missing execution summary build")

    if "execution_summary=result[\"execution_summary\"]" in run_router:
        findings["passed"].append("Router passes execution summary downstream")
    else:
        findings["failed"].append("Router does not pass execution summary to downstream services")

    diagnosis_builder = (BACKEND / "app" / "services" / "diagnosis" / "diagnosis_builder.py").read_text(encoding="utf-8")
    if "execution_summary" in diagnosis_builder and "Execution context:" in diagnosis_builder:
        findings["passed"].append("Diagnosis consumes execution summary context")
    else:
        findings["failed"].append("Diagnosis integration missing execution summary context")

    evaluator = (BACKEND / "app" / "services" / "evaluation" / "execution_evaluator.py").read_text(encoding="utf-8")
    if "result.get(\"execution_summary\")" in evaluator:
        findings["passed"].append("Evaluation consumes execution summary")
    else:
        findings["failed"].append("Evaluation still depends on raw execution logs")
    return findings


def audit_api_and_frontend() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    schemas = (BACKEND / "app" / "schemas.py").read_text(encoding="utf-8")
    frontend = (BACKEND.parent / "frontend" / "src" / "pages" / "Results.tsx").read_text(encoding="utf-8")
    api_types = (BACKEND.parent / "frontend" / "src" / "types" / "api.ts").read_text(encoding="utf-8")

    if "execution_summary: AdaptiveExecutionSummary | None = None" in schemas:
        findings["passed"].append("RunTestResponse exposes execution_summary")
    else:
        findings["failed"].append("RunTestResponse missing execution_summary")

    for token in ("Execution summary", "execution_reasoning", "execution_findings", "execution_recommendations"):
        if token in frontend:
            findings["passed"].append(f"Results.tsx references {token}")
        else:
            findings["failed"].append(f"Results.tsx missing {token}")

    if "AdaptiveExecutionSummary" in api_types and "execution_summary?: AdaptiveExecutionSummary | null" in api_types:
        findings["passed"].append("Frontend API types include execution_summary")
    else:
        findings["failed"].append("Frontend API types missing execution_summary")
    return findings


def run_regression(script_name: str) -> tuple[str, int]:
    proc = subprocess.run(
        [sys.executable, str(BACKEND / "scripts" / script_name)],
        cwd=str(BACKEND),
        capture_output=True,
        text=True,
    )
    output = proc.stdout + proc.stderr
    failures = 0
    for line in output.splitlines():
        if "TOTAL FAILURES:" in line:
            try:
                failures = int(line.split(":")[-1].strip())
            except ValueError:
                failures = 1
    return output, failures


def main() -> None:
    all_findings: dict[str, dict] = {}

    section("1. Execution summary generation")
    all_findings["summary"] = audit_execution_summary_generation()
    print(json.dumps(all_findings["summary"], indent=2))

    section("2. Effective plan selection")
    all_findings["effective_plan"] = audit_effective_plan_selection()
    print(json.dumps(all_findings["effective_plan"], indent=2))

    section("3. Coverage integration")
    all_findings["coverage"] = audit_coverage_integration()
    print(json.dumps(all_findings["coverage"], indent=2))

    section("4. Diagnosis and evaluation integration")
    all_findings["integration"] = audit_diagnosis_and_evaluation_integration()
    print(json.dumps(all_findings["integration"], indent=2))

    section("5. API and frontend")
    all_findings["frontend"] = audit_api_and_frontend()
    print(json.dumps(all_findings["frontend"], indent=2))

    section("6. Regression audits")
    scripts = [
        "sprint531_audit.py",
        "sprint53_audit.py",
        "sprint52_audit.py",
        "sprint51_audit.py",
        "sprint50_audit.py",
        "sprint42_audit.py",
        "sprint41b_audit.py",
        "sprint41a_audit.py",
        "sprint41_audit.py",
        "sprint40_audit.py",
        "sprint391_audit.py",
    ]
    regression_failures = 0
    for script in scripts:
        output, failures = run_regression(script)
        if failures == 0:
            all_findings.setdefault("regression", {"passed": [], "failed": []})
            all_findings["regression"]["passed"].append(f"{script} passed")
        else:
            all_findings.setdefault("regression", {"passed": [], "failed": []})
            all_findings["regression"]["failed"].append(f"{script} reported {failures} failure(s)")
            regression_failures += failures
            print(output[-1500:])
    print(json.dumps(all_findings.get("regression", {}), indent=2))

    sprint532_failures = sum(len(v.get("failed", [])) for key, v in all_findings.items() if key != "regression")
    total_failures = sprint532_failures + regression_failures
    print(f"\n{'=' * 60}\nTOTAL FAILURES: {total_failures}\n{'=' * 60}")
    if total_failures:
        sys.exit(1)
    print("\nSprint 5.3.2 audit passed.")


if __name__ == "__main__":
    main()
