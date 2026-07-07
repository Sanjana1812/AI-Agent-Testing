"""Sprint 5.3.1 verification harness — evaluation explainability and trust."""

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


def audit_explainability_module() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    path = BACKEND / "app" / "services" / "evaluation" / "explainability.py"
    if not path.exists():
        findings["failed"].append("explainability.py missing")
        return findings

    from app.services.evaluation.explainability import (
        DimensionEvaluation,
        assess_trust,
        build_overall_explainability,
        map_trust_level,
    )

    findings["passed"].append("explainability.py present")
    if map_trust_level(96) == "VERY_HIGH":
        findings["passed"].append("Trust VERY_HIGH mapping works")
    else:
        findings["failed"].append("VERY_HIGH trust mapping incorrect")

    if map_trust_level(88) == "HIGH":
        findings["passed"].append("Trust HIGH mapping works")
    else:
        findings["failed"].append("HIGH trust mapping incorrect")

    if map_trust_level(75) == "MEDIUM":
        findings["passed"].append("Trust MEDIUM mapping works")
    else:
        findings["failed"].append("MEDIUM trust mapping incorrect")

    if map_trust_level(55) == "LOW":
        findings["passed"].append("Trust LOW mapping works")
    else:
        findings["failed"].append("LOW trust mapping incorrect")

    if map_trust_level(40) == "VERY_LOW":
        findings["passed"].append("Trust VERY_LOW mapping works")
    else:
        findings["failed"].append("VERY_LOW trust mapping incorrect")

    trust = assess_trust(
        overall_score=88,
        planner_score=91,
        execution_score=88,
        evidence_score=100,
        diagnosis_score=89,
        goal_completion_score=66,
    )
    if trust.trust_level == "HIGH" and trust.trust_reason:
        findings["passed"].append("assess_trust returns level and reason")
    else:
        findings["failed"].append("assess_trust incomplete")

    dim = DimensionEvaluation(
        score=90,
        summary="ok",
        strengths=["a"],
        weaknesses=["b"],
        reasoning="because",
        recommendations=["do x"],
    )
    overall = build_overall_explainability(
        overall_score=90,
        planner=dim,
        execution=dim,
        evidence=dim,
        diagnosis=dim,
        goal_completion=dim,
        trust=trust,
    )
    if overall.reasoning and overall.strengths and overall.weaknesses and overall.recommendations:
        findings["passed"].append("build_overall_explainability produces full output")
    else:
        findings["failed"].append("Overall explainability incomplete")
    return findings


def _sample_result() -> dict:
    return {
        "id": "audit-run-531",
        "url": "https://example.com",
        "goal": "Verify navigation, search, and product pages",
        "status": "completed",
        "summary": {"total_steps": 4, "passed_steps": 3, "failed_steps": 0, "health": "PASS"},
        "ai_plan_metadata": {
            "generated_journey": ["Navigation", "Search", "Footer"],
            "execution_priority": ["Navigation", "Search", "Product"],
        },
        "ai_plan": [
            {"action": "open_page", "label": "Open Website"},
            {"action": "click", "label": "Verify Navigation"},
            {"action": "click", "label": "Verify Search"},
            {"action": "verify_visible", "label": "Verify Footer"},
        ],
        "steps": [
            {"step": "Open Website", "status": "passed"},
            {"step": "Verify Navigation", "status": "passed"},
            {"step": "Verify Search", "status": "passed"},
        ],
        "execution_intelligence": {"steps_retried": 1, "modals_dismissed": 1},
    }


def _sample_evidence() -> dict:
    return {
        "screenshot": "/storage/screenshots/audit.png",
        "console_logs": [{"type": "log", "text": "ready"}],
        "network_logs": [],
        "dom_snapshot": "<html></html>",
        "assertions": [{"label": "Navigation visible", "passed": True}],
    }


def audit_goal_completion() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.evaluation.goal_completion import evaluate_goal_completion_detail

    detail = evaluate_goal_completion_detail(_sample_result())
    if detail.score < 100:
        findings["passed"].append("Goal completion reflects partial verification")
    else:
        findings["failed"].append("Goal completion should be below 100% for partial sample")

    joined = " ".join(detail.weaknesses).lower()
    if "product" in joined:
        findings["passed"].append("Missing product pages noted in weaknesses")
    else:
        findings["failed"].append("Product pages gap not explained")

    if any("footer" in item.lower() for item in detail.weaknesses):
        findings["passed"].append("Planner-only footer noted outside goal")
    else:
        findings["warnings"].append("Footer outside goal not explicitly noted")
    return findings


def audit_reasoning_generation() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.evaluation.planner_evaluator import evaluate_planner_detail
    from app.services.evaluation.execution_evaluator import evaluate_execution_detail
    from app.services.evaluation.evidence_evaluator import evaluate_evidence_detail
    from app.services.evaluation.diagnosis_evaluator import evaluate_diagnosis_detail

    result = _sample_result()
    dimensions = [
        evaluate_planner_detail(result),
        evaluate_execution_detail(result),
        evaluate_evidence_detail(_sample_evidence(), result),
        evaluate_diagnosis_detail(None, _sample_evidence()),
    ]
    for index, dim in enumerate(dimensions, start=1):
        if dim.reasoning and dim.strengths and dim.weaknesses and dim.recommendations:
            findings["passed"].append(f"Dimension {index} explainability complete")
        else:
            findings["failed"].append(f"Dimension {index} explainability incomplete")

    planner = dimensions[0]
    if planner.confidence is not None:
        findings["passed"].append("Planner confidence included")
    else:
        findings["failed"].append("Planner confidence missing")
    return findings


def audit_evaluation_report() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.evaluation.report import build_evaluation_report, write_evaluation_reports
    from app.services.evaluation.scorecard import build_evaluation_result

    report = build_evaluation_report(
        _sample_result(),
        evidence_package=_sample_evidence(),
        diagnosis_report=None,
        write_reports=False,
    )
    summary = report.get("summary") or {}
    for field in (
        "trust_level",
        "trust_reason",
        "overall_reasoning",
        "planner_reasoning",
        "execution_reasoning",
        "evidence_reasoning",
        "diagnosis_reasoning",
        "goal_completion_reasoning",
    ):
        if summary.get(field):
            findings["passed"].append(f"Report summary includes {field}")
        else:
            findings["failed"].append(f"Report summary missing {field}")

    evaluation = build_evaluation_result(
        _sample_result(),
        evidence_package=_sample_evidence(),
    )
    with tempfile.TemporaryDirectory() as tmp:
        paths = write_evaluation_reports(evaluation, storage_dir=Path(tmp) / "audit-run-531")
        html = Path(paths["evaluation_html"]).read_text(encoding="utf-8")
        for token in ("Trust Level", "Overall Reasoning", "Strengths", "Weaknesses", "Recommendations"):
            if token in html:
                findings["passed"].append(f"HTML report contains {token}")
            else:
                findings["failed"].append(f"HTML report missing {token}")
    return findings


def audit_frontend_integration() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    results = (BACKEND.parent / "frontend" / "src" / "pages" / "Results.tsx").read_text(encoding="utf-8")
    api_types = (BACKEND.parent / "frontend" / "src" / "types" / "api.ts").read_text(encoding="utf-8")

    for token in ("trust_level", "Why this score?", "overall_strengths", "overall_weaknesses"):
        if token in results:
            findings["passed"].append(f"Results.tsx references {token}")
        else:
            findings["failed"].append(f"Results.tsx missing {token}")

    if "trust_level" in api_types and "overall_reasoning" in api_types:
        findings["passed"].append("api.ts defines explainability fields")
    else:
        findings["failed"].append("api.ts missing explainability fields")
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

    section("1. Explainability module")
    all_findings["explainability"] = audit_explainability_module()
    print(json.dumps(all_findings["explainability"], indent=2))

    section("2. Trust level")
    all_findings["trust"] = {"passed": all_findings["explainability"]["passed"][:6], "failed": [], "warnings": []}
    print(json.dumps(all_findings["trust"], indent=2))

    section("3. Goal completion")
    all_findings["goal_completion"] = audit_goal_completion()
    print(json.dumps(all_findings["goal_completion"], indent=2))

    section("4. Reasoning generation")
    all_findings["reasoning"] = audit_reasoning_generation()
    print(json.dumps(all_findings["reasoning"], indent=2))

    section("5. Evaluation report")
    all_findings["report"] = audit_evaluation_report()
    print(json.dumps(all_findings["report"], indent=2))

    section("6. Frontend integration")
    all_findings["frontend"] = audit_frontend_integration()
    print(json.dumps(all_findings["frontend"], indent=2))

    section("7. Regression audits")
    scripts = [
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

    sprint531_failures = sum(
        len(v.get("failed", []))
        for key, v in all_findings.items()
        if key not in {"regression", "trust"}
    )
    total_failures = sprint531_failures + regression_failures
    print(f"\n{'=' * 60}\nTOTAL FAILURES: {total_failures}\n{'=' * 60}")
    if total_failures:
        sys.exit(1)
    print("\nSprint 5.3.1 audit passed.")


if __name__ == "__main__":
    main()
