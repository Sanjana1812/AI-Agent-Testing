"""Build planner metadata attached to every run."""

from __future__ import annotations

from datetime import datetime, timezone

PLANNER_VERSION = "4.1.0"
CONTEXT_VERSION = "2.1"


def compute_validation_score(*, plan_steps: int, min_steps: int, max_steps: int, rejections: int) -> float:
    """Simple 0–100 score based on plan size and context validation."""
    if plan_steps < min_steps:
        return max(0.0, 40.0 - rejections * 5)
    size_score = min(100.0, (plan_steps / max_steps) * 70.0)
    rejection_penalty = min(30.0, rejections * 10.0)
    return round(max(0.0, size_score + 30.0 - rejection_penalty), 1)


def build_plan_metadata(
    *,
    planner_source: str,
    planning_time_ms: int,
    validation_score: float,
    provider: str | None = None,
    context_refreshes: int = 0,
    pages_visited: list[str] | None = None,
    cache_hits: int = 0,
    cache_misses: int = 0,
    planner_confidence: float | None = None,
    planner_confidence_label: str | None = None,
    detected_website_type: str | None = None,
    detected_intent: str | None = None,
    primary_navigation: list[str] | None = None,
    planner_strategy: str | None = None,
    generated_journey: list[str] | None = None,
    website_type: str | None = None,
    business_domain: str | None = None,
    primary_goal: str | None = None,
    target_audience: str | None = None,
    recommended_test_flow: list[str] | None = None,
    high_risk_areas: list[str] | None = None,
    testing_priority: list[str] | None = None,
    analysis_confidence: float | None = None,
    analysis_reasoning: str | None = None,
    testing_strategy: str | None = None,
    confidence_breakdown: dict | None = None,
    coverage_report: dict | None = None,
    execution_priority: list[str] | None = None,
    strategy_reasoning: str | None = None,
    estimated_coverage_percent: float | None = None,
) -> dict:
    payload = {
        "planner_source": planner_source,
        "planner_version": PLANNER_VERSION,
        "context_version": CONTEXT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "validation_score": validation_score,
        "planning_time_ms": planning_time_ms,
        "provider": provider or planner_source,
        "context_refreshes": context_refreshes,
        "pages_visited": pages_visited or [],
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
    }
    if planner_confidence is not None:
        payload["planner_confidence"] = planner_confidence
    if planner_confidence_label:
        payload["planner_confidence_label"] = planner_confidence_label
    if detected_website_type:
        payload["detected_website_type"] = detected_website_type
    if detected_intent:
        payload["detected_intent"] = detected_intent
    if primary_navigation:
        payload["primary_navigation"] = primary_navigation
    if planner_strategy:
        payload["planner_strategy"] = planner_strategy
    if generated_journey:
        payload["generated_journey"] = generated_journey
    if website_type:
        payload["website_type"] = website_type
    if business_domain:
        payload["business_domain"] = business_domain
    if primary_goal:
        payload["primary_goal"] = primary_goal
    if target_audience:
        payload["target_audience"] = target_audience
    if recommended_test_flow:
        payload["recommended_test_flow"] = recommended_test_flow
    if high_risk_areas:
        payload["high_risk_areas"] = high_risk_areas
    if testing_priority:
        payload["testing_priority"] = testing_priority
    if analysis_confidence is not None:
        payload["analysis_confidence"] = analysis_confidence
    if analysis_reasoning:
        payload["analysis_reasoning"] = analysis_reasoning
    if testing_strategy:
        payload["testing_strategy"] = testing_strategy
    if confidence_breakdown:
        payload["confidence_breakdown"] = confidence_breakdown
    if coverage_report:
        payload["coverage_report"] = coverage_report
    if execution_priority:
        payload["execution_priority"] = execution_priority
    if strategy_reasoning:
        payload["strategy_reasoning"] = strategy_reasoning
    if estimated_coverage_percent is not None:
        payload["estimated_coverage_percent"] = estimated_coverage_percent
    return payload
