"""Sprint 5.3 verification harness — evaluation and validation framework."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))


def section(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def audit_package() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    modules = [
        "__init__",
        "models",
        "dataset",
        "planner_evaluator",
        "execution_evaluator",
        "evidence_evaluator",
        "diagnosis_evaluator",
        "goal_completion",
        "metrics",
        "scorecard",
        "report",
        "validator",
    ]
    base = BACKEND / "app" / "services" / "evaluation"
    for module in modules:
        if (base / f"{module}.py").exists():
            findings["passed"].append(f"evaluation/{module}.py present")
        else:
            findings["failed"].append(f"evaluation/{module}.py missing")
    return findings


def audit_dataset() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.evaluation.dataset import (
        find_matching_case,
        load_all_cases,
        load_evaluation_case,
        validate_case_payload,
    )

    root = BACKEND / "evaluation"
    if not root.is_dir():
        findings["failed"].append("backend/evaluation directory missing")
        return findings

    expected = {"amazon", "github", "openai", "stripe", "shopify", "microsoft", "wikipedia"}
    found = {path.stem for path in root.glob("*.json")}
    if expected.issubset(found):
        findings["passed"].append("All seven sample datasets present")
    else:
        missing = sorted(expected - found)
        findings["failed"].append(f"Missing datasets: {', '.join(missing)}")

    cases = load_all_cases()
    if len(cases) >= 7:
        findings["passed"].append(f"Dataset loader returned {len(cases)} cases")
    else:
        findings["failed"].append(f"Expected at least 7 cases, got {len(cases)}")

    github = load_evaluation_case("github.json")
    if github.url and github.goal and github.minimum_assertions >= 0:
        findings["passed"].append("load_evaluation_case parses GitHub case")
    else:
        findings["failed"].append("GitHub case parse failed")

    matched = find_matching_case(url="https://github.com/features", goal=github.goal)
    if matched and matched.name == "GitHub":
        findings["passed"].append("find_matching_case matches URL prefix")
    else:
        findings["failed"].append("find_matching_case failed for GitHub URL")

    invalid_errors = validate_case_payload({"url": "", "goal": "", "minimum_assertions": -1})
    if invalid_errors:
        findings["passed"].append("validate_case_payload rejects invalid cases")
    else:
        findings["failed"].append("validate_case_payload should reject invalid cases")
    return findings


def _sample_result() -> dict:
    return {
        "id": "audit-run-53",
        "url": "https://github.com",
        "goal": "Verify navigation, repository discovery, and documentation access",
        "status": "completed",
        "steps": [
            {"action": "open_page", "label": "Open Website", "status": "passed"},
            {"action": "click", "label": 'Click "Explore"', "status": "passed"},
            {"action": "verify_visible", "label": "Verify Navigation", "status": "passed"},
            {"action": "verify_visible", "label": "Verify Footer", "status": "passed"},
        ],
        "website_context_summary": {
            "website_type": "Developer Platform",
            "primary_goal": "Software collaboration",
            "recommended_test_flow": ["Homepage", "Explore", "Documentation"],
            "testing_strategy": "Focus on navigation and docs",
            "estimated_coverage_percent": 75,
        },
        "execution_intelligence": {
            "summary": {
                "retries": 1,
                "recoveries": 0,
                "skipped_steps": 0,
                "replanned_steps": 0,
            }
        },
        "assertions": [
            {"status": "passed", "label": "Navigation visible"},
            {"status": "failed", "label": "Search works"},
        ],
    }


def _sample_evidence() -> dict:
    return {
        "screenshot": "/storage/screenshots/audit.png",
        "console_logs": [{"type": "log", "text": "ready"}],
        "network_logs": [{"url": "https://github.com", "status": 200}],
        "dom_snapshot": "<html></html>",
        "assertion_evidence": [{"label": "Navigation visible", "passed": True}],
        "failure_evidence": [{"step": "Search", "message": "not found"}],
    }


def _sample_diagnosis() -> dict:
    return {
        "failure_type": "element_not_found",
        "severity": "medium",
        "confidence": 0.82,
        "root_cause": "Search selector did not match DOM",
        "recommendation": "Update selector strategy",
        "developer_action": "Review search component markup",
        "qa_action": "Re-run with updated goal",
    }


def audit_planner_evaluator() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.evaluation.planner_evaluator import evaluate_planner

    score, planner_findings = evaluate_planner(_sample_result())
    if 0 <= score <= 100 and planner_findings:
        findings["passed"].append("Planner evaluator returns score and findings")
    else:
        findings["failed"].append("Planner evaluator output invalid")
    return findings


def audit_execution_evaluator() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.evaluation.execution_evaluator import evaluate_execution

    score, summary = evaluate_execution(_sample_result())
    if 0 <= score <= 100 and summary:
        findings["passed"].append("Execution evaluator returns score and summary")
    else:
        findings["failed"].append("Execution evaluator output invalid")
    return findings


def audit_evidence_evaluator() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.evaluation.evidence_evaluator import evaluate_evidence

    score, summary = evaluate_evidence(_sample_evidence(), _sample_result())
    if 0 <= score <= 100 and summary:
        findings["passed"].append("Evidence evaluator returns score and summary")
    else:
        findings["failed"].append("Evidence evaluator output invalid")
    return findings


def audit_diagnosis_evaluator() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.evaluation.diagnosis_evaluator import evaluate_diagnosis

    score, summary = evaluate_diagnosis(_sample_diagnosis(), _sample_evidence())
    if 0 <= score <= 100 and summary:
        findings["passed"].append("Diagnosis evaluator returns score and summary")
    else:
        findings["failed"].append("Diagnosis evaluator output invalid")
    return findings


def audit_goal_completion() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.evaluation.goal_completion import evaluate_goal_completion

    goal = "Verify navigation, search, and product pages"
    score, summary = evaluate_goal_completion(_sample_result(), goal=goal)
    if 0 <= score <= 100 and summary:
        findings["passed"].append("Goal completion returns percentage and summary")
    if score < 100:
        findings["passed"].append("Partial goal coverage reflected in score")
    else:
        findings["warnings"].append("Goal completion scored 100% for partial goal sample")
    return findings


def audit_metrics_and_scorecard() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.evaluation.metrics import build_metrics, build_scorecard
    from app.services.evaluation.scorecard import build_evaluation_result

    scorecard = build_scorecard(
        planner_score=91,
        execution_score=88,
        evidence_score=100,
        diagnosis_score=89,
        goal_completion_score=90,
    )
    if scorecard.overall_score > 0:
        findings["passed"].append("Metrics module computes overall score")
    else:
        findings["failed"].append("Overall score not computed")

    metrics = build_metrics(
        planner_score=91,
        execution_score=88,
        evidence_score=100,
        diagnosis_score=89,
        goal_completion_score=90,
    )
    if len(metrics) == 5:
        findings["passed"].append("Five weighted metrics produced")
    else:
        findings["failed"].append(f"Expected 5 metrics, got {len(metrics)}")

    evaluation = build_evaluation_result(
        _sample_result(),
        evidence_package=_sample_evidence(),
        diagnosis_report=_sample_diagnosis(),
    )
    if evaluation.scorecard.overall_score > 0 and evaluation.summary.planner_findings:
        findings["passed"].append("Scorecard orchestrates all evaluators")
    else:
        findings["failed"].append("build_evaluation_result incomplete")
    return findings


def audit_report_generation() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.evaluation.report import build_evaluation_report

    with tempfile.TemporaryDirectory() as tmp:
        storage = Path(tmp)
        report = build_evaluation_report(
            _sample_result(),
            evidence_package=_sample_evidence(),
            diagnosis_report=_sample_diagnosis(),
            write_reports=False,
        )
        if report.get("scorecard") and report.get("summary"):
            findings["passed"].append("build_evaluation_report returns scorecard payload")
        else:
            findings["failed"].append("build_evaluation_report missing scorecard")

        from app.services.evaluation.models import EvaluationResult
        from app.services.evaluation.report import write_evaluation_reports
        from app.services.evaluation.scorecard import build_evaluation_result

        evaluation = build_evaluation_result(
            _sample_result(),
            evidence_package=_sample_evidence(),
            diagnosis_report=_sample_diagnosis(),
        )
        paths = write_evaluation_reports(evaluation, storage_dir=storage / "audit-run-53")
        json_path = Path(paths["evaluation_json"])
        html_path = Path(paths["evaluation_html"])
        if json_path.exists() and html_path.exists():
            findings["passed"].append("evaluation.json and evaluation.html generated")
        else:
            findings["failed"].append("Report files not written")

        html_text = html_path.read_text(encoding="utf-8")
        for token in (
            "Executive Summary",
            "Planner",
            "Execution",
            "Evidence",
            "Diagnosis",
            "Goal Completion",
            "Overall AI Score",
            "Recommendations",
        ):
            if token in html_text:
                findings["passed"].append(f"HTML report contains {token}")
            else:
                findings["failed"].append(f"HTML report missing {token}")
    return findings


def audit_validator() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.evaluation.metrics import build_metrics
    from app.services.evaluation.models import EvaluationResult, EvaluationScorecard, EvaluationSummary
    from app.services.evaluation.validator import validate_evaluation_result

    valid = validate_evaluation_result(
        EvaluationResult(
            run_id="x",
            goal="g",
            scorecard=EvaluationScorecard(
                planner_score=90,
                execution_score=90,
                evidence_score=90,
                diagnosis_score=90,
                goal_completion_score=90,
                overall_score=90,
            ),
            summary=EvaluationSummary(
                execution_summary="4/4 steps completed.",
                evidence_summary="Screenshot and logs captured.",
                planner_confidence=90,
                planner_strengths=["Goal understood"],
                planner_weaknesses=["None"],
                planner_reasoning="Planner aligned with goal.",
                planner_recommendations=["Maintain quality"],
                execution_strengths=["Steps completed"],
                execution_weaknesses=["None"],
                execution_reasoning="Execution stable.",
                execution_recommendations=["Maintain quality"],
                evidence_strengths=["Screenshot captured"],
                evidence_weaknesses=["None"],
                evidence_reasoning="Evidence complete.",
                evidence_recommendations=["Maintain quality"],
                diagnosis_strengths=["Not required"],
                diagnosis_weaknesses=["None"],
                diagnosis_reasoning="No failures.",
                diagnosis_recommendations=["Maintain quality"],
                goal_completion_strengths=["Goal covered"],
                goal_completion_weaknesses=["None"],
                goal_completion_reasoning="Goal themes verified.",
                goal_completion_recommendations=["Maintain quality"],
                trust_level="HIGH",
                trust_reason="Strong run quality.",
                overall_reasoning="Overall score reflects strong dimensions.",
                overall_strengths=["Planner strong"],
                overall_weaknesses=["None"],
                overall_recommendations=["Maintain quality"],
            ),
            metrics=build_metrics(
                planner_score=90,
                execution_score=90,
                evidence_score=90,
                diagnosis_score=90,
                goal_completion_score=90,
            ),
        )
    )
    if valid.valid:
        findings["passed"].append("Validator accepts complete scorecard")
    else:
        findings["failed"].append("Validator rejected valid scorecard")

    invalid = validate_evaluation_result(
        EvaluationResult(
            run_id="",
            goal="",
            scorecard=EvaluationScorecard(planner_score=150),
            summary=EvaluationSummary(),
        )
    )
    if not invalid.valid:
        findings["passed"].append("Validator rejects out-of-range scores")
    else:
        findings["failed"].append("Validator should reject invalid scores")
    return findings


def audit_backend_integration() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    run_router = (BACKEND / "app" / "routers" / "run.py").read_text(encoding="utf-8")
    for token in ("build_evaluation_report", "evaluation_report", "build_diagnosis_report"):
        if token in run_router:
            findings["passed"].append(f"run.py integrates {token}")
        else:
            findings["failed"].append(f"run.py missing {token}")

    diagnosis_idx = run_router.find("build_diagnosis_report")
    eval_idx = run_router.find("build_evaluation_report")
    if diagnosis_idx >= 0 and eval_idx > diagnosis_idx:
        findings["passed"].append("Evaluation runs after diagnosis")
    else:
        findings["failed"].append("Evaluation must be wired after diagnosis")

    schemas = (BACKEND / "app" / "schemas.py").read_text(encoding="utf-8")
    if "evaluation_report" in schemas:
        findings["passed"].append("RunTestResponse exposes evaluation_report")
    else:
        findings["failed"].append("schemas.py missing evaluation_report")

    for path, forbidden in [
        ("app/services/ai_planner.py", "evaluation"),
        ("app/services/playwright_runner.py", "build_evaluation_report"),
    ]:
        text = (BACKEND / path).read_text(encoding="utf-8").lower()
        if forbidden.lower() not in text:
            findings["passed"].append(f"{path} not modified by evaluation layer")
        else:
            findings["failed"].append(f"{path} must not import evaluation")
    return findings


def audit_frontend_integration() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    results = (BACKEND.parent / "frontend" / "src" / "pages" / "Results.tsx").read_text(encoding="utf-8")
    api_types = (BACKEND.parent / "frontend" / "src" / "types" / "api.ts").read_text(encoding="utf-8")

    for token in ("evaluation_report", "Evaluation summary", "overall_score", "planner_score"):
        if token in results:
            findings["passed"].append(f"Results.tsx references {token}")
        else:
            findings["failed"].append(f"Results.tsx missing {token}")

    if "EvaluationReport" in api_types and "evaluation_report" in api_types:
        findings["passed"].append("api.ts defines EvaluationReport type")
    else:
        findings["failed"].append("api.ts missing EvaluationReport")
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

    section("1. Evaluation package")
    all_findings["package"] = audit_package()
    print(json.dumps(all_findings["package"], indent=2))

    section("2. Dataset loader")
    all_findings["dataset"] = audit_dataset()
    print(json.dumps(all_findings["dataset"], indent=2))

    section("3. Planner evaluator")
    all_findings["planner"] = audit_planner_evaluator()
    print(json.dumps(all_findings["planner"], indent=2))

    section("4. Execution evaluator")
    all_findings["execution"] = audit_execution_evaluator()
    print(json.dumps(all_findings["execution"], indent=2))

    section("5. Evidence evaluator")
    all_findings["evidence"] = audit_evidence_evaluator()
    print(json.dumps(all_findings["evidence"], indent=2))

    section("6. Diagnosis evaluator")
    all_findings["diagnosis"] = audit_diagnosis_evaluator()
    print(json.dumps(all_findings["diagnosis"], indent=2))

    section("7. Goal completion")
    all_findings["goal_completion"] = audit_goal_completion()
    print(json.dumps(all_findings["goal_completion"], indent=2))

    section("8. Metrics and scorecard")
    all_findings["metrics"] = audit_metrics_and_scorecard()
    print(json.dumps(all_findings["metrics"], indent=2))

    section("9. Report generation")
    all_findings["report"] = audit_report_generation()
    print(json.dumps(all_findings["report"], indent=2))

    section("10. Validator")
    all_findings["validator"] = audit_validator()
    print(json.dumps(all_findings["validator"], indent=2))

    section("11. Backend integration")
    all_findings["backend"] = audit_backend_integration()
    print(json.dumps(all_findings["backend"], indent=2))

    section("12. Frontend integration")
    all_findings["frontend"] = audit_frontend_integration()
    print(json.dumps(all_findings["frontend"], indent=2))

    section("13. Regression audits")
    scripts = [
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

    sprint53_failures = sum(
        len(v.get("failed", [])) for key, v in all_findings.items() if key != "regression"
    )
    total_failures = sprint53_failures + regression_failures
    print(f"\n{'=' * 60}\nTOTAL FAILURES: {total_failures}\n{'=' * 60}")
    if total_failures:
        sys.exit(1)
    print("\nSprint 5.3 audit passed.")


if __name__ == "__main__":
    main()
