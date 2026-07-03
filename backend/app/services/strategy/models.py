"""Strategy layer models — explainability, coverage, and testing strategy (Sprint 4.1A)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

STRATEGY_VERSION = "4.1A"

SIGNAL_NAMES = (
    "Navigation",
    "Hero",
    "Buttons",
    "Forms",
    "Metadata",
    "Headings",
    "Internal Links",
    "URL Structure",
)

COVERAGE_AREA_NAMES = (
    "Navigation",
    "Hero",
    "Sections",
    "Buttons",
    "Forms",
    "Footer",
    "Search",
    "Authentication",
    "Checkout",
    "Documentation",
)


@dataclass
class SignalContribution:
    signal: str
    weight: float
    score: float
    contribution: float
    evidence: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal": self.signal,
            "weight": round(self.weight, 3),
            "score": round(self.score, 3),
            "contribution": round(self.contribution, 3),
            "evidence": self.evidence,
        }


@dataclass
class ConfidenceBreakdown:
    signals: list[SignalContribution]
    total_confidence: float
    reasoning: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "signals": [signal.to_dict() for signal in self.signals],
            "total_confidence": round(self.total_confidence, 3),
            "reasoning": self.reasoning,
        }


@dataclass
class CoverageArea:
    area: str
    status: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "area": self.area,
            "status": self.status,
            "reason": self.reason,
        }


@dataclass
class CoverageReport:
    areas: list[CoverageArea]
    estimated_coverage_percent: float
    tested_count: int
    applicable_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "areas": [area.to_dict() for area in self.areas],
            "estimated_coverage_percent": round(self.estimated_coverage_percent, 1),
            "tested_count": self.tested_count,
            "applicable_count": self.applicable_count,
        }


@dataclass
class TestingStrategy:
    website_type: str
    testing_strategy: str
    testing_priority: list[str]
    execution_priority: list[str]
    reasoning: str
    recommended_test_flow: list[str] = field(default_factory=list)
    high_risk_areas: list[str] = field(default_factory=list)
    confidence: float = 0.0
    strategy_version: str = STRATEGY_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "website_type": self.website_type,
            "testing_strategy": self.testing_strategy,
            "testing_priority": list(self.testing_priority),
            "execution_priority": list(self.execution_priority),
            "reasoning": self.reasoning,
            "recommended_test_flow": list(self.recommended_test_flow),
            "high_risk_areas": list(self.high_risk_areas),
            "confidence": round(self.confidence, 3),
            "strategy_version": self.strategy_version,
        }
