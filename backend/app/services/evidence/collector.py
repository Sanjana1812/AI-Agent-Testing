"""Collect structured evidence packages for AI diagnosis (Sprint 4.1B)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.models.diagnosis.evidence import Evidence, EvidenceSource
from app.models.diagnosis.evidence_package import EvidencePackage as LegacyEvidencePackage
from app.services.evidence.dom_capture import build_context_dom_snapshot
from app.services.evidence.models import EvidencePackage, ExecutionContext, FailureEvidence
from app.services.evidence.serializer import serialize_evidence_package
from app.services.failures.failure_enricher import enrich_failures
from app.services.strategy.models import STRATEGY_VERSION


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _collect_assertions(result: dict) -> list[dict[str, Any]]:
    assertions: list[dict[str, Any]] = []
    for step in result.get("steps", []):
        for assertion in step.get("assertions") or []:
            enriched = dict(assertion)
            enriched["step_id"] = step.get("id")
            enriched["step"] = step.get("step")
            assertions.append(enriched)
    return assertions


def _build_testing_strategy_payload(result: dict, planner_metadata: dict | None) -> dict[str, Any] | None:
    if not planner_metadata:
        return None
    return {
        "testing_strategy": planner_metadata.get("testing_strategy"),
        "testing_priority": planner_metadata.get("testing_priority"),
        "execution_priority": planner_metadata.get("execution_priority"),
        "strategy_reasoning": planner_metadata.get("strategy_reasoning"),
        "strategy_version": STRATEGY_VERSION,
    }


def _failure_evidence_from_record(record: dict[str, Any]) -> FailureEvidence:
    ctx_data = record.get("execution_context")
    execution_context = None
    if isinstance(ctx_data, dict):
        execution_context = ExecutionContext(
            browser=ctx_data.get("browser"),
            viewport=ctx_data.get("viewport"),
            planner_version=ctx_data.get("planner_version"),
            strategy_version=ctx_data.get("strategy_version"),
            context_version=ctx_data.get("context_version"),
            elapsed_time_ms=int(ctx_data.get("elapsed_time_ms") or 0),
            retry_count=int(ctx_data.get("retry_count") or 0),
        )

    return FailureEvidence(
        step_number=int(record.get("step_number") or 0),
        step_name=str(record.get("step_name") or ""),
        action=record.get("action"),
        timestamp=str(record.get("timestamp") or _utc_now_iso()),
        current_url=record.get("current_url"),
        page_title=record.get("page_title"),
        selector_attempted=record.get("selector_attempted"),
        selector_alternatives=list(record.get("selector_alternatives") or []),
        failure_type=str(record.get("failure_type") or ""),
        exception=str(record.get("exception") or ""),
        screenshot=record.get("screenshot"),
        dom_snapshot=record.get("dom_snapshot"),
        console_errors=list(record.get("console_errors") or []),
        network_errors=list(record.get("network_errors") or []),
        previous_successful_steps=list(record.get("previous_successful_steps") or []),
        execution_context=execution_context,
    )


def _failure_evidence_from_enriched_failure(
    failure: dict,
    *,
    result: dict,
    steps: list[dict],
    execution_evidence: dict | None,
    browser: str | None,
    viewport: str | None,
    planner_metadata: dict | None,
) -> FailureEvidence:
    step_id = failure.get("step_id")
    step_number = int(step_id) if step_id and str(step_id).isdigit() else 0
    step = next((item for item in steps if item.get("id") == step_id), None)
    step_name = step.get("step") if step else failure.get("expected_element") or "unknown"

    record = None
    if execution_evidence:
        for candidate in execution_evidence.get("failure_records", []):
            if candidate.get("step_number") == step_number:
                record = candidate
                break

    if record:
        return _failure_evidence_from_record(record)

    previous_successful = [item for item in steps if item.get("status") == "passed"]
    return FailureEvidence(
        step_number=step_number,
        step_name=str(step_name),
        action=failure.get("action"),
        timestamp=failure.get("timestamp") or _utc_now_iso(),
        current_url=failure.get("current_url") or result.get("url"),
        page_title=failure.get("page_title") or result.get("title"),
        selector_attempted=failure.get("selector"),
        selector_alternatives=[],
        failure_type=str(failure.get("type") or ""),
        exception=str(failure.get("message") or ""),
        screenshot=failure.get("screenshot_path") or result.get("screenshot"),
        dom_snapshot=build_context_dom_snapshot(failure.get("available_context")),
        console_errors=list(execution_evidence.get("page_errors", [])) if execution_evidence else [],
        network_errors=[],
        previous_successful_steps=previous_successful,
        execution_context=ExecutionContext(
            browser=browser,
            viewport=viewport,
            planner_version=(planner_metadata or {}).get("planner_version"),
            strategy_version=STRATEGY_VERSION if planner_metadata else None,
            context_version=(planner_metadata or {}).get("context_version"),
            elapsed_time_ms=int(result.get("duration_ms") or 0),
            retry_count=0,
        ),
    )


class EvidenceCollector:
    """Build evidence packages for RCA without coupling to runner internals."""

    def build_package(
        self,
        result: dict,
        *,
        website_context: dict | None = None,
        website_analysis: dict | None = None,
        testing_strategy: dict | None = None,
        execution_evidence: dict | None = None,
        website_context_summary: dict | None = None,
    ) -> EvidencePackage:
        planner_metadata = result.get("ai_plan_metadata") or {}
        enriched_failures = enrich_failures(result, website_context_summary)
        steps = result.get("steps", [])

        failure_evidence = [
            _failure_evidence_from_enriched_failure(
                failure,
                result=result,
                steps=steps,
                execution_evidence=execution_evidence,
                browser=result.get("browser"),
                viewport=result.get("viewport"),
                planner_metadata=planner_metadata,
            )
            for failure in enriched_failures
        ]

        dom_snapshot = None
        if execution_evidence and execution_evidence.get("failure_records"):
            dom_snapshot = execution_evidence["failure_records"][-1].get("dom_snapshot")
        if dom_snapshot is None:
            dom_snapshot = build_context_dom_snapshot(website_context)

        console_logs = list(execution_evidence.get("console_logs", [])) if execution_evidence else []
        network_logs = list(execution_evidence.get("network_logs", [])) if execution_evidence else []

        if not console_logs:
            console_logs = [
                {"type": "error", "text": message, "timestamp": _utc_now_iso()}
                for message in _extract_console_errors(result.get("failures", []))
            ]
        if not network_logs:
            network_logs = [
                {"event": "http_error", "text": message, "timestamp": _utc_now_iso()}
                for message in _extract_network_errors(result.get("failures", []))
            ]

        return EvidencePackage(
            run_id=str(result.get("id") or ""),
            execution_summary=dict(result.get("execution_summary") or result.get("summary") or {}),
            website_analysis=website_analysis,
            testing_strategy=testing_strategy or _build_testing_strategy_payload(result, planner_metadata),
            execution_timeline=list(steps),
            planner_metadata=planner_metadata or None,
            explainability_records=planner_metadata.get("confidence_breakdown"),
            coverage_report=planner_metadata.get("coverage_report"),
            assertions=_collect_assertions(result),
            screenshot=result.get("screenshot"),
            final_url=result.get("url"),
            page_title=result.get("title"),
            http_status=result.get("http_status"),
            failure_evidence=failure_evidence,
            console_logs=console_logs,
            network_logs=network_logs,
            dom_snapshot=dom_snapshot,
        )

    # --- Sprint 4.0 legacy compatibility (per-failure packages) ---

    def collect(
        self,
        failure: dict,
        *,
        result: dict | None = None,
        website_context: dict | None = None,
        planner_metadata: dict | None = None,
        website_context_summary: dict | None = None,
    ) -> LegacyEvidencePackage:
        result = result or {}
        steps = result.get("steps", [])
        failures = result.get("failures", [])
        step = _step_for_failure(failure, steps)

        context_summary = (
            failure.get("website_context_summary")
            or website_context_summary
            or failure.get("available_context")
        )

        package: LegacyEvidencePackage = {
            "screenshot_path": failure.get("screenshot_path") or result.get("screenshot"),
            "dom_snapshot": build_context_dom_snapshot(website_context),
            "current_url": failure.get("current_url") or result.get("url"),
            "page_title": failure.get("page_title") or result.get("title"),
            "current_action": failure.get("action"),
            "current_step": step,
            "selector": failure.get("selector"),
            "website_context": context_summary if isinstance(context_summary, dict) else None,
            "planner_metadata": planner_metadata or result.get("ai_plan_metadata"),
            "assertion_results": list(failure.get("assertion_results") or (step or {}).get("assertions") or []),
            "console_errors": _extract_console_errors(failures),
            "network_errors": _extract_network_errors(failures),
            "timestamp": failure.get("timestamp") or _utc_now_iso(),
            "failure": dict(failure),
        }
        package["evidence_items"] = _build_evidence_items(failure, package=package)
        return package

    def collect_for_run(
        self,
        result: dict,
        *,
        website_context: dict | None = None,
        website_context_summary: dict | None = None,
    ) -> list[LegacyEvidencePackage]:
        if not result.get("failures"):
            return []

        enriched = enrich_failures(result, website_context_summary)
        planner_metadata = result.get("ai_plan_metadata")
        packages: list[LegacyEvidencePackage] = []
        for failure in enriched:
            packages.append(
                self.collect(
                    failure,
                    result=result,
                    website_context=website_context,
                    planner_metadata=planner_metadata,
                    website_context_summary=website_context_summary,
                )
            )
        return packages


def collect_evidence_for_run(
    result: dict,
    *,
    website_context: dict | None = None,
    website_context_summary: dict | None = None,
) -> list[LegacyEvidencePackage]:
    return EvidenceCollector().collect_for_run(
        result,
        website_context=website_context,
        website_context_summary=website_context_summary,
    )


def build_evidence_package(
    result: dict,
    *,
    website_context: dict | None = None,
    website_analysis: dict | None = None,
    testing_strategy: dict | None = None,
    execution_evidence: dict | None = None,
    website_context_summary: dict | None = None,
) -> dict[str, Any]:
    package = EvidenceCollector().build_package(
        result,
        website_context=website_context,
        website_analysis=website_analysis,
        testing_strategy=testing_strategy,
        execution_evidence=execution_evidence,
        website_context_summary=website_context_summary,
    )
    return serialize_evidence_package(package)


# --- Legacy helpers ---


def _extract_console_errors(failures: list[dict]) -> list[str]:
    errors: list[str] = []
    for failure in failures:
        if failure.get("type") == "javascript_error":
            message = failure.get("message")
            if message:
                errors.append(str(message))
    return errors


def _extract_network_errors(failures: list[dict]) -> list[str]:
    errors: list[str] = []
    for failure in failures:
        if failure.get("type") in {"navigation_error", "http_error"}:
            message = failure.get("message")
            if message:
                errors.append(str(message))
    return errors


def _step_for_failure(failure: dict, steps: list[dict]) -> dict | None:
    step_id = failure.get("step_id")
    if not step_id:
        return None
    for step in steps:
        if step.get("id") == step_id:
            return step
    return None


def _build_evidence_items(
    failure: dict,
    *,
    package: LegacyEvidencePackage,
) -> list[Evidence]:
    items: list[Evidence] = []

    if package.get("screenshot_path"):
        items.append(
            {
                "source": EvidenceSource.SCREENSHOT.value,
                "description": "Run screenshot captured at failure time",
                "value": package["screenshot_path"],
                "confidence": 1.0,
            }
        )

    if package.get("dom_snapshot"):
        items.append(
            {
                "source": EvidenceSource.DOM.value,
                "description": "Website context snapshot at planning time",
                "value": json.dumps(package["dom_snapshot"], default=str)[:4000],
                "confidence": 0.85,
            }
        )

    for assertion in package.get("assertion_results") or []:
        items.append(
            {
                "source": EvidenceSource.ASSERTION.value,
                "description": assertion.get("reason") or assertion.get("type", "Assertion"),
                "value": f"expected={assertion.get('expected')} actual={assertion.get('actual')}",
                "confidence": 1.0 if assertion.get("passed") is False else 0.5,
            }
        )

    if package.get("website_context"):
        summary = package["website_context"]
        if isinstance(summary, dict):
            items.append(
                {
                    "source": EvidenceSource.CONTEXT.value,
                    "description": "Website context summary",
                    "value": json.dumps(summary, default=str)[:2000],
                    "confidence": 0.9,
                }
            )

    step = package.get("current_step")
    if step:
        items.append(
            {
                "source": EvidenceSource.TIMELINE.value,
                "description": f"Failed step {step.get('id')}: {step.get('step')}",
                "value": f"duration_ms={step.get('duration_ms', 0)}",
                "confidence": 1.0,
            }
        )

    for error in package.get("console_errors") or []:
        items.append(
            {
                "source": EvidenceSource.CONSOLE.value,
                "description": "Console error",
                "value": error[:1000],
                "confidence": 0.95,
            }
        )

    for error in package.get("network_errors") or []:
        items.append(
            {
                "source": EvidenceSource.NETWORK.value,
                "description": "Network error",
                "value": error[:1000],
                "confidence": 0.95,
            }
        )

    if failure.get("selector"):
        items.append(
            {
                "source": EvidenceSource.DOM.value,
                "description": "Target selector",
                "value": failure["selector"],
                "confidence": 0.9,
            }
        )

    return items
