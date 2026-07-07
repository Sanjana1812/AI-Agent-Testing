"""Read-only planner quality evaluation."""

from __future__ import annotations

import re
from typing import Any

from app.services.evaluation.explainability import DimensionEvaluation
from app.services.evaluation.models import EvaluationCase

_GENERIC_LABELS = re.compile(
    r"(interaction|step|open website|open page|wait\s+\d+ms)",
    re.IGNORECASE,
)


def _evaluate_planner_detail(
    result: dict[str, Any],
    *,
    evaluation_case: EvaluationCase | None = None,
) -> DimensionEvaluation:
    findings: list[str] = []
    meta = result.get("ai_plan_metadata") or {}
    plan = result.get("ai_plan") or []
    goal = str(result.get("goal") or "")
    website_summary = result.get("website_context_summary") or {}

    scores: list[float] = []
    strengths: list[str] = []
    weaknesses: list[str] = []
    recommendations: list[str] = []

    if goal.strip():
        scores.append(95.0)
        findings.append("Testing goal was provided and understood by the planner pipeline.")
        strengths.append("Goal correctly understood by the planner pipeline.")
    else:
        scores.append(20.0)
        findings.append("Testing goal was missing from the run result.")
        weaknesses.append("Testing goal was missing from the run result.")

    priority = meta.get("execution_priority") or meta.get("testing_priority") or []
    journey = meta.get("generated_journey") or []
    if plan:
        action_types = {step.get("action") for step in plan if isinstance(step, dict)}
        has_nav = "click" in action_types or "open_page" in action_types
        has_verify = any(
            str(step.get("action", "")).startswith("verify") for step in plan if isinstance(step, dict)
        )
        relevance = 70.0
        if has_nav:
            relevance += 10.0
            strengths.append("Navigation actions included in the plan.")
        if has_verify:
            relevance += 10.0
            strengths.append("Verification steps included in the plan.")
        if priority:
            relevance += 5.0
            strengths.append("Execution priority areas informed the plan.")
        scores.append(min(relevance, 100.0))
        findings.append(
            f"Planner produced {len(plan)} steps with navigation={'yes' if has_nav else 'no'} "
            f"and verification={'yes' if has_verify else 'no'}."
        )
        if not has_nav:
            weaknesses.append("Plan lacks explicit navigation steps.")
        if not has_verify:
            weaknesses.append("Plan lacks verification steps.")
    else:
        scores.append(0.0)
        findings.append("No executable plan was produced.")
        weaknesses.append("No executable plan was produced.")

    labels = [
        str(step.get("label") or step.get("action") or "")
        for step in plan
        if isinstance(step, dict)
    ]
    generic_count = sum(1 for label in labels if _GENERIC_LABELS.search(label))
    generic_rate = (generic_count / len(labels)) if labels else 1.0
    generic_score = max(0.0, 100.0 - generic_rate * 100.0)
    scores.append(generic_score)
    findings.append(f"Generic step rate: {generic_rate * 100:.0f}% ({generic_count}/{len(labels) or 0}).")
    if generic_count:
        weaknesses.append("Generic verification or interaction step detected.")
        recommendations.append(
            "Replace generic verification steps with semantic, goal-aligned validations."
        )

    if priority:
        covered = 0
        plan_text = " ".join(labels).lower()
        missing_priority: list[str] = []
        for area in priority[:5]:
            if str(area).lower() in plan_text:
                covered += 1
            else:
                missing_priority.append(str(area))
        priority_score = (covered / len(priority[:5])) * 100.0
        scores.append(priority_score)
        findings.append(f"Execution priority coverage: {covered}/{len(priority[:5])} areas reflected in plan.")
        if covered:
            strengths.append(f"{covered} execution priority area(s) reflected in the plan.")
        for area in missing_priority[:2]:
            weaknesses.append(f"{area} priority area missing from plan.")
            recommendations.append(f"Add planner steps covering {area}.")
    else:
        scores.append(75.0)
        findings.append("No explicit execution priority list was available; using neutral priority score.")

    if journey:
        unique = len({item.lower() for item in journey if item})
        journey_score = min(100.0, 60.0 + unique * 8.0)
        scores.append(journey_score)
        findings.append(f"Semantic journey contains {unique} distinct destinations.")
        strengths.append(f"Semantic journey includes {unique} distinct destination(s).")
    else:
        scores.append(65.0)
        findings.append("Generated journey metadata was not available.")
        weaknesses.append("Generated journey metadata was not available.")

    if evaluation_case:
        if evaluation_case.expected_website_type:
            detected = meta.get("website_type") or website_summary.get("website_type") or ""
            if evaluation_case.expected_website_type.lower() in str(detected).lower():
                scores.append(100.0)
                findings.append("Detected website type aligns with evaluation case expectation.")
            else:
                scores.append(70.0)
                findings.append("Website type differs from benchmark expectation (informational only).")

    planner_score = sum(scores) / len(scores) if scores else 0.0
    confidence = round(min(100.0, sum(scores) / max(len(scores), 1)), 1)

    if not strengths:
        strengths.append("Planner produced a runnable test plan.")
    if not weaknesses:
        weaknesses.append("No significant planner weaknesses detected.")
    if not recommendations:
        recommendations.append("Maintain semantic step labels and priority-aligned planning.")

    reasoning = (
        f"Planner score {planner_score:.0f}% from goal understanding, step relevance, "
        f"generic step rate ({generic_rate * 100:.0f}%), priority coverage, and journey quality. "
        + " ".join(findings[:3])
    )

    return DimensionEvaluation(
        score=round(planner_score, 1),
        summary=" ".join(findings[:2]),
        confidence=confidence,
        strengths=strengths,
        weaknesses=weaknesses,
        reasoning=reasoning,
        recommendations=recommendations,
        findings=findings,
    )


def evaluate_planner(
    result: dict[str, Any],
    *,
    evaluation_case: EvaluationCase | None = None,
) -> tuple[float, list[str]]:
    detail = _evaluate_planner_detail(result, evaluation_case=evaluation_case)
    return detail.score, detail.findings


def evaluate_planner_detail(
    result: dict[str, Any],
    *,
    evaluation_case: EvaluationCase | None = None,
) -> DimensionEvaluation:
    return _evaluate_planner_detail(result, evaluation_case=evaluation_case)
