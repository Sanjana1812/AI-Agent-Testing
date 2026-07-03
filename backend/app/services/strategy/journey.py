"""Strategy-driven journey builder (Sprint 4.1A)."""

from __future__ import annotations

import logging

from app.services.planner.intent_classifier import IntentType
from app.services.strategy.models import TestingStrategy
from app.services.website_analysis.journey_builder import try_build_analysis_journey
from app.services.website_analysis.models import WebsiteAnalysis
from app.services.website_context.json_builder import WebsiteContext

logger = logging.getLogger(__name__)


def _analysis_from_strategy(strategy: TestingStrategy) -> WebsiteAnalysis:
    """Adapt a TestingStrategy into a WebsiteAnalysis for journey conversion."""
    flow = list(strategy.recommended_test_flow or strategy.execution_priority)
    if flow and flow[-1].lower() != "screenshot":
        flow.append("Screenshot")
    return WebsiteAnalysis(
        website_type=strategy.website_type,
        business_domain="",
        business_purpose="",
        primary_goal="",
        target_audience="",
        critical_user_journeys=[],
        recommended_test_flow=flow,
        high_risk_areas=list(strategy.high_risk_areas),
        testing_priority=list(strategy.testing_priority),
        confidence=strategy.confidence,
        reasoning=strategy.reasoning,
    )


def try_build_strategy_journey(
    strategy: TestingStrategy,
    context: WebsiteContext,
    *,
    intent: IntentType | str,
) -> list[dict] | None:
    """Build and validate a strategy-driven journey; return None if invalid."""
    analysis_proxy = _analysis_from_strategy(strategy)
    plan = try_build_analysis_journey(analysis_proxy, context, intent=intent)
    if plan:
        logger.info(
            "[StrategyEngine] Using strategy-driven journey for %s (%d steps)",
            strategy.website_type,
            len(plan),
        )
    return plan
