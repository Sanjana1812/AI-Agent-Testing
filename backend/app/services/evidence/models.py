"""Evidence Foundation models (Sprint 4.1B)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

EVIDENCE_VERSION = "4.1B"


@dataclass
class ExecutionContext:
    browser: str | None = None
    viewport: str | None = None
    planner_version: str | None = None
    strategy_version: str | None = None
    context_version: str | None = None
    elapsed_time_ms: int = 0
    retry_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "browser": self.browser,
            "viewport": self.viewport,
            "planner_version": self.planner_version,
            "strategy_version": self.strategy_version,
            "context_version": self.context_version,
            "elapsed_time_ms": self.elapsed_time_ms,
            "retry_count": self.retry_count,
        }


@dataclass
class FailureEvidence:
    step_number: int
    step_name: str
    action: str | None
    timestamp: str
    current_url: str | None
    page_title: str | None
    selector_attempted: str | None
    selector_alternatives: list[str] = field(default_factory=list)
    failure_type: str = ""
    exception: str = ""
    screenshot: str | None = None
    dom_snapshot: dict[str, Any] | None = None
    console_errors: list[str] = field(default_factory=list)
    network_errors: list[str] = field(default_factory=list)
    previous_successful_steps: list[dict[str, Any]] = field(default_factory=list)
    execution_context: ExecutionContext | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_number": self.step_number,
            "step_name": self.step_name,
            "action": self.action,
            "timestamp": self.timestamp,
            "current_url": self.current_url,
            "page_title": self.page_title,
            "selector_attempted": self.selector_attempted,
            "selector_alternatives": list(self.selector_alternatives),
            "failure_type": self.failure_type,
            "exception": self.exception,
            "screenshot": self.screenshot,
            "dom_snapshot": self.dom_snapshot,
            "console_errors": list(self.console_errors),
            "network_errors": list(self.network_errors),
            "previous_successful_steps": list(self.previous_successful_steps),
            "execution_context": self.execution_context.to_dict() if self.execution_context else None,
        }


@dataclass
class EvidencePackage:
    run_id: str
    execution_summary: dict[str, Any]
    website_analysis: dict[str, Any] | None = None
    testing_strategy: dict[str, Any] | None = None
    execution_timeline: list[dict[str, Any]] = field(default_factory=list)
    planner_metadata: dict[str, Any] | None = None
    explainability_records: dict[str, Any] | None = None
    coverage_report: dict[str, Any] | None = None
    assertions: list[dict[str, Any]] = field(default_factory=list)
    screenshot: str | None = None
    final_url: str | None = None
    page_title: str | None = None
    http_status: int | None = None
    failure_evidence: list[FailureEvidence] = field(default_factory=list)
    console_logs: list[dict[str, Any]] = field(default_factory=list)
    network_logs: list[dict[str, Any]] = field(default_factory=list)
    dom_snapshot: dict[str, Any] | None = None
    evidence_version: str = EVIDENCE_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "execution_summary": dict(self.execution_summary),
            "website_analysis": self.website_analysis,
            "testing_strategy": self.testing_strategy,
            "execution_timeline": list(self.execution_timeline),
            "planner_metadata": self.planner_metadata,
            "explainability_records": self.explainability_records,
            "coverage_report": self.coverage_report,
            "assertions": list(self.assertions),
            "screenshot": self.screenshot,
            "final_url": self.final_url,
            "page_title": self.page_title,
            "http_status": self.http_status,
            "failure_evidence": [item.to_dict() for item in self.failure_evidence],
            "console_logs": list(self.console_logs),
            "network_logs": list(self.network_logs),
            "dom_snapshot": self.dom_snapshot,
            "evidence_version": self.evidence_version,
        }
