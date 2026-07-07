"""Read-only diagnosis quality evaluation."""

from __future__ import annotations

from typing import Any

from app.services.evaluation.explainability import DimensionEvaluation

_REQUIRED_FIELDS = (
    "failure_type",
    "root_cause",
    "severity",
    "confidence",
    "recommendation",
    "developer_action",
    "qa_action",
)


def _evaluate_diagnosis_detail(
    diagnosis_report: dict[str, Any] | None,
    evidence_package: dict[str, Any] | None = None,
) -> DimensionEvaluation:
    summary = (evidence_package or {}).get("execution_summary") or {}
    has_failures = (
        summary.get("failed_steps", 0) > 0
        or summary.get("health") not in {None, "PASS"}
        or bool((evidence_package or {}).get("failure_evidence"))
    )

    if not has_failures:
        return DimensionEvaluation(
            score=100.0,
            summary="Run passed with no failures; diagnosis not required.",
            strengths=["No failures detected; diagnosis not required."],
            weaknesses=["No failure diagnosis was needed for this passing run."],
            reasoning="Run completed without failures, so diagnosis quality is scored at maximum.",
            recommendations=["Continue monitoring diagnosis output on failing runs."],
        )

    if not diagnosis_report:
        return DimensionEvaluation(
            score=0.0,
            summary="Failures occurred but no diagnosis report was generated.",
            strengths=["Failure state was detected."],
            weaknesses=["Failures occurred but no diagnosis report was generated."],
            reasoning="Execution failures were present without a corresponding diagnosis report.",
            recommendations=["Ensure diagnosis engine runs after evidence collection on failed runs."],
        )

    present = sum(1 for field in _REQUIRED_FIELDS if diagnosis_report.get(field))
    score = (present / len(_REQUIRED_FIELDS)) * 100.0

    strengths: list[str] = []
    weaknesses: list[str] = []
    recommendations: list[str] = []

    if diagnosis_report.get("root_cause"):
        strengths.append("Root cause identified.")
    else:
        weaknesses.append("Root cause not documented.")
    if diagnosis_report.get("severity"):
        strengths.append("Severity assigned.")
    if diagnosis_report.get("developer_action"):
        strengths.append("Developer recommendation available.")
    if diagnosis_report.get("qa_action"):
        strengths.append("QA action guidance available.")
    if diagnosis_report.get("recommendation"):
        strengths.append("Remediation recommendation provided.")

    if diagnosis_report.get("reasoning"):
        score = min(score + 5.0, 100.0)
        strengths.append("Diagnosis includes reasoning narrative.")
    if diagnosis_report.get("supporting_evidence"):
        score = min(score + 5.0, 100.0)
        strengths.append("Supporting evidence cited in diagnosis.")
    else:
        weaknesses.append("Confidence reduced because supporting evidence was limited.")
        recommendations.append("Include supporting evidence references in diagnosis output.")

    if diagnosis_report.get("next_steps"):
        score = min(score + 5.0, 100.0)

    confidence = diagnosis_report.get("confidence")
    if isinstance(confidence, (int, float)) and confidence >= 0.7:
        score = min(score + 5.0, 100.0)
    elif isinstance(confidence, (int, float)) and confidence < 0.7:
        weaknesses.append("Diagnosis confidence is below the high-confidence threshold.")

    if present < len(_REQUIRED_FIELDS):
        missing = [field for field in _REQUIRED_FIELDS if not diagnosis_report.get(field)]
        weaknesses.append(f"Missing diagnosis fields: {', '.join(missing[:3])}.")
        recommendations.append("Complete all required diagnosis fields for failed runs.")

    if not recommendations:
        recommendations.append("Diagnosis quality is strong; maintain field completeness on failures.")

    diagnosis_summary = (
        f"Diagnosis covered {present}/{len(_REQUIRED_FIELDS)} required fields "
        f"with failure_type={diagnosis_report.get('failure_type')} "
        f"and confidence={diagnosis_report.get('confidence_label') or diagnosis_report.get('confidence')}."
    )

    reasoning = (
        f"Diagnosis score {score:.0f}% from {present}/{len(_REQUIRED_FIELDS)} required fields"
        + (" with supporting evidence." if diagnosis_report.get("supporting_evidence") else ".")
    )

    return DimensionEvaluation(
        score=round(score, 1),
        summary=diagnosis_summary,
        strengths=strengths,
        weaknesses=weaknesses,
        reasoning=reasoning,
        recommendations=recommendations,
    )


def evaluate_diagnosis(
    diagnosis_report: dict[str, Any] | None,
    evidence_package: dict[str, Any] | None = None,
) -> tuple[float, str]:
    detail = _evaluate_diagnosis_detail(diagnosis_report, evidence_package)
    return detail.score, detail.summary


def evaluate_diagnosis_detail(
    diagnosis_report: dict[str, Any] | None,
    evidence_package: dict[str, Any] | None = None,
) -> DimensionEvaluation:
    return _evaluate_diagnosis_detail(diagnosis_report, evidence_package)
