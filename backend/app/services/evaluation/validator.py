"""Validate evaluation outputs and dataset cases."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.evaluation.dataset import validate_case_payload
from app.services.evaluation.explainability import TRUST_LEVELS
from app.services.evaluation.models import EvaluationCase, EvaluationResult, EvaluationScorecard


@dataclass
class ValidationResult:
    valid: bool
    message: str = ""
    errors: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "message": self.message,
            "errors": list(self.errors or []),
        }


def _score_in_range(score: float, name: str, errors: list[str]) -> None:
    if score < 0 or score > 100:
        errors.append(f"{name} score out of range: {score}")


def validate_scorecard(scorecard: EvaluationScorecard) -> ValidationResult:
    errors: list[str] = []
    _score_in_range(scorecard.planner_score, "planner", errors)
    _score_in_range(scorecard.execution_score, "execution", errors)
    _score_in_range(scorecard.evidence_score, "evidence", errors)
    _score_in_range(scorecard.diagnosis_score, "diagnosis", errors)
    _score_in_range(scorecard.goal_completion_score, "goal_completion", errors)
    _score_in_range(scorecard.overall_score, "overall", errors)
    if errors:
        return ValidationResult(valid=False, message="Scorecard validation failed.", errors=errors)
    return ValidationResult(valid=True, message="Scorecard valid.")


def _validate_summary_explainability(summary: Any) -> list[str]:
    errors: list[str] = []
    dimensions = (
        ("planner", True),
        ("execution", False),
        ("evidence", False),
        ("diagnosis", False),
        ("goal_completion", False),
    )
    for prefix, require_confidence in dimensions:
        if not getattr(summary, f"{prefix}_reasoning", ""):
            errors.append(f"{prefix} reasoning is missing")
        if not getattr(summary, f"{prefix}_strengths", []):
            errors.append(f"{prefix} strengths are missing")
        if not getattr(summary, f"{prefix}_weaknesses", []):
            errors.append(f"{prefix} weaknesses are missing")
        if not getattr(summary, f"{prefix}_recommendations", []):
            errors.append(f"{prefix} recommendations are missing")
        if require_confidence and summary.planner_confidence is None:
            errors.append("planner confidence is missing")

    if not summary.trust_level:
        errors.append("trust_level is missing")
    elif summary.trust_level not in TRUST_LEVELS:
        errors.append(f"invalid trust_level: {summary.trust_level}")
    if not summary.trust_reason:
        errors.append("trust_reason is missing")
    if not summary.overall_reasoning:
        errors.append("overall_reasoning is missing")
    if not summary.overall_strengths:
        errors.append("overall_strengths are missing")
    if not summary.overall_weaknesses:
        errors.append("overall_weaknesses are missing")
    if not summary.overall_recommendations:
        errors.append("overall_recommendations are missing")
    return errors


def validate_evaluation_result(evaluation: EvaluationResult) -> ValidationResult:
    errors: list[str] = []
    if not evaluation.run_id:
        errors.append("run_id is missing")
    if not evaluation.goal:
        errors.append("goal is missing")
    if not evaluation.metrics:
        errors.append("metrics are missing")

    scorecard_validation = validate_scorecard(evaluation.scorecard)
    if not scorecard_validation.valid:
        errors.extend(scorecard_validation.errors or [])

    if not evaluation.summary.execution_summary:
        errors.append("execution_summary is missing")
    if not evaluation.summary.evidence_summary:
        errors.append("evidence_summary is missing")

    errors.extend(_validate_summary_explainability(evaluation.summary))

    if errors:
        return ValidationResult(valid=False, message="Evaluation result validation failed.", errors=errors)
    return ValidationResult(valid=True, message="Evaluation result valid.")


def validate_evaluation_case(case: EvaluationCase | dict[str, Any]) -> ValidationResult:
    payload = case.to_dict() if isinstance(case, EvaluationCase) else case
    errors = validate_case_payload(payload)
    if errors:
        return ValidationResult(valid=False, message="Invalid evaluation case.", errors=errors)
    return ValidationResult(valid=True, message="Evaluation case valid.")
