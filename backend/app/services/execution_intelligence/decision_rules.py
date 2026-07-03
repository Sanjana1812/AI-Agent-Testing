"""Decision rules separated from the engine for future sprint expansion."""

from __future__ import annotations

from typing import Any

from app.services.diagnosis.models import FailureType
from app.services.execution_intelligence.models import Decision, DecisionType, ExecutionContext, Observation
from app.services.execution_intelligence.prompts import DECISION_REASON_TEMPLATES
from app.services.execution_intelligence.runtime_classifier import (
    FailureClassifier,
    is_skippable_classification,
)


def rule_for_passed_step(observation: Observation) -> Decision:
    """Return CONTINUE when a step completed successfully."""
    return Decision(
        decision_type=DecisionType.CONTINUE,
        reason=DECISION_REASON_TEMPLATES["CONTINUE"].format(
            step_name=observation.step_name,
            status=observation.status,
        ),
        confidence=0.95,
    )


def rule_for_failed_step(observation: Observation) -> Decision:
    """Return ABORT when a step failed and no adaptive rule matched."""
    return Decision(
        decision_type=DecisionType.ABORT,
        reason=DECISION_REASON_TEMPLATES["ABORT"].format(
            step_name=observation.step_name,
            status=observation.status,
        ),
        confidence=0.9,
    )


class SmartSkipRule:
    def evaluate(self, observation: Observation, context: ExecutionContext) -> Decision | None:
        if observation.status != "failed":
            return None

        classifier = FailureClassifier()
        classification = classifier.classify(
            error_message=observation.error_message or "",
            selector_used=observation.selector,
            step_action=observation.step_action,
            step_name=observation.step_name,
            http_status=observation.http_status,
            preceding_steps_passed=len(context.completed_steps),
            total_steps=context.total_steps or observation.total_steps,
            goal=context.goal,
            strategy=context.strategy,
            planner_metadata=context.planner_metadata,
        )
        failure_type = classification["failure_type"]
        if not is_skippable_classification(failure_type):
            return None

        strategy = context.strategy or {}
        priority_areas = (
            strategy.get("execution_priority")
            or strategy.get("execution_priorities")
            or strategy.get("testing_priority")
            or []
        )[:3]

        step_is_priority = any(
            str(priority).lower() in observation.step_name.lower() for priority in priority_areas
        )
        if step_is_priority:
            return None

        label = failure_type.value
        if failure_type == FailureType.TIMING:
            label = "FLAKY"

        return Decision(
            decision_type=DecisionType.SKIP,
            reason=(
                f"Step classified as {label} and is not a priority area. "
                "Skipping to continue execution."
            ),
            confidence=float(classification["confidence"]),
            metadata={"failure_type": label},
        )


class SelectorRetryRule:
    def evaluate(self, observation: Observation, context: ExecutionContext) -> Decision | None:
        if observation.status != "failed":
            return None
        if observation.selector_found:
            return None

        classifier = FailureClassifier()
        classification = classifier.classify(
            error_message=observation.error_message or "",
            selector_used=observation.selector,
            step_action=observation.step_action,
            step_name=observation.step_name,
            http_status=observation.http_status,
            preceding_steps_passed=len(context.completed_steps),
            total_steps=context.total_steps or observation.total_steps,
            goal=context.goal,
            strategy=context.strategy,
            planner_metadata=context.planner_metadata,
        )
        if classification["failure_type"] != FailureType.SELECTOR:
            return None

        step_key = f"step_{observation.step_index}"
        current_retries = context.retry_count.get(step_key, 0)
        if current_retries >= 2:
            return None

        alternatives = self._get_selector_alternatives(observation.selector, context)
        if not alternatives:
            return None

        return Decision(
            decision_type=DecisionType.RETRY,
            reason=(
                f"Selector failed. Attempting alternative ({current_retries + 1}/2). "
                f"Alternative: {alternatives[0]}"
            ),
            confidence=0.7,
            metadata={
                "alternative_selector": alternatives[0],
                "retry_number": current_retries + 1,
            },
        )

    def _get_selector_alternatives(
        self,
        failed_selector: str | None,
        context: ExecutionContext,
    ) -> list[str]:
        alternatives: list[str] = []
        if not failed_selector:
            return alternatives

        if failed_selector.startswith("#"):
            element_name = failed_selector[1:]
            alternatives.append(f'[data-testid="{element_name}"]')
            alternatives.append(f'[aria-label*="{element_name}"]')

        if failed_selector.startswith("."):
            class_name = failed_selector[1:]
            alternatives.append(f'[class*="{class_name}"]')

        if "[" in failed_selector:
            alternatives.append(failed_selector.replace('="', '*="'))

        planner = context.planner_metadata or {}
        for alt in planner.get("selector_alternatives") or []:
            if alt and alt not in alternatives:
                alternatives.append(str(alt))

        return alternatives[:2]


class ModalDismissRule:
    DISMISS_SELECTORS = [
        'button[id*="accept"]',
        'button[id*="cookie"]',
        'button[class*="accept"]',
        'button[class*="cookie"]',
        '[aria-label*="Accept"]',
        '[aria-label*="Close"]',
        'button[class*="close"]',
        'button[class*="dismiss"]',
        '[data-dismiss]',
        '.modal-close',
        '.popup-close',
        'button:has-text("Accept")',
        'button:has-text("OK")',
        'button:has-text("Got it")',
        'button:has-text("Close")',
        'button:has-text("No thanks")',
    ]

    def evaluate(self, observation: Observation, context: ExecutionContext) -> Decision | None:
        if not observation.modal_detected:
            return None

        step_key = f"modal_{observation.step_index}"
        if context.recovery_attempts.get(step_key, 0) >= 1:
            return None

        return Decision(
            decision_type=DecisionType.RECOVER,
            reason="Modal or overlay detected. Attempting dismissal before retry.",
            confidence=0.8,
            metadata={
                "recovery_type": "modal_dismiss",
                "dismiss_selectors": list(self.DISMISS_SELECTORS),
                "retry_after_recovery": True,
            },
        )


class ReplanRule:
    """Propose REPLAN when a navigation target is unavailable and a semantic alternative exists."""

    REPLANNABLE_ACTIONS = {"click", "verify_visible", "verify_text"}

    def evaluate(self, observation: Observation, context: ExecutionContext) -> Decision | None:
        if observation.status != "failed":
            return None
        if observation.step_action not in self.REPLANNABLE_ACTIONS:
            return None
        if context.replan_count >= 2:
            return None

        classifier = FailureClassifier()
        classification = classifier.classify(
            error_message=observation.error_message or "",
            selector_used=observation.selector,
            step_action=observation.step_action,
            step_name=observation.step_name,
            http_status=observation.http_status,
            preceding_steps_passed=len(context.completed_steps),
            total_steps=context.total_steps or observation.total_steps,
            goal=context.goal,
            strategy=context.strategy,
            planner_metadata=context.planner_metadata,
        )
        failure_type = classification["failure_type"]
        if is_skippable_classification(failure_type):
            return None

        step_key = f"step_{observation.step_index}"
        if failure_type == FailureType.SELECTOR and context.retry_count.get(step_key, 0) < 2:
            return None

        replannable_types = {
            FailureType.NAVIGATION,
            FailureType.SELECTOR,
            FailureType.APPLICATION,
            FailureType.NETWORK,
        }
        if failure_type not in replannable_types:
            return None

        from app.services.replanning.candidate_generator import find_best_candidate

        failed_step = {
            "action": observation.step_action,
            "label": observation.step_name,
            "selector": observation.selector,
            "target": "link",
        }
        candidate = find_best_candidate(
            failed_step=failed_step,
            step_index=observation.step_index,
            step_name=observation.step_name,
            website_context=context.website_context,
            website_analysis=context.website_analysis,
            strategy=context.strategy,
            planner_metadata=context.planner_metadata,
            visited_pages=context.visited_pages,
        )
        if candidate is None or candidate.confidence < 0.7:
            return None

        return Decision(
            decision_type=DecisionType.REPLAN,
            reason=(
                f"Step '{observation.step_name}' is unavailable at runtime. "
                f"Replacing remaining plan entry with '{candidate.replacement_label}'."
            ),
            confidence=candidate.confidence,
            metadata={
                "replacement_step": candidate.replacement_step,
                "original_step": candidate.original_step,
                "source": candidate.source,
                "failure_type": failure_type.value,
            },
        )


def evaluate_observation(
    observation: Observation,
    context: ExecutionContext | None = None,
) -> Decision:
    """Evaluate rules in priority order; fall back to CONTINUE/ABORT."""
    if context is None:
        from app.services.execution_intelligence.execution_context import build_execution_context

        context = build_execution_context(goal="")
    if observation.status == "passed":
        return rule_for_passed_step(observation)

    rules: list[Any] = [
        ModalDismissRule(),
        SmartSkipRule(),
        SelectorRetryRule(),
        ReplanRule(),
    ]
    for rule in rules:
        if observation.status == "failed":
            decision = rule.evaluate(observation, context)
            if decision is not None:
                return decision

    if observation.status == "failed":
        return rule_for_failed_step(observation)

    return Decision(
        decision_type=DecisionType.CONTINUE,
        reason=(
            f"Step {observation.step_name} reported status '{observation.status}'. "
            "Defaulting to CONTINUE."
        ),
        confidence=0.5,
    )
