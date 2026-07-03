"""Validate replanning proposals before applying them to the remaining plan."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.replanning.candidate_generator import _extract_step_label, _normalize_label
from app.services.replanning.models import DEFAULT_CONFIDENCE_THRESHOLD, DEFAULT_MAX_REPLANS, PlanCandidate


@dataclass
class ReplanValidationResult:
    valid: bool
    rejection_reason: str | None = None


class ReplanValidator:
    def __init__(
        self,
        *,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        max_replans: int = DEFAULT_MAX_REPLANS,
    ) -> None:
        self.confidence_threshold = confidence_threshold
        self.max_replans = max_replans

    def validate(
        self,
        *,
        candidate: PlanCandidate,
        goal: str,
        replan_count: int,
        remaining_plan: list[dict],
    ) -> ReplanValidationResult:
        if replan_count >= self.max_replans:
            return ReplanValidationResult(
                valid=False,
                rejection_reason="Maximum replan attempts exceeded for this run.",
            )

        if candidate.confidence < self.confidence_threshold:
            return ReplanValidationResult(
                valid=False,
                rejection_reason=(
                    f"Candidate confidence {candidate.confidence:.2f} "
                    f"below threshold {self.confidence_threshold:.2f}."
                ),
            )

        if self._goal_would_change(candidate, goal):
            return ReplanValidationResult(
                valid=False,
                rejection_reason="Replacement would change the business testing goal.",
            )

        if not self._candidate_is_related(candidate):
            return ReplanValidationResult(
                valid=False,
                rejection_reason="Replacement candidate is unrelated to the failed step.",
            )

        if not remaining_plan:
            return ReplanValidationResult(
                valid=False,
                rejection_reason="Remaining plan is empty.",
            )

        modified = list(remaining_plan)
        if modified:
            modified[0] = candidate.replacement_step
        if not modified or all(step.get("action") == "capture" for step in modified):
            return ReplanValidationResult(
                valid=False,
                rejection_reason="Replan would leave no executable steps.",
            )

        return ReplanValidationResult(valid=True)

    def _goal_would_change(self, candidate: PlanCandidate, goal: str) -> bool:
        goal_norm = _normalize_label(goal)
        replacement_norm = _extract_step_label(candidate.replacement_step)
        if not goal_norm or not replacement_norm:
            return False
        blocked_pairs = {
            ("login", "pricing"),
            ("checkout", "about"),
            ("payment", "blog"),
        }
        for left, right in blocked_pairs:
            if left in goal_norm and right in replacement_norm:
                return True
        return False

    def _candidate_is_related(self, candidate: PlanCandidate) -> bool:
        original = _extract_step_label(candidate.original_step)
        replacement = _extract_step_label(candidate.replacement_step)
        if not original or not replacement:
            return False
        if original == replacement:
            return False
        if candidate.confidence >= self.confidence_threshold:
            return True
        return False
