"""Collect structured evidence packages from failed test executions."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from app.models.diagnosis.evidence import Evidence, EvidenceSource
from app.models.diagnosis.evidence_package import EvidencePackage
from app.services.failures.failure_enricher import enrich_failures


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _build_dom_snapshot(website_context: dict | None) -> dict | None:
    if not website_context:
        return None
    return {
        "metadata": website_context.get("metadata"),
        "navigation": website_context.get("navigation", [])[:20],
        "buttons": website_context.get("buttons", [])[:20],
        "forms": website_context.get("forms", [])[:10],
        "sections": website_context.get("sections", [])[:15],
        "headings": website_context.get("headings", [])[:20],
    }


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
    package: EvidencePackage,
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


class EvidenceCollector:
    """Build structured evidence packages from execution results without runner changes."""

    def collect(
        self,
        failure: dict,
        *,
        result: dict | None = None,
        website_context: dict | None = None,
        planner_metadata: dict | None = None,
        website_context_summary: dict | None = None,
    ) -> EvidencePackage:
        """Collect a single evidence package for one failure record."""
        result = result or {}
        steps = result.get("steps", [])
        failures = result.get("failures", [])
        step = _step_for_failure(failure, steps)

        context_summary = (
            failure.get("website_context_summary")
            or website_context_summary
            or failure.get("available_context")
        )

        package: EvidencePackage = {
            "screenshot_path": failure.get("screenshot_path") or result.get("screenshot"),
            "dom_snapshot": _build_dom_snapshot(website_context),
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
    ) -> list[EvidencePackage]:
        """Collect one evidence package per failure in a run result."""
        if not result.get("failures"):
            return []

        enriched = enrich_failures(result, website_context_summary)
        planner_metadata = result.get("ai_plan_metadata")
        packages: list[EvidencePackage] = []
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
) -> list[EvidencePackage]:
    """Convenience wrapper for collecting evidence packages from a run result."""
    return EvidenceCollector().collect_for_run(
        result,
        website_context=website_context,
        website_context_summary=website_context_summary,
    )
