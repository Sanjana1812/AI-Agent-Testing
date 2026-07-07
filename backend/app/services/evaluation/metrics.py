"""Aggregate evaluation metric scores."""

from __future__ import annotations

from app.services.evaluation.models import EvaluationMetric, EvaluationScorecard

_METRIC_WEIGHTS = {
    "planner": 0.25,
    "execution": 0.25,
    "evidence": 0.15,
    "diagnosis": 0.15,
    "goal_completion": 0.20,
}


def build_metrics(
    *,
    planner_score: float,
    execution_score: float,
    evidence_score: float,
    diagnosis_score: float,
    goal_completion_score: float,
) -> list[EvaluationMetric]:
    return [
        EvaluationMetric("planner", planner_score, _METRIC_WEIGHTS["planner"]),
        EvaluationMetric("execution", execution_score, _METRIC_WEIGHTS["execution"]),
        EvaluationMetric("evidence", evidence_score, _METRIC_WEIGHTS["evidence"]),
        EvaluationMetric("diagnosis", diagnosis_score, _METRIC_WEIGHTS["diagnosis"]),
        EvaluationMetric("goal_completion", goal_completion_score, _METRIC_WEIGHTS["goal_completion"]),
    ]


def calculate_overall_score(metrics: list[EvaluationMetric]) -> float:
    total_weight = sum(metric.weight for metric in metrics)
    if total_weight <= 0:
        return 0.0
    weighted = sum(metric.score * metric.weight for metric in metrics)
    return round(weighted / total_weight, 1)


def build_scorecard(
    *,
    planner_score: float,
    execution_score: float,
    evidence_score: float,
    diagnosis_score: float,
    goal_completion_score: float,
) -> EvaluationScorecard:
    metrics = build_metrics(
        planner_score=planner_score,
        execution_score=execution_score,
        evidence_score=evidence_score,
        diagnosis_score=diagnosis_score,
        goal_completion_score=goal_completion_score,
    )
    overall = calculate_overall_score(metrics)
    return EvaluationScorecard(
        planner_score=planner_score,
        execution_score=execution_score,
        evidence_score=evidence_score,
        diagnosis_score=diagnosis_score,
        goal_completion_score=goal_completion_score,
        overall_score=overall,
    )
