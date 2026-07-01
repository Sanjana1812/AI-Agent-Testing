"""Validate AI diagnosis responses before they reach the API layer."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.diagnosis.evidence import EvidenceSource
from app.models.diagnosis.failure_categories import FailureCategory
from app.models.diagnosis.severity import Severity
from app.models.diagnosis.suggested_fix import SuggestedFixType


@dataclass
class DiagnosisValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class DiagnosisValidator:
    """Schema and semantic validation for future AI-generated diagnoses."""

    REQUIRED_FIELDS = ("summary", "root_cause", "category", "severity", "confidence", "evidence")
    OPTIONAL_FIELDS = ("recommendations", "suggested_fix", "provider", "latency_ms")

    def __init__(self, *, min_confidence: float = 0.0, max_confidence: float = 1.0) -> None:
        self.min_confidence = min_confidence
        self.max_confidence = max_confidence

    def validate(self, diagnosis: dict | None) -> DiagnosisValidationResult:
        errors: list[str] = []
        warnings: list[str] = []

        if not diagnosis:
            return DiagnosisValidationResult(valid=False, errors=["Diagnosis payload is empty"])

        if not isinstance(diagnosis, dict):
            return DiagnosisValidationResult(valid=False, errors=["Diagnosis must be a dict"])

        for field_name in self.REQUIRED_FIELDS:
            value = diagnosis.get(field_name)
            if value is None or (isinstance(value, str) and not value.strip()):
                errors.append(f"Missing required field: {field_name}")

        confidence = diagnosis.get("confidence")
        if confidence is not None:
            if not isinstance(confidence, (int, float)):
                errors.append("confidence must be numeric")
            elif not (self.min_confidence <= float(confidence) <= self.max_confidence):
                errors.append(
                    f"confidence must be between {self.min_confidence} and {self.max_confidence}"
                )

        category = diagnosis.get("category")
        if category is not None:
            valid_categories = {c.value for c in FailureCategory}
            if category not in valid_categories:
                errors.append(f"Invalid category: {category}")

        severity = diagnosis.get("severity")
        if severity is not None:
            valid_severities = {s.value for s in Severity}
            if severity not in valid_severities:
                errors.append(f"Invalid severity: {severity}")

        evidence = diagnosis.get("evidence")
        if evidence is not None:
            if not isinstance(evidence, list):
                errors.append("evidence must be a list")
            else:
                errors.extend(self._validate_evidence_list(evidence))

        recommendations = diagnosis.get("recommendations")
        if recommendations is not None:
            if not isinstance(recommendations, list):
                errors.append("recommendations must be a list")
            elif not all(isinstance(item, str) for item in recommendations):
                errors.append("recommendations must contain strings")

        suggested_fix = diagnosis.get("suggested_fix")
        if suggested_fix is not None:
            errors.extend(self._validate_suggested_fix(suggested_fix))

        provider = diagnosis.get("provider")
        if provider is not None and not isinstance(provider, str):
            errors.append("provider must be a string")

        latency_ms = diagnosis.get("latency_ms")
        if latency_ms is not None:
            if not isinstance(latency_ms, int) or latency_ms < 0:
                errors.append("latency_ms must be a non-negative integer")

        if not diagnosis.get("root_cause") and diagnosis.get("summary"):
            warnings.append("root_cause is empty but summary is present")

        return DiagnosisValidationResult(valid=not errors, errors=errors, warnings=warnings)

    def _validate_evidence_list(self, evidence: list) -> list[str]:
        errors: list[str] = []
        valid_sources = {source.value for source in EvidenceSource}

        if not evidence:
            errors.append("evidence must contain at least one item")
            return errors

        for index, item in enumerate(evidence):
            if not isinstance(item, dict):
                errors.append(f"evidence[{index}] must be a dict")
                continue

            source = item.get("source")
            if not source:
                errors.append(f"evidence[{index}] missing source")
            elif source not in valid_sources:
                errors.append(f"evidence[{index}] has invalid source: {source}")

            if not item.get("description"):
                errors.append(f"evidence[{index}] missing description")

            item_confidence = item.get("confidence")
            if item_confidence is not None:
                if not isinstance(item_confidence, (int, float)):
                    errors.append(f"evidence[{index}].confidence must be numeric")
                elif not (0.0 <= float(item_confidence) <= 1.0):
                    errors.append(f"evidence[{index}].confidence out of range")

        return errors

    def _validate_suggested_fix(self, suggested_fix: dict) -> list[str]:
        errors: list[str] = []
        if not isinstance(suggested_fix, dict):
            return ["suggested_fix must be a dict"]

        fix_type = suggested_fix.get("type")
        if fix_type and fix_type not in {t.value for t in SuggestedFixType}:
            errors.append(f"Invalid suggested_fix.type: {fix_type}")

        for field_name in ("title", "description"):
            value = suggested_fix.get(field_name)
            if value is not None and not isinstance(value, str):
                errors.append(f"suggested_fix.{field_name} must be a string")

        return errors
