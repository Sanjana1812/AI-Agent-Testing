"""Website Analysis Engine — semantic understanding from structured context."""

from __future__ import annotations

import logging
import time

from app.services.website_analysis.classifier import classify_context
from app.services.website_analysis.journey_builder import (
    build_critical_journeys,
    build_recommended_flow,
)
from app.services.website_analysis.models import ANALYSIS_VERSION, WebsiteAnalysis
from app.services.website_analysis.risk_engine import compute_high_risk_areas, compute_testing_priority
from app.services.website_context.context_utils import is_context_empty
from app.services.website_context.json_builder import WebsiteContext

logger = logging.getLogger(__name__)


class WebsiteAnalyzer:
    """Analyze Website Context and produce a strongly typed WebsiteAnalysis."""

    def analyze(
        self,
        context: WebsiteContext,
        *,
        goal: str | None = None,
    ) -> WebsiteAnalysis:
        start = time.perf_counter()
        if is_context_empty(context):
            reasoning = (
                "Website structure could not be extracted before analysis. "
                "Classification and journey recommendations are unavailable until context extraction succeeds."
            )
            if goal:
                reasoning += f" Testing goal noted: {goal.strip()}."
            analysis = WebsiteAnalysis(
                website_type="Unknown",
                business_domain="Not determined",
                business_purpose="Not determined",
                primary_goal="Not determined",
                target_audience="Not determined",
                critical_user_journeys=[],
                recommended_test_flow=[],
                high_risk_areas=["Context extraction"],
                testing_priority=["Restore website context extraction"],
                confidence=0.0,
                reasoning=reasoning,
                analysis_version=ANALYSIS_VERSION,
            )
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            logger.warning("[WebsiteAnalysis] Empty context — analysis deferred (%dms)", elapsed_ms)
            return analysis

        classification = classify_context(context)
        website_type = classification["website_type"]
        recommended_flow = build_recommended_flow(website_type)
        critical_journeys = build_critical_journeys(website_type, recommended_flow)
        high_risk_areas = compute_high_risk_areas(website_type, context=context)
        testing_priority = compute_testing_priority(website_type, context=context)

        reasoning = classification["reasoning"]
        if goal:
            reasoning += f" Testing goal considered: {goal.strip()}."

        analysis = WebsiteAnalysis(
            website_type=website_type,
            business_domain=classification["business_domain"],
            business_purpose=classification["business_purpose"],
            primary_goal=classification["primary_goal"],
            target_audience=classification["target_audience"],
            critical_user_journeys=critical_journeys,
            recommended_test_flow=recommended_flow,
            high_risk_areas=high_risk_areas,
            testing_priority=testing_priority,
            confidence=classification["confidence"],
            reasoning=reasoning,
            analysis_version=ANALYSIS_VERSION,
        )
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            "[WebsiteAnalysis] Classified as %s (confidence=%.2f, %dms)",
            analysis.website_type,
            analysis.confidence,
            elapsed_ms,
        )
        return analysis


def analyze_website(context: WebsiteContext, *, goal: str | None = None) -> WebsiteAnalysis:
    return WebsiteAnalyzer().analyze(context, goal=goal)
