"""Coordinate observer → decision engine → validator."""

from __future__ import annotations

import logging
from typing import Any

from app.services.execution_intelligence.decision_engine import DecisionEngine
from app.services.execution_intelligence.execution_context import (
    append_intelligence_log,
    build_execution_context,
    record_replan,
    record_skip,
    update_execution_context,
)
from app.services.execution_intelligence.models import (
    Decision,
    DecisionRecord,
    DecisionType,
    ExecutionContext,
    ExecutionIntelligenceTrace,
    StepDecisionOutcome,
)
from app.services.execution_intelligence.observer import ExecutionObserver
from app.services.execution_intelligence.validator import DecisionValidator

logger = logging.getLogger(__name__)


class ExecutionIntelligenceOrchestrator:
    """Coordinates observation, decisions, validation, and context logging."""

    def __init__(self) -> None:
        self._observer = ExecutionObserver()
        self._engine = DecisionEngine()
        self._validator = DecisionValidator()
        self._trace = ExecutionIntelligenceTrace()
        self._context: ExecutionContext | None = None

    @property
    def context(self) -> ExecutionContext | None:
        return self._context

    @property
    def trace(self) -> ExecutionIntelligenceTrace:
        return self._trace

    def start(
        self,
        *,
        goal: str,
        website_analysis: dict[str, Any] | None = None,
        strategy: dict[str, Any] | None = None,
        planner_metadata: dict[str, Any] | None = None,
        website_context: dict[str, Any] | None = None,
        total_steps: int = 0,
    ) -> ExecutionContext:
        self._context = build_execution_context(
            goal=goal,
            website_analysis=website_analysis,
            strategy=strategy,
            planner_metadata=planner_metadata,
            website_context=website_context,
            total_steps=total_steps,
        )
        self._trace = ExecutionIntelligenceTrace(version="5.2")
        return self._context

    def process_step(self, step_payload: dict[str, Any]) -> StepDecisionOutcome:
        if self._context is None:
            raise RuntimeError("ExecutionIntelligenceOrchestrator.start() must be called first")

        observation = self._observer.observe(step_payload)
        proposed = self._engine.decide(observation, self._context)
        validation = self._validator.validate(proposed, observation, self._context)

        decision = proposed
        validated = validation.valid
        if not validation.valid:
            decision = self._validator.fallback_abort(
                observation,
                validation.rejection_reason or validation.message,
            )
            validated = decision.decision_type == DecisionType.ABORT

        update_execution_context(self._context, observation)
        outcome = self._resolve_outcome(decision, observation)
        self._apply_context_side_effects(decision, observation, outcome)

        record = DecisionRecord(
            observation=observation,
            decision=decision,
            validated=validated,
            validation_message=validation.message,
            outcome=outcome,
        )
        self._trace.decisions.append(record)

        append_intelligence_log(
            self._context,
            observation=observation,
            decision=decision,
            validated=validated,
            outcome=outcome,
        )

        logger.debug(
            "[ExecutionIntelligence] step=%s status=%s decision=%s outcome=%s",
            observation.step_name,
            observation.status,
            decision.decision_type.value,
            outcome,
        )

        return StepDecisionOutcome(
            observation=observation,
            decision=decision,
            validated=validated and proposed.decision_type == decision.decision_type,
            validation_message=validation.message,
            outcome=outcome,
            rejection_reason=validation.rejection_reason,
        )

    def after_step(self, step_payload: dict[str, Any]) -> DecisionRecord:
        """Backward-compatible wrapper used by older integration paths."""
        outcome = self.process_step(step_payload)
        return self._trace.decisions[-1]

    def record_retry(self, step_index: int) -> None:
        if self._context is None:
            return
        step_key = f"step_{step_index}"
        self._context.retry_count[step_key] = self._context.retry_count.get(step_key, 0) + 1

    def record_recovery(self, step_index: int) -> None:
        if self._context is None:
            return
        step_key = f"modal_{step_index}"
        self._context.recovery_attempts[step_key] = self._context.recovery_attempts.get(step_key, 0) + 1

    def _resolve_outcome(self, decision: Decision, observation: Observation) -> str:
        if decision.decision_type == DecisionType.CONTINUE:
            return "continued"
        if decision.decision_type == DecisionType.SKIP:
            return "skipped"
        if decision.decision_type == DecisionType.RETRY:
            return "retried"
        if decision.decision_type == DecisionType.RECOVER:
            return "recovered"
        if decision.decision_type == DecisionType.REPLAN:
            return "replanned"
        if decision.decision_type == DecisionType.ABORT:
            return "aborted"
        return "continued"

    def _apply_context_side_effects(
        self,
        decision: Decision,
        observation: Observation,
        outcome: str,
    ) -> None:
        if self._context is None:
            return
        if outcome == "skipped":
            record_skip(self._context, observation, decision)
        if decision.decision_type == DecisionType.RETRY:
            self.record_retry(observation.step_index)
        if decision.decision_type == DecisionType.RECOVER:
            self.record_recovery(observation.step_index)
        if decision.decision_type == DecisionType.REPLAN and outcome == "replanned":
            pass  # history recorded by runner after engine applies plan changes

    def record_replan_history(self, history_entry: dict[str, Any]) -> None:
        if self._context is None:
            return
        record_replan(self._context, history_entry)

    def export(self) -> dict[str, Any]:
        payload = self._trace.to_dict()
        if self._context is not None:
            payload["execution_context"] = self._context.to_dict()
        return payload
