"""Evaluate observations and produce structured decisions."""

from __future__ import annotations

from app.services.execution_intelligence.decision_rules import evaluate_observation
from app.services.execution_intelligence.models import Decision, ExecutionContext, Observation


class DecisionEngine:
    """Modular decision engine — delegates rule logic to decision_rules."""

    def decide(self, observation: Observation, context: ExecutionContext) -> Decision:
        return evaluate_observation(observation, context)
