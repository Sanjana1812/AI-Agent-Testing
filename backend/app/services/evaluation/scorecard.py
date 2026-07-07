"""Build evaluation scorecards from evaluator outputs."""

from __future__ import annotations

from typing import Any

from app.services.evaluation.dataset import find_matching_case
from app.services.evaluation.diagnosis_evaluator import evaluate_diagnosis_detail
from app.services.evaluation.evidence_evaluator import evaluate_evidence_detail
from app.services.evaluation.execution_evaluator import evaluate_execution_detail
from app.services.evaluation.explainability import assess_trust, build_overall_explainability
from app.services.evaluation.goal_completion import evaluate_goal_completion_detail
from app.services.evaluation.metrics import build_metrics, build_scorecard
from app.services.evaluation.models import EvaluationResult, EvaluationSummary
from app.services.evaluation.planner_evaluator import evaluate_planner_detail


def _merge_recommendations(*groups: list[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for group in groups:
        for item in group:
            if item and item not in seen:
                seen.add(item)
                merged.append(item)
    return merged


def build_evaluation_result(
    result: dict[str, Any],
    *,
    evidence_package: dict[str, Any] | None = None,
    diagnosis_report: dict[str, Any] | None = None,
    goal: str | None = None,
    execution_summary: dict[str, Any] | None = None,
) -> EvaluationResult:
    run_id = str(result.get("id") or "")
    stated_goal = goal or str(result.get("goal") or "")
    evaluation_case = find_matching_case(url=str(result.get("url") or ""), goal=stated_goal)
    if execution_summary and not result.get("execution_summary"):
        result = dict(result)
        result["execution_summary"] = execution_summary

    planner = evaluate_planner_detail(result, evaluation_case=evaluation_case)
    execution = evaluate_execution_detail(result)
    evidence = evaluate_evidence_detail(evidence_package, result)
    diagnosis = evaluate_diagnosis_detail(diagnosis_report, evidence_package)
    goal_completion = evaluate_goal_completion_detail(result, goal=stated_goal)

    scorecard = build_scorecard(
        planner_score=planner.score,
        execution_score=execution.score,
        evidence_score=evidence.score,
        diagnosis_score=diagnosis.score,
        goal_completion_score=goal_completion.score,
    )
    metrics = build_metrics(
        planner_score=planner.score,
        execution_score=execution.score,
        evidence_score=evidence.score,
        diagnosis_score=diagnosis.score,
        goal_completion_score=goal_completion.score,
    )
    trust = assess_trust(
        overall_score=scorecard.overall_score,
        planner_score=planner.score,
        execution_score=execution.score,
        evidence_score=evidence.score,
        diagnosis_score=diagnosis.score,
        goal_completion_score=goal_completion.score,
    )
    overall = build_overall_explainability(
        overall_score=scorecard.overall_score,
        planner=planner,
        execution=execution,
        evidence=evidence,
        diagnosis=diagnosis,
        goal_completion=goal_completion,
        trust=trust,
    )

    summary = EvaluationSummary(
        planner_findings=planner.findings,
        execution_summary=execution.summary,
        evidence_summary=evidence.summary,
        diagnosis_summary=diagnosis.summary,
        goal_completion_summary=goal_completion.summary,
        recommendations=_merge_recommendations(
            planner.recommendations,
            execution.recommendations,
            evidence.recommendations,
            diagnosis.recommendations,
            goal_completion.recommendations,
            overall.recommendations,
        ),
        planner_confidence=planner.confidence,
        planner_strengths=planner.strengths,
        planner_weaknesses=planner.weaknesses,
        planner_reasoning=planner.reasoning,
        planner_recommendations=planner.recommendations,
        execution_strengths=execution.strengths,
        execution_weaknesses=execution.weaknesses,
        execution_reasoning=execution.reasoning,
        execution_recommendations=execution.recommendations,
        evidence_strengths=evidence.strengths,
        evidence_weaknesses=evidence.weaknesses,
        evidence_reasoning=evidence.reasoning,
        evidence_recommendations=evidence.recommendations,
        diagnosis_strengths=diagnosis.strengths,
        diagnosis_weaknesses=diagnosis.weaknesses,
        diagnosis_reasoning=diagnosis.reasoning,
        diagnosis_recommendations=diagnosis.recommendations,
        goal_completion_strengths=goal_completion.strengths,
        goal_completion_weaknesses=goal_completion.weaknesses,
        goal_completion_reasoning=goal_completion.reasoning,
        goal_completion_recommendations=goal_completion.recommendations,
        trust_level=trust.trust_level,
        trust_reason=trust.trust_reason,
        overall_reasoning=overall.reasoning,
        overall_strengths=overall.strengths,
        overall_weaknesses=overall.weaknesses,
        overall_recommendations=overall.recommendations,
    )
    return EvaluationResult(
        run_id=run_id,
        goal=stated_goal,
        scorecard=scorecard,
        summary=summary,
        metrics=metrics,
        evaluation_case=evaluation_case,
    )
