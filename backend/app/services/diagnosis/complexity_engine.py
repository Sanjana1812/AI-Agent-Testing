"""Estimate fix complexity and time from failure type and severity."""

from __future__ import annotations

from app.services.diagnosis.models import FailureType, FixComplexity, SeverityLevel


_COMPLEXITY_MAP: dict[FailureType, tuple[FixComplexity, str]] = {
    FailureType.TEST_DESIGN: (FixComplexity.LOW, "30 minutes"),
    FailureType.AI_PLANNING: (FixComplexity.MEDIUM, "2 hours"),
    FailureType.SELECTOR: (FixComplexity.LOW, "15 minutes"),
    FailureType.ASSERTION: (FixComplexity.LOW, "30 minutes"),
    FailureType.TIMING: (FixComplexity.MEDIUM, "1 hour"),
    FailureType.NAVIGATION: (FixComplexity.MEDIUM, "2 hours"),
    FailureType.NETWORK: (FixComplexity.HIGH, "1 day"),
    FailureType.APPLICATION: (FixComplexity.HIGH, "1 day"),
    FailureType.AUTHENTICATION: (FixComplexity.HIGH, "1 day"),
    FailureType.DATA: (FixComplexity.MEDIUM, "4 hours"),
    FailureType.ENVIRONMENT: (FixComplexity.MEDIUM, "1 hour"),
    FailureType.UNKNOWN: (FixComplexity.MEDIUM, "2 hours"),
}


def estimate_complexity(
    failure_type: FailureType,
    severity: SeverityLevel,
) -> tuple[FixComplexity, str]:
    """Return fix complexity label and human-readable time estimate."""
    complexity, fix_time = _COMPLEXITY_MAP.get(
        failure_type, (FixComplexity.MEDIUM, "2 hours")
    )
    if severity == SeverityLevel.CRITICAL and complexity == FixComplexity.LOW:
        return FixComplexity.MEDIUM, "2 hours"
    if severity == SeverityLevel.CRITICAL and failure_type == FailureType.APPLICATION:
        return FixComplexity.HIGH, "2 days"
    return complexity, fix_time
