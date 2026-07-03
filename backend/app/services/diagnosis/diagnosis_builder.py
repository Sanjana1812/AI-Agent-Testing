"""Assemble a complete DiagnosisReport from structured evidence."""

from __future__ import annotations

import logging
from typing import Any

from app.services.diagnosis.complexity_engine import estimate_complexity
from app.services.diagnosis.confidence_engine import compute_confidence
from app.services.diagnosis.failure_classifier import classify_failure
from app.services.diagnosis.models import DiagnosisReport
from app.services.diagnosis.ownership_engine import determine_ownership
from app.services.diagnosis.recommendation_engine import build_recommendations
from app.services.diagnosis.root_cause_analyzer import analyze_root_cause
from app.services.diagnosis.severity_engine import determine_severity

logger = logging.getLogger(__name__)


def _has_failures(evidence_package: dict[str, Any]) -> bool:
    summary = evidence_package.get("execution_summary") or {}
    if summary.get("failed_steps", 0) > 0:
        return True
    if summary.get("health") not in {None, "PASS"}:
        return True
    if evidence_package.get("failure_evidence"):
        return True
    return False


def build_diagnosis_report(
    evidence_package: dict[str, Any] | None,
    *,
    goal: str = "",
) -> dict[str, Any] | None:
    """
    Build a DiagnosisReport from an EvidencePackage dict.

    Returns None when the run passed with no failures (nothing to diagnose).
    """
    if not evidence_package or not isinstance(evidence_package, dict):
        return None

    if not _has_failures(evidence_package):
        return None

    failure_type = classify_failure(evidence_package, goal=goal)
    analysis = analyze_root_cause(evidence_package, failure_type, goal=goal)

    recommendations = build_recommendations(
        failure_type,
        determine_severity(
            failure_type,
            evidence_package,
            business_impact_hint=analysis.get("root_cause", ""),
        ),
        determine_ownership(failure_type),
        evidence_package,
        root_cause=analysis.get("root_cause", ""),
        navigation_mapping=analysis.get("navigation_mapping_override"),
    )

    severity = determine_severity(
        failure_type,
        evidence_package,
        business_impact_hint=recommendations["business_impact"],
    )
    ownership = determine_ownership(failure_type)
    complexity, fix_time = estimate_complexity(failure_type, severity)
    confidence, confidence_label = compute_confidence(
        evidence_package,
        failure_type,
        analysis.get("supporting_evidence", []),
        analysis.get("alternative_hypotheses", []),
    )

    report = DiagnosisReport(
        failure_type=failure_type.value,
        root_cause=analysis["root_cause"],
        severity=severity.value,
        confidence=confidence,
        confidence_label=confidence_label.value,
        business_impact=recommendations["business_impact"],
        recommendation=recommendations["recommendation"],
        developer_action=recommendations["developer_action"],
        qa_action=recommendations["qa_action"],
        next_steps=recommendations["next_steps"],
        supporting_evidence=analysis["supporting_evidence"],
        reasoning=analysis["reasoning"],
        alternative_hypotheses=analysis["alternative_hypotheses"],
        ownership=ownership.value,
        fix_complexity=complexity.value,
        estimated_fix_time=fix_time,
    )

    logger.info(
        "[Diagnosis] Built report type=%s severity=%s confidence=%.0f%%",
        report.failure_type,
        report.severity,
        report.confidence * 100,
    )
    return report.to_dict()
