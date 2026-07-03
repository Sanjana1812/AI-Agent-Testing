"""Compute diagnosis confidence from evidence completeness."""

from __future__ import annotations

from typing import Any

from app.services.diagnosis.models import ConfidenceLabel, FailureType


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def compute_confidence(
    evidence_package: dict[str, Any],
    failure_type: FailureType,
    supporting_evidence: list[dict[str, Any]],
    alternative_hypotheses: list[str],
) -> tuple[float, ConfidenceLabel]:
    """Return confidence score (0-1) and label from available signals."""
    score = 0.35

    failure_records = evidence_package.get("failure_evidence") or []
    if failure_records:
        score += 0.15
        record = failure_records[0] if isinstance(failure_records[0], dict) else {}
        if record.get("selector_attempted") or record.get("exception"):
            score += 0.08
        if record.get("dom_snapshot"):
            score += 0.05
        if record.get("console_errors"):
            score += 0.04
        if record.get("network_errors"):
            score += 0.04

    coverage = evidence_package.get("coverage_report") or {}
    if coverage.get("areas"):
        score += 0.06
    if coverage.get("estimated_coverage_percent") is not None:
        score += 0.04

    planner = evidence_package.get("planner_metadata") or {}
    if planner.get("planner_confidence") is not None:
        score += min(0.08, float(planner["planner_confidence"]) * 0.08)
    if planner.get("confidence_breakdown") or evidence_package.get("explainability_records"):
        score += 0.05

    analysis = evidence_package.get("website_analysis") or {}
    analysis_conf = analysis.get("confidence") or analysis.get("analysis_confidence")
    if analysis_conf is not None:
        score += min(0.06, float(analysis_conf) * 0.06)

    assertions = evidence_package.get("assertions") or []
    if assertions:
        score += 0.05

    if len(supporting_evidence) >= 4:
        score += 0.06
    elif len(supporting_evidence) >= 2:
        score += 0.03

    if failure_type == FailureType.UNKNOWN:
        score -= 0.15
    elif failure_type == FailureType.TEST_DESIGN:
        score += 0.08

    if len(alternative_hypotheses) > 2:
        score -= 0.05

    final = _clamp(score)
    if final >= 0.75:
        return final, ConfidenceLabel.HIGH
    if final >= 0.5:
        return final, ConfidenceLabel.MEDIUM
    return final, ConfidenceLabel.LOW
