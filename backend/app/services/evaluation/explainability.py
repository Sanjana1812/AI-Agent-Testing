"""Sprint 5.3.1 — Evaluation explainability and trust layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

TRUST_LEVELS = ("VERY_HIGH", "HIGH", "MEDIUM", "LOW", "VERY_LOW")


@dataclass
class DimensionEvaluation:
    """Explainability output for a single evaluation dimension."""

    score: float
    summary: str = ""
    confidence: float | None = None
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    reasoning: str = ""
    recommendations: list[str] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "score": round(self.score, 1),
            "summary": self.summary,
            "strengths": list(self.strengths),
            "weaknesses": list(self.weaknesses),
            "reasoning": self.reasoning,
            "recommendations": list(self.recommendations),
        }
        if self.confidence is not None:
            payload["confidence"] = round(self.confidence, 1)
        if self.findings:
            payload["findings"] = list(self.findings)
        return payload


@dataclass
class TrustAssessment:
    trust_level: str
    trust_reason: str

    def to_dict(self) -> dict[str, str]:
        return {
            "trust_level": self.trust_level,
            "trust_reason": self.trust_reason,
        }


@dataclass
class OverallExplainability:
    reasoning: str
    strengths: list[str]
    weaknesses: list[str]
    recommendations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_reasoning": self.reasoning,
            "overall_strengths": list(self.strengths),
            "overall_weaknesses": list(self.weaknesses),
            "overall_recommendations": list(self.recommendations),
        }


def map_trust_level(overall_score: float) -> str:
    if overall_score >= 95:
        return "VERY_HIGH"
    if overall_score >= 85:
        return "HIGH"
    if overall_score >= 70:
        return "MEDIUM"
    if overall_score >= 50:
        return "LOW"
    return "VERY_LOW"


def build_trust_reason(
    *,
    trust_level: str,
    overall_score: float,
    planner_score: float,
    execution_score: float,
    evidence_score: float,
    diagnosis_score: float,
    goal_completion_score: float,
) -> str:
    scores = {
        "planner": planner_score,
        "execution": execution_score,
        "evidence": evidence_score,
        "diagnosis": diagnosis_score,
        "goal completion": goal_completion_score,
    }
    strong = [name for name, value in scores.items() if value >= 85]
    weak = [name for name, value in scores.items() if value < 70]

    if trust_level == "VERY_HIGH":
        return (
            "Nearly all requested functionality was verified with comprehensive evidence, "
            "consistent diagnosis, and strong planner alignment."
        )
    if trust_level == "HIGH":
        base = "Most requested functionality was verified successfully"
        if evidence_score >= 85:
            base += " with strong evidence"
        if diagnosis_score >= 85:
            base += " and consistent diagnosis"
        return base + "."

    if trust_level == "MEDIUM":
        parts = [f"Overall score is {overall_score:.0f}%."]
        if weak:
            parts.append(f"Lower confidence in {', '.join(weak)}.")
        if strong:
            parts.append(f"Strengths observed in {', '.join(strong)}.")
        return " ".join(parts)

    if trust_level == "LOW":
        return (
            f"Several dimensions scored below expectations ({', '.join(weak) or 'multiple areas'}); "
            "treat this run as indicative but not fully reliable."
        )

    return (
        "Significant gaps across planner, execution, evidence, or goal alignment reduce confidence "
        "in this evaluation."
    )


def assess_trust(
    *,
    overall_score: float,
    planner_score: float,
    execution_score: float,
    evidence_score: float,
    diagnosis_score: float,
    goal_completion_score: float,
) -> TrustAssessment:
    level = map_trust_level(overall_score)
    reason = build_trust_reason(
        trust_level=level,
        overall_score=overall_score,
        planner_score=planner_score,
        execution_score=execution_score,
        evidence_score=evidence_score,
        diagnosis_score=diagnosis_score,
        goal_completion_score=goal_completion_score,
    )
    return TrustAssessment(trust_level=level, trust_reason=reason)


def _ensure_non_empty(items: list[str], fallback: str) -> list[str]:
    cleaned = [item.strip() for item in items if item and item.strip()]
    return cleaned or [fallback]


def build_overall_explainability(
    *,
    overall_score: float,
    planner: DimensionEvaluation,
    execution: DimensionEvaluation,
    evidence: DimensionEvaluation,
    diagnosis: DimensionEvaluation,
    goal_completion: DimensionEvaluation,
    trust: TrustAssessment,
) -> OverallExplainability:
    strengths: list[str] = []
    weaknesses: list[str] = []
    recommendations: list[str] = []

    for dimension in (planner, execution, evidence, diagnosis, goal_completion):
        strengths.extend(dimension.strengths[:2])
        weaknesses.extend(dimension.weaknesses[:2])
        recommendations.extend(dimension.recommendations[:1])

    strengths = _ensure_non_empty(strengths[:6], f"Overall AI score reached {overall_score:.0f}%.")
    weaknesses = _ensure_non_empty(
        weaknesses[:6],
        "No major weaknesses detected across evaluation dimensions.",
    )
    recommendations = _ensure_non_empty(
        recommendations[:5],
        "Maintain current planner and execution quality for future runs.",
    )

    reasoning = (
        f"Overall AI score is {overall_score:.0f}% with {trust.trust_level.replace('_', ' ').title()} "
        f"trust. Planner ({planner.score:.0f}%), execution ({execution.score:.0f}%), "
        f"evidence ({evidence.score:.0f}%), diagnosis ({diagnosis.score:.0f}%), and "
        f"goal completion ({goal_completion.score:.0f}%) were combined using existing sprint weights. "
        f"{trust.trust_reason}"
    )

    return OverallExplainability(
        reasoning=reasoning,
        strengths=strengths,
        weaknesses=weaknesses,
        recommendations=recommendations,
    )


def validate_dimension_explainability(
    name: str,
    dimension: DimensionEvaluation,
    *,
    require_confidence: bool = False,
) -> list[str]:
    errors: list[str] = []
    if not dimension.reasoning:
        errors.append(f"{name} reasoning is missing")
    if not dimension.strengths:
        errors.append(f"{name} strengths are missing")
    if not dimension.weaknesses:
        errors.append(f"{name} weaknesses are missing")
    if not dimension.recommendations:
        errors.append(f"{name} recommendations are missing")
    if require_confidence and dimension.confidence is None:
        errors.append(f"{name} confidence is missing")
    return errors
