"""Generate evaluation JSON and HTML reports."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from app.services.evaluation.models import EvaluationResult, EvaluationSummary
from app.services.evaluation.scorecard import build_evaluation_result
from app.services.evaluation.validator import validate_evaluation_result

_EVALUATION_STORAGE = Path(__file__).resolve().parent.parent.parent.parent / "storage" / "evaluation"


def _list_items(items: list[str]) -> str:
    if not items:
        return "<li>None recorded.</li>"
    return "".join(f"<li>{html.escape(item)}</li>" for item in items)


def _render_dimension_section(
    title: str,
    score: float,
    *,
    summary: EvaluationSummary,
    prefix: str,
) -> str:
    strengths = getattr(summary, f"{prefix}_strengths", [])
    weaknesses = getattr(summary, f"{prefix}_weaknesses", [])
    reasoning = getattr(summary, f"{prefix}_reasoning", "")
    recommendations = getattr(summary, f"{prefix}_recommendations", [])
    confidence_html = ""
    if prefix == "planner" and summary.planner_confidence is not None:
        confidence_html = f"<p><strong>Confidence:</strong> {summary.planner_confidence:.0f}%</p>"

    return f"""
  <div class="card">
    <h2>{html.escape(title)}</h2>
    <p class="score">{score:.0f}%</p>
    {confidence_html}
    <h3>Strengths</h3>
    <ul>{_list_items(strengths)}</ul>
    <h3>Weaknesses</h3>
    <ul>{_list_items(weaknesses)}</ul>
    <p><strong>Reasoning:</strong> {html.escape(reasoning)}</p>
    <h3>Recommendations</h3>
    <ul>{_list_items(recommendations)}</ul>
  </div>"""


def _render_html(evaluation: EvaluationResult) -> str:
    scorecard = evaluation.scorecard
    summary = evaluation.summary

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Evaluation Report — {html.escape(evaluation.run_id)}</title>
  <style>
    body {{ font-family:Segoe UI,Arial,sans-serif; margin:2rem; color:#0f172b; background:#f7f6f3; }}
    h1,h2,h3 {{ color:#3239a0; }}
    .card {{ background:#fff; border:1px solid #e5e3dc; border-radius:12px; padding:1.25rem; margin-bottom:1rem; }}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:1rem; }}
    .score {{ font-size:1.75rem; font-weight:700; }}
    .trust {{ display:inline-block; padding:0.35rem 0.75rem; border-radius:999px; background:#e8e6ff; color:#3239a0; font-weight:600; }}
    ul {{ line-height:1.6; }}
  </style>
</head>
<body>
  <h1>AI QA Evaluation Report</h1>
  <div class="card">
    <h2>Executive Summary</h2>
    <p><strong>Run ID:</strong> {html.escape(evaluation.run_id)}</p>
    <p><strong>Goal:</strong> {html.escape(evaluation.goal)}</p>
    <p class="score">Overall AI Score: {scorecard.overall_score:.0f}%</p>
    <p><span class="trust">Trust Level: {html.escape(summary.trust_level.replace('_', ' '))}</span></p>
    <p><strong>Trust Reason:</strong> {html.escape(summary.trust_reason)}</p>
    <p><strong>Overall Reasoning:</strong> {html.escape(summary.overall_reasoning)}</p>
    <h3>Overall Strengths</h3>
    <ul>{_list_items(summary.overall_strengths)}</ul>
    <h3>Overall Weaknesses</h3>
    <ul>{_list_items(summary.overall_weaknesses)}</ul>
    <h3>Overall Recommendations</h3>
    <ul>{_list_items(summary.overall_recommendations)}</ul>
  </div>
  <div class="grid">
    <div class="card"><h3>Planner</h3><p class="score">{scorecard.planner_score:.0f}%</p></div>
    <div class="card"><h3>Execution</h3><p class="score">{scorecard.execution_score:.0f}%</p></div>
    <div class="card"><h3>Evidence</h3><p class="score">{scorecard.evidence_score:.0f}%</p></div>
    <div class="card"><h3>Diagnosis</h3><p class="score">{scorecard.diagnosis_score:.0f}%</p></div>
    <div class="card"><h3>Goal Completion</h3><p class="score">{scorecard.goal_completion_score:.0f}%</p></div>
  </div>
  {_render_dimension_section("Planner", scorecard.planner_score, summary=summary, prefix="planner")}
  {_render_dimension_section("Execution", scorecard.execution_score, summary=summary, prefix="execution")}
  {_render_dimension_section("Evidence", scorecard.evidence_score, summary=summary, prefix="evidence")}
  {_render_dimension_section("Diagnosis", scorecard.diagnosis_score, summary=summary, prefix="diagnosis")}
  <div class="card">
    <h2>Goal Completion</h2>
    <p class="score">{scorecard.goal_completion_score:.0f}%</p>
    <p>{html.escape(summary.goal_completion_summary)}</p>
    <h3>Strengths</h3>
    <ul>{_list_items(summary.goal_completion_strengths)}</ul>
    <h3>Weaknesses</h3>
    <ul>{_list_items(summary.goal_completion_weaknesses)}</ul>
    <p><strong>Reasoning:</strong> {html.escape(summary.goal_completion_reasoning)}</p>
    <h3>Recommendations</h3>
    <ul>{_list_items(summary.goal_completion_recommendations)}</ul>
  </div>
</body>
</html>"""


def write_evaluation_reports(
    evaluation: EvaluationResult,
    *,
    storage_dir: Path | None = None,
) -> dict[str, str]:
    root = storage_dir or (_EVALUATION_STORAGE / evaluation.run_id)
    root.mkdir(parents=True, exist_ok=True)

    json_path = root / "evaluation.json"
    html_path = root / "evaluation.html"
    payload = evaluation.to_dict()

    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    html_path.write_text(_render_html(evaluation), encoding="utf-8")

    return {
        "evaluation_json": str(json_path),
        "evaluation_html": str(html_path),
    }


def build_evaluation_report(
    result: dict[str, Any],
    *,
    evidence_package: dict[str, Any] | None = None,
    diagnosis_report: dict[str, Any] | None = None,
    goal: str | None = None,
    execution_summary: dict[str, Any] | None = None,
    write_reports: bool = True,
) -> dict[str, Any]:
    """Build evaluation scorecard and optional on-disk reports from existing run outputs."""
    evaluation = build_evaluation_result(
        result,
        evidence_package=evidence_package,
        diagnosis_report=diagnosis_report,
        goal=goal,
        execution_summary=execution_summary,
    )
    validation = validate_evaluation_result(evaluation)
    if not validation.valid:
        evaluation.summary.recommendations.insert(
            0,
            f"Evaluation validation warnings: {validation.message}",
        )

    if write_reports and evaluation.run_id:
        evaluation.report_paths = write_evaluation_reports(evaluation)

    report = evaluation.to_dict()
    report["validation"] = validation.to_dict()
    return report
