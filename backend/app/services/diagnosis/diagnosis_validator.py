"""Validate Sprint 4.2 DiagnosisReport payloads."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.services.diagnosis.models import (
    ConfidenceLabel,
    FailureType,
    FixComplexity,
    Ownership,
    SeverityLevel,
)


@dataclass
class DiagnosisReportValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class DiagnosisReportValidator:
    """Schema validation for DiagnosisReport dicts."""

    REQUIRED_FIELDS = (
        "failure_type",
        "root_cause",
        "severity",
        "confidence",
        "confidence_label",
        "business_impact",
        "recommendation",
        "developer_action",
        "qa_action",
        "next_steps",
        "supporting_evidence",
        "reasoning",
        "alternative_hypotheses",
        "ownership",
        "fix_complexity",
        "estimated_fix_time",
    )

    def validate(self, report: dict[str, Any] | None) -> DiagnosisReportValidationResult:
        errors: list[str] = []
        warnings: list[str] = []

        if not report:
            return DiagnosisReportValidationResult(valid=False, errors=["Diagnosis report is empty"])

        if not isinstance(report, dict):
            return DiagnosisReportValidationResult(valid=False, errors=["Diagnosis report must be a dict"])

        for field_name in self.REQUIRED_FIELDS:
            value = report.get(field_name)
            if value is None or (isinstance(value, str) and not value.strip()):
                errors.append(f"Missing required field: {field_name}")

        failure_type = report.get("failure_type")
        if failure_type and failure_type not in {t.value for t in FailureType}:
            errors.append(f"Invalid failure_type: {failure_type}")

        severity = report.get("severity")
        if severity and severity not in {s.value for s in SeverityLevel}:
            errors.append(f"Invalid severity: {severity}")

        ownership = report.get("ownership")
        if ownership and ownership not in {o.value for o in Ownership}:
            errors.append(f"Invalid ownership: {ownership}")

        complexity = report.get("fix_complexity")
        if complexity and complexity not in {c.value for c in FixComplexity}:
            errors.append(f"Invalid fix_complexity: {complexity}")

        label = report.get("confidence_label")
        if label and label not in {c.value for c in ConfidenceLabel}:
            errors.append(f"Invalid confidence_label: {label}")

        confidence = report.get("confidence")
        if confidence is not None:
            if not isinstance(confidence, (int, float)):
                errors.append("confidence must be numeric")
            elif not (0.0 <= float(confidence) <= 1.0):
                errors.append("confidence must be between 0 and 1")

        for list_field in ("next_steps", "supporting_evidence", "alternative_hypotheses"):
            value = report.get(list_field)
            if value is not None and not isinstance(value, list):
                errors.append(f"{list_field} must be a list")

        evidence = report.get("supporting_evidence") or []
        for index, item in enumerate(evidence):
            if not isinstance(item, dict):
                errors.append(f"supporting_evidence[{index}] must be a dict")
            elif not item.get("source") or not item.get("description"):
                errors.append(f"supporting_evidence[{index}] missing source or description")

        if not report.get("root_cause") and report.get("reasoning"):
            warnings.append("root_cause empty but reasoning present")

        return DiagnosisReportValidationResult(valid=not errors, errors=errors, warnings=warnings)
