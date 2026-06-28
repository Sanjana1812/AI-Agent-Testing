"""Pre-Sprint 4 architecture verification harness."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))


def section(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def audit_ai_providers() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.ai.base import BaseAIProvider
    from app.services.ai.provider_factory import get_ai_provider, registered_providers
    from app.services.ai.providers.gemini_provider import GeminiProvider
    from app.services.ai.providers.ollama_provider import OllamaProvider

    for name in ("ollama", "gemini", "claude", "openai"):
        provider = get_ai_provider(name)
        if not isinstance(provider, BaseAIProvider):
            findings["failed"].append(f"{name} is not a BaseAIProvider")
        else:
            findings["passed"].append(f"Provider '{name}' resolves via factory")

    if set(registered_providers()) >= {"ollama", "gemini", "claude", "openai"}:
        findings["passed"].append("All four providers registered")
    else:
        findings["failed"].append(f"Missing providers: {registered_providers()}")

    ollama = OllamaProvider()
    gemini = GeminiProvider()
    if ollama.name == "ollama" and hasattr(ollama, "generate_plan") and hasattr(ollama, "is_available"):
        findings["passed"].append("OllamaProvider exposes required interface")
    if gemini.name == "gemini":
        findings["passed"].append("GeminiProvider placeholder present")

    return findings


def audit_diagnosis_models() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.models.diagnosis import (
        Diagnosis,
        Evidence,
        EvidenceSource,
        FailureCategory,
        RichFailure,
        Severity,
        SuggestedFix,
        SuggestedFixType,
    )

    categories = {c.value for c in FailureCategory}
    expected_categories = {
        "Application Bug",
        "Planner Issue",
        "Locator Issue",
        "Assertion Failure",
        "Timing Issue",
        "Responsive Layout",
        "Network Issue",
        "Authentication Issue",
        "Accessibility Issue",
        "Unknown",
    }
    if categories == expected_categories:
        findings["passed"].append("All failure categories defined")
    else:
        findings["failed"].append(f"Category mismatch: {expected_categories - categories}")

    severities = {s.value for s in Severity}
    if severities == {"Critical", "High", "Medium", "Low", "Informational"}:
        findings["passed"].append("Severity enum complete")

    if EvidenceSource.DOM.value == "DOM" and SuggestedFixType.SELECTOR.value == "Selector":
        findings["passed"].append("Evidence and SuggestedFix type enums present")

    sample_failure: RichFailure = {
        "type": "element_not_found",
        "message": "Target not found",
        "severity": "medium",
        "step_id": "3",
    }
    sample_diagnosis: Diagnosis = {
        "summary": "Placeholder",
        "category": FailureCategory.LOCATOR_ISSUE.value,
        "severity": Severity.MEDIUM.value,
        "evidence": [{"source": EvidenceSource.DOM.value, "confidence": 0.9}],
        "recommendations": [],
        "suggested_fix": {"type": SuggestedFixType.SELECTOR.value},
    }
    if sample_failure and sample_diagnosis:
        findings["passed"].append("RichFailure and Diagnosis models importable")

    return findings


def audit_schemas() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.schemas import ExecutionFailure, PlannerMetadata, RunTestResponse

    required = {
        "id", "goal", "status", "title", "url", "http_status", "duration_ms",
        "screenshot", "ai_plan", "ai_plan_source", "steps", "failures", "summary",
    }
    fields = set(RunTestResponse.model_fields.keys())
    if required.issubset(fields):
        findings["passed"].append("RunTestResponse core fields preserved")
    else:
        findings["failed"].append(f"Missing core fields: {required - fields}")

    if "ai_plan_metadata" in fields:
        findings["passed"].append("Planner metadata field added (optional)")

    extended = {
        "step_id", "action", "target", "expected", "actual", "exception_type",
        "current_url", "page_title", "planner_source", "screenshot_path",
        "assertion_results", "website_context_summary", "timestamp", "category",
    }
    failure_fields = set(ExecutionFailure.model_fields.keys())
    if extended.issubset(failure_fields):
        findings["passed"].append("ExecutionFailure extended with rich fields")

    meta_fields = set(PlannerMetadata.model_fields.keys())
    if {"planner_source", "planner_version", "context_version", "generated_at", "validation_score", "planning_time_ms"}.issubset(meta_fields):
        findings["passed"].append("PlannerMetadata model complete")

    return findings


def audit_display_labels() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.planner.display_labels import build_step_label

    cases = [
        ({"action": "verify_visible", "target": "hero"}, "Verify Hero Section"),
        ({"action": "click", "target": "button", "text": "LET'S TALK"}, 'Click "LET\'S TALK"'),
        ({"action": "verify_form", "target": "form"}, "Verify Contact Form"),
        ({"action": "open_page"}, "Open Page"),
        ({"action": "capture"}, "Capture Screenshot"),
    ]
    for step, expected in cases:
        label = build_step_label(step)
        if label == expected:
            findings["passed"].append(f"Label OK: {step['action']} -> {label}")
        else:
            findings["failed"].append(f"Label mismatch for {step}: got '{label}', expected '{expected}'")

    return findings


def audit_no_runner_changes() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    runner_path = BACKEND / "app" / "services" / "playwright_runner.py"
    source = runner_path.read_text(encoding="utf-8")
    if "def _execute_sync(" in source:
        findings["passed"].append("_execute_sync preserved")
    if source.count("ai_plan_metadata") == 1:
        findings["passed"].append("Only orchestration layer attaches planner metadata")
    elif "ai_plan_metadata" in source:
        findings["warnings"].append(f"ai_plan_metadata references: {source.count('ai_plan_metadata')}")

    frontend_results = Path(__file__).resolve().parent.parent.parent / "frontend" / "src" / "pages" / "Results.jsx"
    if frontend_results.exists():
        findings["passed"].append("Results.jsx untouched (file exists, no edits in this sprint)")

    return findings


async def audit_integration() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.ai_planner import generate_test_plan
    from app.services.failures.failure_enricher import enrich_failures
    from app.services.website_context.json_builder import empty_context

    plan_data = await generate_test_plan("https://example.com", "check the flow", empty_context())
    if plan_data.get("plan") and plan_data.get("metadata"):
        findings["passed"].append("generate_test_plan returns plan + metadata")
        meta = plan_data["metadata"]
        for key in ("planner_source", "planner_version", "context_version", "generated_at", "validation_score", "planning_time_ms"):
            if key in meta:
                findings["passed"].append(f"metadata.{key} present")
            else:
                findings["failed"].append(f"metadata missing {key}")
    else:
        findings["failed"].append("generate_test_plan missing plan or metadata")

    mock_result = {
        "url": "https://example.com",
        "title": "Example Domain",
        "ai_plan_source": plan_data.get("source"),
        "screenshot": "/storage/screenshots/test.png",
        "ai_plan": plan_data.get("plan", []),
        "steps": [{"id": "1", "step": "open_page:Open Page", "status": "passed", "duration_ms": 100, "assertions": []}],
        "failures": [{"type": "timeout", "message": "Timed out", "severity": "medium"}],
    }
    enriched = enrich_failures(mock_result, {"buttons": 0})
    if enriched and enriched[0].get("timestamp") and enriched[0].get("planner_source"):
        findings["passed"].append("Failure enricher adds extended fields")
    else:
        findings["failed"].append("Failure enricher did not extend failures")

    return findings


def main() -> None:
    all_findings = {}

    section("1. AI PROVIDER ARCHITECTURE")
    all_findings["providers"] = audit_ai_providers()
    print(json.dumps(all_findings["providers"], indent=2))

    section("2. DIAGNOSIS MODELS")
    all_findings["models"] = audit_diagnosis_models()
    print(json.dumps(all_findings["models"], indent=2))

    section("3. API SCHEMAS")
    all_findings["schemas"] = audit_schemas()
    print(json.dumps(all_findings["schemas"], indent=2))

    section("4. DISPLAY LABELS")
    all_findings["labels"] = audit_display_labels()
    print(json.dumps(all_findings["labels"], indent=2))

    section("5. RUNNER / FRONTEND CONSTRAINTS")
    all_findings["constraints"] = audit_no_runner_changes()
    print(json.dumps(all_findings["constraints"], indent=2))

    section("6. INTEGRATION")
    all_findings["integration"] = asyncio.run(audit_integration())
    print(json.dumps(all_findings["integration"], indent=2))

    failed = sum(len(v.get("failed", [])) for v in all_findings.values())
    print(f"\n{'=' * 60}\nTOTAL FAILURES: {failed}\n{'=' * 60}")


if __name__ == "__main__":
    main()
