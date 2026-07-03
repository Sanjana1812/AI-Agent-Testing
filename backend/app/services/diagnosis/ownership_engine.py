"""Assign likely fix ownership from failure classification."""

from __future__ import annotations

from app.services.diagnosis.models import FailureType, Ownership


def determine_ownership(failure_type: FailureType) -> Ownership:
    """Map failure type to the most likely owning team."""
    mapping = {
        FailureType.ENVIRONMENT: Ownership.INFRASTRUCTURE,
        FailureType.NAVIGATION: Ownership.FRONTEND,
        FailureType.SELECTOR: Ownership.QA,
        FailureType.ASSERTION: Ownership.QA,
        FailureType.NETWORK: Ownership.BACKEND,
        FailureType.APPLICATION: Ownership.FRONTEND,
        FailureType.TIMING: Ownership.QA,
        FailureType.AUTHENTICATION: Ownership.BACKEND,
        FailureType.DATA: Ownership.BACKEND,
        FailureType.AI_PLANNING: Ownership.PLANNER,
        FailureType.TEST_DESIGN: Ownership.PLANNER,
        FailureType.UNKNOWN: Ownership.UNKNOWN,
    }
    return mapping.get(failure_type, Ownership.UNKNOWN)
