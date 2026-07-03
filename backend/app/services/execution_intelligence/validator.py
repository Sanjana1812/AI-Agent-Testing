"""Validate decisions before they are acted upon during execution."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.diagnosis.models import FailureType
from app.services.execution_intelligence.models import Decision, DecisionType, ExecutionContext, Observation
from app.services.execution_intelligence.runtime_classifier import is_skippable_classification


@dataclass
class ValidationResult:
    valid: bool
    decision: Decision
    message: str = ""
    rejection_reason: str | None = None

    @property
    def allowed(self) -> bool:
        return self.valid


class DecisionValidator:
    """Sprint 5.1: CONTINUE, ABORT, SKIP, RETRY, RECOVER validation."""

    def validate(
        self,
        decision: Decision,
        observation: Observation | None = None,
        context: ExecutionContext | None = None,
    ) -> ValidationResult:
        if observation is None or context is None:
            if decision.decision_type in {DecisionType.CONTINUE, DecisionType.ABORT}:
                return ValidationResult(
                    valid=True,
                    decision=decision,
                    message=f"{decision.decision_type.value} is permitted.",
                )
            return ValidationResult(
                valid=False,
                decision=decision,
                message=f"{decision.decision_type.value} requires observation context.",
                rejection_reason="Missing observation/context for adaptive validation.",
            )

        if decision.decision_type == DecisionType.CONTINUE:
            return ValidationResult(valid=True, decision=decision, message="CONTINUE is always permitted.")

        if decision.decision_type == DecisionType.ABORT:
            return ValidationResult(valid=True, decision=decision, message="ABORT is always permitted.")

        if decision.decision_type == DecisionType.SKIP:
            return self._validate_skip(decision, observation, context)

        if decision.decision_type == DecisionType.RETRY:
            return self._validate_retry(decision, observation, context)

        if decision.decision_type == DecisionType.RECOVER:
            return self._validate_recover(decision, observation, context)

        if decision.decision_type == DecisionType.REPLAN:
            return self._validate_replan(decision, observation, context)

        return ValidationResult(
            valid=False,
            decision=decision,
            message=f"{decision.decision_type.value} is not enabled.",
            rejection_reason=f"{decision.decision_type.value} is not enabled.",
        )

    def _validate_skip(
        self,
        decision: Decision,
        observation: Observation,
        context: ExecutionContext,
    ) -> ValidationResult:
        if observation.step_index <= 1:
            return self._reject(decision, "Cannot skip the first step of the journey.")

        if decision.confidence < 0.6:
            return self._reject(decision, "SKIP confidence below 0.6 threshold.")

        failure_label = (decision.metadata or {}).get("failure_type", "")
        skippable_labels = {"TEST_DESIGN", "FLAKY", FailureType.TIMING.value}
        if failure_label not in skippable_labels:
            from app.services.execution_intelligence.runtime_classifier import FailureClassifier

            classification = FailureClassifier().classify(
                error_message=observation.error_message or "",
                selector_used=observation.selector,
                step_action=observation.step_action,
                step_name=observation.step_name,
                goal=context.goal,
                strategy=context.strategy,
                planner_metadata=context.planner_metadata,
            )
            if not is_skippable_classification(classification["failure_type"]):
                return self._reject(decision, "Failure type is not skippable.")

        strategy = context.strategy or {}
        critical = strategy.get("critical_steps") or strategy.get("testing_priority") or []
        if observation.step_name in critical:
            return self._reject(decision, "Step is marked critical in strategy.")

        return ValidationResult(valid=True, decision=decision, message="SKIP permitted.")

    def _validate_retry(
        self,
        decision: Decision,
        observation: Observation,
        context: ExecutionContext,
    ) -> ValidationResult:
        metadata = decision.metadata or {}
        if not metadata.get("alternative_selector"):
            return self._reject(decision, "RETRY missing alternative_selector metadata.")

        retry_number = int(metadata.get("retry_number", 0))
        if retry_number > 2:
            return self._reject(decision, "RETRY budget exceeded.")

        step_key = f"step_{observation.step_index}"
        if context.retry_count.get(step_key, 0) >= 2:
            return self._reject(decision, "Step retry budget exhausted.")

        return ValidationResult(valid=True, decision=decision, message="RETRY permitted.")

    def _validate_recover(
        self,
        decision: Decision,
        observation: Observation,
        context: ExecutionContext,
    ) -> ValidationResult:
        metadata = decision.metadata or {}
        if metadata.get("recovery_type") != "modal_dismiss":
            return self._reject(decision, "Only modal_dismiss recovery is enabled.")

        if not metadata.get("retry_after_recovery"):
            return self._reject(decision, "RECOVER requires retry_after_recovery.")

        step_key = f"modal_{observation.step_index}"
        if context.recovery_attempts.get(step_key, 0) >= 1:
            return self._reject(decision, "Recovery already attempted for this step.")

        return ValidationResult(valid=True, decision=decision, message="RECOVER permitted.")

    def _validate_replan(
        self,
        decision: Decision,
        observation: Observation,
        context: ExecutionContext,
    ) -> ValidationResult:
        if decision.confidence < 0.7:
            return self._reject(decision, "REPLAN confidence below 0.7 threshold.")

        if context.replan_count >= 2:
            return self._reject(decision, "Maximum replan attempts exceeded.")

        metadata = decision.metadata or {}
        if not metadata.get("replacement_step"):
            return self._reject(decision, "REPLAN missing replacement_step metadata.")

        if observation.step_index <= 0:
            return self._reject(decision, "Cannot replan before the first executable step.")

        return ValidationResult(valid=True, decision=decision, message="REPLAN permitted.")

    def _reject(self, decision: Decision, reason: str) -> ValidationResult:
        return ValidationResult(
            valid=False,
            decision=decision,
            message=reason,
            rejection_reason=reason,
        )

    def fallback_abort(self, observation: Observation, reason: str) -> Decision:
        from app.services.execution_intelligence.decision_rules import rule_for_failed_step

        if observation.status == "failed":
            abort = rule_for_failed_step(observation)
            abort.reason = f"{abort.reason} Validation rejected adaptive action: {reason}"
            return abort
        return Decision(
            decision_type=DecisionType.CONTINUE,
            reason="Validation rejected adaptive action; continuing.",
            confidence=0.5,
        )
