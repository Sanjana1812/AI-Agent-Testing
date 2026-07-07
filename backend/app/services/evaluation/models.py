"""Sprint 5.3 — Evaluation data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

EVALUATION_VERSION = "5.3.1"


@dataclass
class EvaluationCase:
    url: str
    goal: str
    expected_website_type: str = ""
    expected_business_goal: str = ""
    expected_journeys: list[str] = field(default_factory=list)
    expected_priority_areas: list[str] = field(default_factory=list)
    minimum_assertions: int = 0
    name: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> EvaluationCase:
        return cls(
            url=str(payload.get("url", "")),
            goal=str(payload.get("goal", "")),
            expected_website_type=str(payload.get("expected_website_type", "")),
            expected_business_goal=str(payload.get("expected_business_goal", "")),
            expected_journeys=list(payload.get("expected_journeys") or []),
            expected_priority_areas=list(payload.get("expected_priority_areas") or []),
            minimum_assertions=int(payload.get("minimum_assertions", 0)),
            name=str(payload.get("name", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "goal": self.goal,
            "expected_website_type": self.expected_website_type,
            "expected_business_goal": self.expected_business_goal,
            "expected_journeys": list(self.expected_journeys),
            "expected_priority_areas": list(self.expected_priority_areas),
            "minimum_assertions": self.minimum_assertions,
            "name": self.name,
        }


@dataclass
class EvaluationMetric:
    name: str
    score: float
    weight: float = 1.0
    details: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "score": round(self.score, 1),
            "weight": self.weight,
            "details": self.details,
        }


@dataclass
class EvaluationScorecard:
    planner_score: float = 0.0
    execution_score: float = 0.0
    evidence_score: float = 0.0
    diagnosis_score: float = 0.0
    goal_completion_score: float = 0.0
    overall_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "planner_score": round(self.planner_score, 1),
            "execution_score": round(self.execution_score, 1),
            "evidence_score": round(self.evidence_score, 1),
            "diagnosis_score": round(self.diagnosis_score, 1),
            "goal_completion_score": round(self.goal_completion_score, 1),
            "overall_score": round(self.overall_score, 1),
        }


@dataclass
class EvaluationSummary:
    planner_findings: list[str] = field(default_factory=list)
    execution_summary: str = ""
    evidence_summary: str = ""
    diagnosis_summary: str = ""
    goal_completion_summary: str = ""
    recommendations: list[str] = field(default_factory=list)
    planner_confidence: float | None = None
    planner_strengths: list[str] = field(default_factory=list)
    planner_weaknesses: list[str] = field(default_factory=list)
    planner_reasoning: str = ""
    planner_recommendations: list[str] = field(default_factory=list)
    execution_strengths: list[str] = field(default_factory=list)
    execution_weaknesses: list[str] = field(default_factory=list)
    execution_reasoning: str = ""
    execution_recommendations: list[str] = field(default_factory=list)
    evidence_strengths: list[str] = field(default_factory=list)
    evidence_weaknesses: list[str] = field(default_factory=list)
    evidence_reasoning: str = ""
    evidence_recommendations: list[str] = field(default_factory=list)
    diagnosis_strengths: list[str] = field(default_factory=list)
    diagnosis_weaknesses: list[str] = field(default_factory=list)
    diagnosis_reasoning: str = ""
    diagnosis_recommendations: list[str] = field(default_factory=list)
    goal_completion_strengths: list[str] = field(default_factory=list)
    goal_completion_weaknesses: list[str] = field(default_factory=list)
    goal_completion_reasoning: str = ""
    goal_completion_recommendations: list[str] = field(default_factory=list)
    trust_level: str = ""
    trust_reason: str = ""
    overall_reasoning: str = ""
    overall_strengths: list[str] = field(default_factory=list)
    overall_weaknesses: list[str] = field(default_factory=list)
    overall_recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "planner_findings": list(self.planner_findings),
            "execution_summary": self.execution_summary,
            "evidence_summary": self.evidence_summary,
            "diagnosis_summary": self.diagnosis_summary,
            "goal_completion_summary": self.goal_completion_summary,
            "recommendations": list(self.recommendations),
            "planner_confidence": self.planner_confidence,
            "planner_strengths": list(self.planner_strengths),
            "planner_weaknesses": list(self.planner_weaknesses),
            "planner_reasoning": self.planner_reasoning,
            "planner_recommendations": list(self.planner_recommendations),
            "execution_strengths": list(self.execution_strengths),
            "execution_weaknesses": list(self.execution_weaknesses),
            "execution_reasoning": self.execution_reasoning,
            "execution_recommendations": list(self.execution_recommendations),
            "evidence_strengths": list(self.evidence_strengths),
            "evidence_weaknesses": list(self.evidence_weaknesses),
            "evidence_reasoning": self.evidence_reasoning,
            "evidence_recommendations": list(self.evidence_recommendations),
            "diagnosis_strengths": list(self.diagnosis_strengths),
            "diagnosis_weaknesses": list(self.diagnosis_weaknesses),
            "diagnosis_reasoning": self.diagnosis_reasoning,
            "diagnosis_recommendations": list(self.diagnosis_recommendations),
            "goal_completion_strengths": list(self.goal_completion_strengths),
            "goal_completion_weaknesses": list(self.goal_completion_weaknesses),
            "goal_completion_reasoning": self.goal_completion_reasoning,
            "goal_completion_recommendations": list(self.goal_completion_recommendations),
            "trust_level": self.trust_level,
            "trust_reason": self.trust_reason,
            "overall_reasoning": self.overall_reasoning,
            "overall_strengths": list(self.overall_strengths),
            "overall_weaknesses": list(self.overall_weaknesses),
            "overall_recommendations": list(self.overall_recommendations),
        }


@dataclass
class EvaluationResult:
    run_id: str
    goal: str
    scorecard: EvaluationScorecard
    summary: EvaluationSummary
    metrics: list[EvaluationMetric] = field(default_factory=list)
    evaluation_case: EvaluationCase | None = None
    report_paths: dict[str, str] = field(default_factory=dict)
    version: str = EVALUATION_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "goal": self.goal,
            "version": self.version,
            "scorecard": self.scorecard.to_dict(),
            "summary": self.summary.to_dict(),
            "metrics": [metric.to_dict() for metric in self.metrics],
            "evaluation_case": self.evaluation_case.to_dict() if self.evaluation_case else None,
            "report_paths": dict(self.report_paths),
        }
