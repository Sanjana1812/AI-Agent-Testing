"""Serialization helpers for evidence packages."""

from __future__ import annotations

import json
from typing import Any

from app.services.evidence.models import EvidencePackage, FailureEvidence


def serialize_evidence_package(package: EvidencePackage) -> dict[str, Any]:
    return package.to_dict()


def serialize_failure_evidence(evidence: FailureEvidence) -> dict[str, Any]:
    return evidence.to_dict()


def evidence_package_to_json(package: EvidencePackage, *, indent: int | None = None) -> str:
    return json.dumps(serialize_evidence_package(package), indent=indent, default=str)


def failure_evidence_from_dict(data: dict[str, Any]) -> FailureEvidence:
    execution_context = data.get("execution_context")
    from app.services.evidence.models import ExecutionContext

    ctx = None
    if isinstance(execution_context, dict):
        ctx = ExecutionContext(
            browser=execution_context.get("browser"),
            viewport=execution_context.get("viewport"),
            planner_version=execution_context.get("planner_version"),
            strategy_version=execution_context.get("strategy_version"),
            context_version=execution_context.get("context_version"),
            elapsed_time_ms=int(execution_context.get("elapsed_time_ms") or 0),
            retry_count=int(execution_context.get("retry_count") or 0),
        )

    return FailureEvidence(
        step_number=int(data.get("step_number") or 0),
        step_name=str(data.get("step_name") or ""),
        action=data.get("action"),
        timestamp=str(data.get("timestamp") or ""),
        current_url=data.get("current_url"),
        page_title=data.get("page_title"),
        selector_attempted=data.get("selector_attempted"),
        selector_alternatives=list(data.get("selector_alternatives") or []),
        failure_type=str(data.get("failure_type") or ""),
        exception=str(data.get("exception") or ""),
        screenshot=data.get("screenshot"),
        dom_snapshot=data.get("dom_snapshot"),
        console_errors=list(data.get("console_errors") or []),
        network_errors=list(data.get("network_errors") or []),
        previous_successful_steps=list(data.get("previous_successful_steps") or []),
        execution_context=ctx,
    )
