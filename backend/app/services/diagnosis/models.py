"""Sprint 4.2 — Diagnosis data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

DIAGNOSIS_VERSION = "4.2"


class FailureType(str, Enum):
    ENVIRONMENT = "ENVIRONMENT"
    NAVIGATION = "NAVIGATION"
    SELECTOR = "SELECTOR"
    ASSERTION = "ASSERTION"
    NETWORK = "NETWORK"
    APPLICATION = "APPLICATION"
    TIMING = "TIMING"
    AUTHENTICATION = "AUTHENTICATION"
    DATA = "DATA"
    AI_PLANNING = "AI_PLANNING"
    TEST_DESIGN = "TEST_DESIGN"
    UNKNOWN = "UNKNOWN"


class SeverityLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Ownership(str, Enum):
    FRONTEND = "Frontend Team"
    BACKEND = "Backend Team"
    QA = "QA Team"
    PLANNER = "Planner"
    INFRASTRUCTURE = "Infrastructure"
    UNKNOWN = "Unknown"


class FixComplexity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ConfidenceLabel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


@dataclass
class DiagnosisReport:
    failure_type: str
    root_cause: str
    severity: str
    confidence: float
    confidence_label: str
    business_impact: str
    recommendation: str
    developer_action: str
    qa_action: str
    next_steps: list[str] = field(default_factory=list)
    supporting_evidence: list[dict[str, Any]] = field(default_factory=list)
    reasoning: str = ""
    alternative_hypotheses: list[str] = field(default_factory=list)
    ownership: str = Ownership.UNKNOWN.value
    fix_complexity: str = FixComplexity.MEDIUM.value
    estimated_fix_time: str = "2 hours"
    diagnosis_version: str = DIAGNOSIS_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "failure_type": self.failure_type,
            "root_cause": self.root_cause,
            "severity": self.severity,
            "confidence": round(self.confidence, 3),
            "confidence_label": self.confidence_label,
            "business_impact": self.business_impact,
            "recommendation": self.recommendation,
            "developer_action": self.developer_action,
            "qa_action": self.qa_action,
            "next_steps": list(self.next_steps),
            "supporting_evidence": list(self.supporting_evidence),
            "reasoning": self.reasoning,
            "alternative_hypotheses": list(self.alternative_hypotheses),
            "ownership": self.ownership,
            "fix_complexity": self.fix_complexity,
            "estimated_fix_time": self.estimated_fix_time,
            "diagnosis_version": self.diagnosis_version,
        }
