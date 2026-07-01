"""Strongly typed models for AI Website Analysis (Sprint 4.1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


ANALYSIS_VERSION = "4.1.0"


@dataclass(frozen=True)
class WebsiteAnalysis:
    """Semantic understanding of a website derived from structured context."""

    website_type: str
    business_domain: str
    business_purpose: str
    primary_goal: str
    target_audience: str
    critical_user_journeys: list[str]
    recommended_test_flow: list[str]
    high_risk_areas: list[str]
    testing_priority: list[str]
    confidence: float
    reasoning: str
    analysis_version: str = ANALYSIS_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "website_type": self.website_type,
            "business_domain": self.business_domain,
            "business_purpose": self.business_purpose,
            "primary_goal": self.primary_goal,
            "target_audience": self.target_audience,
            "critical_user_journeys": list(self.critical_user_journeys),
            "recommended_test_flow": list(self.recommended_test_flow),
            "high_risk_areas": list(self.high_risk_areas),
            "testing_priority": list(self.testing_priority),
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "analysis_version": self.analysis_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WebsiteAnalysis:
        return cls(
            website_type=str(data.get("website_type", "Business Website")),
            business_domain=str(data.get("business_domain", "General")),
            business_purpose=str(data.get("business_purpose", "Information")),
            primary_goal=str(data.get("primary_goal", "Explore the website")),
            target_audience=str(data.get("target_audience", "General visitors")),
            critical_user_journeys=list(data.get("critical_user_journeys") or []),
            recommended_test_flow=list(data.get("recommended_test_flow") or []),
            high_risk_areas=list(data.get("high_risk_areas") or []),
            testing_priority=list(data.get("testing_priority") or []),
            confidence=float(data.get("confidence", 0.5)),
            reasoning=str(data.get("reasoning", "")),
            analysis_version=str(data.get("analysis_version", ANALYSIS_VERSION)),
        )
