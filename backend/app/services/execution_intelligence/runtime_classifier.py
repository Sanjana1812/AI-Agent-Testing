"""Runtime failure classification using the Diagnosis Engine (read-only)."""

from __future__ import annotations

from typing import Any

from app.services.diagnosis.failure_classifier import classify_failure
from app.services.diagnosis.models import FailureType


class FailureClassifier:
    """Thin adapter over classify_failure for in-loop execution intelligence."""

    def classify(
        self,
        *,
        error_message: str = "",
        selector_used: str | None = None,
        step_action: str = "",
        step_name: str = "",
        http_status: int = 0,
        preceding_steps_passed: int = 0,
        total_steps: int = 0,
        goal: str = "",
        strategy: dict[str, Any] | None = None,
        planner_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        raw_type = "element_not_found"
        if "timeout" in error_message.lower() or step_action == "open_page":
            raw_type = "timeout"
        elif "assertion" in error_message.lower():
            raw_type = "assertion_failure"
        elif "navigation" in error_message.lower():
            raw_type = "navigation_error"

        evidence_package = {
            "failure_evidence": [
                {
                    "failure_type": raw_type,
                    "type": raw_type,
                    "exception": error_message,
                    "message": error_message,
                    "selector": selector_used or "",
                    "selector_attempted": selector_used or "",
                    "step_number": preceding_steps_passed + 1,
                    "step_name": step_name,
                    "action": step_action,
                }
            ],
            "execution_timeline": [{"id": str(preceding_steps_passed + 1), "step": step_name, "status": "failed"}],
            "testing_strategy": strategy or {},
            "planner_metadata": planner_metadata or {},
            "execution_summary": {"failed_steps": 1, "health": "FAIL"},
        }

        failure_type = classify_failure(evidence_package, goal=goal)

        confidence = 0.85
        if failure_type == FailureType.TEST_DESIGN:
            confidence = 0.9
        elif failure_type == FailureType.TIMING:
            failure_type = FailureType.TIMING
            confidence = 0.75
        elif failure_type == FailureType.SELECTOR:
            confidence = 0.8

        return {
            "failure_type": failure_type,
            "confidence": confidence,
        }


def is_flaky_classification(failure_type: FailureType) -> bool:
    return failure_type == FailureType.TIMING


def is_skippable_classification(failure_type: FailureType) -> bool:
    return failure_type == FailureType.TEST_DESIGN or is_flaky_classification(failure_type)
