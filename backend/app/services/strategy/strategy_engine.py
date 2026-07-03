"""Testing strategy engine — derives execution plan from WebsiteAnalysis (Sprint 4.1A)."""

from __future__ import annotations

import logging

from app.services.planner.context_index import ContextIndex
from app.services.strategy.models import ConfidenceBreakdown, TestingStrategy
from app.services.strategy.rules import EXECUTION_FLOWS, EXECUTION_PRIORITIES, STRATEGY_TEMPLATES
from app.services.website_analysis.models import WebsiteAnalysis
from app.services.website_analysis.risk_engine import compute_high_risk_areas, compute_testing_priority
from app.services.website_context.json_builder import WebsiteContext

logger = logging.getLogger(__name__)


def _boost_execution_priority(
    base: list[str],
    *,
    index: ContextIndex,
    testing_priority: list[str],
) -> list[str]:
    merged: list[str] = []
    for item in testing_priority + base:
        normalized = item.strip()
        if normalized and normalized not in merged:
            merged.append(normalized)
    if index.has_password_field() and "Authentication" not in merged:
        merged.insert(0, "Authentication")
    if any("search" in str(button.get("text", "")).lower() for button in index.usable_buttons()):
        if "Search" not in merged:
            merged.insert(min(2, len(merged)), "Search")
    return merged[:8]


def build_testing_strategy(
    analysis: WebsiteAnalysis,
    context: WebsiteContext,
    *,
    goal: str | None = None,
    breakdown: ConfidenceBreakdown | None = None,
) -> TestingStrategy:
    """Build a strategy object consumed by the planner for journey selection."""
    index = ContextIndex(context)
    website_type = analysis.website_type or "Business Website"

    testing_priority = compute_testing_priority(website_type, context=context)
    high_risk_areas = compute_high_risk_areas(website_type, context=context)
    recommended_flow = list(
        analysis.recommended_test_flow
        or EXECUTION_FLOWS.get(website_type, EXECUTION_FLOWS["Business Website"])
    )
    execution_priority = _boost_execution_priority(
        EXECUTION_PRIORITIES.get(website_type, EXECUTION_PRIORITIES["Business Website"]),
        index=index,
        testing_priority=testing_priority,
    )

    strategy_text = STRATEGY_TEMPLATES.get(website_type, STRATEGY_TEMPLATES["Business Website"])
    if goal:
        strategy_text += f" Goal alignment: {goal.strip()}."

    reasoning_parts = [
        strategy_text,
        f"Prioritize {', '.join(testing_priority[:3])}.",
    ]
    if breakdown:
        reasoning_parts.append(breakdown.reasoning)
    elif analysis.reasoning:
        reasoning_parts.append(analysis.reasoning)

    confidence = breakdown.total_confidence if breakdown else analysis.confidence

    strategy = TestingStrategy(
        website_type=website_type,
        testing_strategy=strategy_text,
        testing_priority=testing_priority,
        execution_priority=execution_priority,
        reasoning=" ".join(reasoning_parts).strip(),
        recommended_test_flow=recommended_flow,
        high_risk_areas=high_risk_areas,
        confidence=confidence,
    )
    logger.info(
        "[StrategyEngine] Built strategy for %s — priority=%s execution=%s",
        website_type,
        testing_priority[:3],
        execution_priority[:4],
    )
    return strategy
