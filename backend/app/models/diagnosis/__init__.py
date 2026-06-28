"""Diagnosis and failure data models for Sprint 4."""

from app.models.diagnosis.diagnosis import Diagnosis
from app.models.diagnosis.evidence import Evidence, EvidenceSource
from app.models.diagnosis.failure import RichFailure
from app.models.diagnosis.failure_categories import FailureCategory, FAILURE_TYPE_TO_CATEGORY
from app.models.diagnosis.severity import Severity
from app.models.diagnosis.suggested_fix import SuggestedFix, SuggestedFixType

__all__ = [
    "Diagnosis",
    "Evidence",
    "EvidenceSource",
    "RichFailure",
    "FailureCategory",
    "FAILURE_TYPE_TO_CATEGORY",
    "Severity",
    "SuggestedFix",
    "SuggestedFixType",
]
