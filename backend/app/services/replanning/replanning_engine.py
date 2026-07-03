"""Deterministic runtime replanning engine — modifies remaining plan only."""

from __future__ import annotations

from typing import Any

from app.services.execution_intelligence.models import Decision, Observation
from app.services.execution_intelligence.models import ExecutionContext
from app.services.replanning.candidate_generator import find_best_candidate
from app.services.replanning.history import record_replan
from app.services.replanning.models import ReplanResult
from app.services.replanning.plan_editor import apply_replacement
from app.services.replanning.prompts import REPLAN_REASON_TEMPLATES
from app.services.replanning.validator import ReplanValidator


class ReplanningEngine:
    """Rule-based replanning for the remaining execution plan."""

    def __init__(
        self,
        *,
        confidence_threshold: float = 0.7,
        max_replans: int = 2,
    ) -> None:
        self._validator = ReplanValidator(
            confidence_threshold=confidence_threshold,
            max_replans=max_replans,
        )

    def replan(
        self,
        *,
        observation: Observation,
        context: ExecutionContext,
        remaining_plan: list[dict[str, Any]],
        decision: Decision,
        website_context: dict[str, Any] | None = None,
    ) -> ReplanResult:
        if not remaining_plan:
            return ReplanResult(
                success=False,
                modified_remaining_plan=remaining_plan,
                rejection_reason="No remaining plan to modify.",
            )

        metadata = decision.metadata or {}
        candidate = None
        if metadata.get("replacement_step"):
            from app.services.replanning.models import PlanCandidate

            candidate = PlanCandidate(
                step_index=observation.step_index,
                original_step=remaining_plan[0],
                replacement_step=metadata["replacement_step"],
                confidence=float(decision.confidence),
                reason=decision.reason,
                source=str(metadata.get("source", "decision_metadata")),
            )
        else:
            candidate = find_best_candidate(
                failed_step=remaining_plan[0],
                step_index=observation.step_index,
                step_name=observation.step_name,
                website_context=website_context or context.website_context,
                website_analysis=context.website_analysis,
                strategy=context.strategy,
                planner_metadata=context.planner_metadata,
                visited_pages=context.visited_pages,
            )

        if candidate is None:
            return ReplanResult(
                success=False,
                modified_remaining_plan=remaining_plan,
                rejection_reason="No semantic replacement candidate available.",
            )

        validation = self._validator.validate(
            candidate=candidate,
            goal=context.goal,
            replan_count=context.replan_count,
            remaining_plan=remaining_plan,
        )
        if not validation.valid:
            return ReplanResult(
                success=False,
                modified_remaining_plan=remaining_plan,
                rejection_reason=validation.rejection_reason,
            )

        original_label = candidate.original_step.get("label") or observation.step_name
        replacement_label = candidate.replacement_step.get("label") or candidate.replacement_label
        reason = REPLAN_REASON_TEMPLATES["navigation_unavailable"].format(
            original=original_label,
            replacement=replacement_label,
        )

        modified_remaining, modifications = apply_replacement(
            remaining_plan,
            failed_index=0,
            replacement_step=candidate.replacement_step,
            reason=reason,
            confidence=candidate.confidence,
        )

        history = record_replan(
            original_remaining=remaining_plan,
            modified_remaining=modified_remaining,
            modifications=modifications,
            trigger_observation=observation.to_dict(),
            decision=decision.to_dict(),
            reason=reason,
            confidence=candidate.confidence,
        )

        return ReplanResult(
            success=True,
            modified_remaining_plan=modified_remaining,
            history=history,
            explainability={
                "why_original_invalid": (
                    observation.error_message
                    or f"Step '{observation.step_name}' failed at runtime."
                ),
                "trigger_observation": observation.to_dict(),
                "why_replacement_appropriate": candidate.reason,
                "confidence": candidate.confidence,
                "affected_remaining_steps": history.affected_remaining_steps,
            },
        )
