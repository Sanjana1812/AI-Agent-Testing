"""Sprint 5.3 — Evaluation & Validation Framework (read-only)."""

from app.services.evaluation.dataset import (
    dataset_root,
    find_matching_case,
    load_all_cases,
    load_evaluation_case,
)
from app.services.evaluation.models import (
    EVALUATION_VERSION,
    EvaluationCase,
    EvaluationMetric,
    EvaluationResult,
    EvaluationScorecard,
    EvaluationSummary,
)
from app.services.evaluation.explainability import (
    DimensionEvaluation,
    OverallExplainability,
    TrustAssessment,
    assess_trust,
    build_overall_explainability,
    map_trust_level,
)

from app.services.evaluation.report import build_evaluation_report

__all__ = [
    "EVALUATION_VERSION",
    "DimensionEvaluation",
    "EvaluationCase",
    "EvaluationMetric",
    "EvaluationResult",
    "EvaluationScorecard",
    "EvaluationSummary",
    "OverallExplainability",
    "TrustAssessment",
    "assess_trust",
    "build_evaluation_report",
    "build_overall_explainability",
    "dataset_root",
    "find_matching_case",
    "load_all_cases",
    "load_evaluation_case",
    "map_trust_level",
]
