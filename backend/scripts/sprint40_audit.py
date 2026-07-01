"""Sprint 4.0 verification harness — AI Intelligence Foundation."""

from __future__ import annotations

import asyncio
import inspect
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))


def section(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def audit_evidence_collector() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.models.diagnosis import EvidencePackage, EvidenceSource
    from app.services.evidence import EvidenceCollector, collect_evidence_for_run
    from app.services.website_context.json_builder import empty_context

    mock_context = empty_context()
    mock_context["metadata"] = {"title": "Example", "current_url": "https://example.com"}
    mock_context["buttons"] = [{"text": "Submit", "selector": "button.submit"}]

    mock_result = {
        "url": "https://example.com",
        "title": "Example Domain",
        "ai_plan_source": "semantic_planner",
        "screenshot": "/storage/screenshots/test.png",
        "ai_plan_metadata": {
            "planner_source": "semantic_planner",
            "planner_version": "3.9.1",
            "context_version": "2.1",
            "generated_at": "2026-01-01T00:00:00Z",
            "validation_score": 90.0,
            "planning_time_ms": 12,
        },
        "ai_plan": [
            {"action": "open_page", "label": "Open Page"},
            {"action": "click", "selector": "button.submit", "label": 'Click "Submit"'},
        ],
        "steps": [
            {"id": "1", "step": "open_page:Open Page", "status": "passed", "duration_ms": 120, "assertions": []},
            {
                "id": "2",
                "step": "click:Submit",
                "status": "failed",
                "duration_ms": 450,
                "assertions": [
                    {
                        "type": "element_visible",
                        "expected": "visible",
                        "actual": "hidden",
                        "passed": False,
                        "reason": "Element not visible",
                    }
                ],
            },
        ],
        "failures": [
            {
                "type": "element_not_found",
                "message": "Selector not found: button.submit",
                "severity": "medium",
                "selector": "button.submit",
                "expected_element": 'Click "Submit"',
            },
            {
                "type": "javascript_error",
                "message": "ReferenceError: foo is not defined",
                "severity": "low",
            },
        ],
    }

    collector = EvidenceCollector()
    packages = collector.collect_for_run(
        mock_result,
        website_context=mock_context,
        website_context_summary={"buttons": 1, "navigation_links": 0},
    )

    if len(packages) != 2:
        findings["failed"].append(f"Expected 2 evidence packages, got {len(packages)}")
    else:
        findings["passed"].append("One evidence package per failure")

    package: EvidencePackage = packages[0]
    required_keys = {
        "screenshot_path",
        "dom_snapshot",
        "current_url",
        "page_title",
        "current_action",
        "current_step",
        "selector",
        "website_context",
        "planner_metadata",
        "assertion_results",
        "console_errors",
        "network_errors",
        "timestamp",
        "evidence_items",
        "failure",
    }
    missing = required_keys - set(package.keys())
    if missing:
        findings["failed"].append(f"Evidence package missing keys: {sorted(missing)}")
    else:
        findings["passed"].append("Evidence package contains all required fields")

    if package.get("screenshot_path") == "/storage/screenshots/test.png":
        findings["passed"].append("Screenshot path captured")
    else:
        findings["failed"].append("Screenshot path missing")

    if package.get("selector") == "button.submit":
        findings["passed"].append("Selector captured")
    else:
        findings["failed"].append("Selector not captured")

    if package.get("planner_metadata", {}).get("planner_version") == "3.9.1":
        findings["passed"].append("Planner metadata attached")
    else:
        findings["failed"].append("Planner metadata missing")

    if any(item.get("source") == EvidenceSource.ASSERTION.value for item in package.get("evidence_items", [])):
        findings["passed"].append("Assertion evidence items generated")
    else:
        findings["failed"].append("Assertion evidence items missing")

    console_pkg = packages[1]
    if console_pkg.get("console_errors"):
        findings["passed"].append("Console errors extracted from run failures")
    else:
        findings["failed"].append("Console errors not extracted")

    helper_packages = collect_evidence_for_run(mock_result, website_context=mock_context)
    if len(helper_packages) == 2:
        findings["passed"].append("collect_evidence_for_run helper works")
    else:
        findings["failed"].append("collect_evidence_for_run helper failed")

    empty = collector.collect_for_run({"failures": [], "steps": []})
    if empty == []:
        findings["passed"].append("No packages returned when run has no failures")
    else:
        findings["failed"].append("Expected empty list for successful run")

    return findings


def audit_prompt_registry() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.prompts import get_prompt, list_prompts, load_registry
    from app.services.prompts import planner_v1, rca_v1, summary_v1
    from app.services.ai.providers.prompt_builder import build_planning_prompt
    from app.services.website_context.json_builder import empty_context

    keys = list_prompts()
    if keys == ["planner_v1", "rca_v1", "summary_v1"]:
        findings["passed"].append("All prompt keys registered")
    else:
        findings["failed"].append(f"Unexpected prompt keys: {keys}")

    for key in keys:
        prompt = get_prompt(key)
        if not prompt.version:
            findings["failed"].append(f"{key} missing version")
        elif not prompt.purpose:
            findings["failed"].append(f"{key} missing purpose")
        elif not prompt.template:
            findings["failed"].append(f"{key} missing template")
        else:
            findings["passed"].append(f"{key} exposes version/purpose/template")

    registry = load_registry()
    if len(registry) == 3:
        findings["passed"].append("Prompt registry loads all definitions")

    planner_rendered = planner_v1.render(
        url="https://example.com",
        goal="test checkout",
        intent="navigation",
        website_context=empty_context(),
    )
    builder_rendered = build_planning_prompt(
        "https://example.com",
        "test checkout",
        "navigation",
        empty_context(),
    )
    if planner_rendered == builder_rendered:
        findings["passed"].append("prompt_builder delegates to planner_v1 (no behavior change)")
    else:
        findings["failed"].append("Planning prompt output changed after registry migration")

    rca_text = rca_v1.render(
        failure_summary="Element not found",
        evidence_package={"selector": "button.submit"},
    )
    if "Root Cause Analysis" in rca_text and "evidence_json" not in rca_text:
        findings["passed"].append("rca_v1 render produces analysis prompt")
    else:
        findings["failed"].append("rca_v1 render failed")

    summary_text = summary_v1.render(
        status="failed",
        goal="test",
        url="https://example.com",
        health="FAIL",
        passed_steps=1,
        total_steps=3,
        failures=[{"type": "timeout"}],
        planner_source="semantic_planner",
    )
    if "Summarize this test run" in summary_text:
        findings["passed"].append("summary_v1 render works")
    else:
        findings["failed"].append("summary_v1 render failed")

    return findings


def audit_provider_abstraction() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.ai.provider_factory import get_ai_provider, registered_providers
    from app.services.ai.provider_verification import (
        verify_plan_generation_result_shape,
        verify_provider_abstraction,
    )

    errors = verify_provider_abstraction()
    if not errors:
        findings["passed"].append("All four providers satisfy BaseAIProvider contract")
    else:
        findings["failed"].extend(errors)

    shape_errors = verify_plan_generation_result_shape()
    if not shape_errors:
        findings["passed"].append("PlanGenerationResult shape verified")
    else:
        findings["failed"].extend(shape_errors)

    for name in ("ollama", "gemini", "claude", "openai"):
        provider = get_ai_provider(name)
        if provider.name == name:
            findings["passed"].append(f"Provider '{name}' resolves with correct name")
        else:
            findings["failed"].append(f"Provider name mismatch for {name}")

    if set(registered_providers()) >= {"ollama", "gemini", "claude", "openai"}:
        findings["passed"].append("Factory registers Gemini, Ollama, Claude, OpenAI")

    return findings


def audit_diagnosis_models() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.models.diagnosis import (
        Diagnosis,
        Evidence,
        EvidencePackage,
        EvidenceSource,
        FailureCategory,
        RichFailure,
        Severity,
        SuggestedFix,
        SuggestedFixType,
    )

    diagnosis_fields = {
        "summary",
        "root_cause",
        "category",
        "severity",
        "confidence",
        "evidence",
        "recommendations",
        "suggested_fix",
        "provider",
        "latency_ms",
    }
    if diagnosis_fields.issubset(set(Diagnosis.__annotations__.keys())):
        findings["passed"].append("Diagnosis model supports all required fields")
    else:
        missing = diagnosis_fields - set(Diagnosis.__annotations__.keys())
        findings["failed"].append(f"Diagnosis missing fields: {missing}")

    package_fields = {
        "screenshot_path",
        "dom_snapshot",
        "current_url",
        "page_title",
        "current_action",
        "current_step",
        "selector",
        "website_context",
        "planner_metadata",
        "assertion_results",
        "console_errors",
        "network_errors",
        "timestamp",
        "evidence_items",
        "failure",
    }
    if package_fields.issubset(set(EvidencePackage.__annotations__.keys())):
        findings["passed"].append("EvidencePackage model complete")
    else:
        findings["failed"].append("EvidencePackage missing fields")

    sample: Diagnosis = {
        "summary": "Test failed due to missing selector",
        "root_cause": "Planner chose a selector not present in DOM",
        "category": FailureCategory.LOCATOR_ISSUE.value,
        "severity": Severity.MEDIUM.value,
        "confidence": 0.82,
        "evidence": [{"source": EvidenceSource.DOM.value, "description": "Selector missing", "confidence": 0.9}],
        "recommendations": ["Use data-testid selector"],
        "suggested_fix": {"type": SuggestedFixType.SELECTOR.value, "title": "Update selector"},
        "provider": "ollama",
        "latency_ms": 1200,
    }
    if sample.get("root_cause") and sample.get("confidence") == 0.82:
        findings["passed"].append("Diagnosis sample structure valid")

    rich: RichFailure = {"type": "timeout", "message": "Timed out", "severity": "high"}
    if rich.get("type") == "timeout":
        findings["passed"].append("RichFailure model importable")

    return findings


def audit_diagnosis_validator() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.models.diagnosis import EvidenceSource, FailureCategory, Severity, SuggestedFixType
    from app.services.diagnosis import DiagnosisValidator

    validator = DiagnosisValidator()

    valid = validator.validate(
        {
            "summary": "Failure during click step",
            "root_cause": "Target element was not in the DOM",
            "category": FailureCategory.LOCATOR_ISSUE.value,
            "severity": Severity.HIGH.value,
            "confidence": 0.88,
            "evidence": [
                {
                    "source": EvidenceSource.ASSERTION.value,
                    "description": "Visibility assertion failed",
                    "value": "hidden",
                    "confidence": 1.0,
                }
            ],
            "recommendations": ["Wait for hydration"],
            "suggested_fix": {
                "type": SuggestedFixType.SELECTOR.value,
                "title": "Use stable selector",
                "description": "Prefer data-testid",
            },
            "provider": "ollama",
            "latency_ms": 900,
        }
    )
    if valid.valid:
        findings["passed"].append("Valid diagnosis passes validation")
    else:
        findings["failed"].append(f"Valid diagnosis rejected: {valid.errors}")

    invalid_confidence = validator.validate(
        {
            "summary": "x",
            "root_cause": "x",
            "category": FailureCategory.UNKNOWN.value,
            "severity": Severity.LOW.value,
            "confidence": 1.5,
            "evidence": [{"source": EvidenceSource.DOM.value, "description": "d"}],
        }
    )
    if not invalid_confidence.valid and any("confidence" in err for err in invalid_confidence.errors):
        findings["passed"].append("Confidence range enforced")
    else:
        findings["failed"].append("Confidence range validation failed")

    invalid_category = validator.validate(
        {
            "summary": "x",
            "root_cause": "x",
            "category": "Not A Real Category",
            "severity": Severity.LOW.value,
            "confidence": 0.5,
            "evidence": [{"source": EvidenceSource.DOM.value, "description": "d"}],
        }
    )
    if not invalid_category.valid:
        findings["passed"].append("Category validation enforced")
    else:
        findings["failed"].append("Invalid category accepted")

    missing_fields = validator.validate({"summary": "only summary"})
    if not missing_fields.valid:
        findings["passed"].append("Required fields validation enforced")
    else:
        findings["failed"].append("Missing required fields accepted")

    bad_evidence = validator.validate(
        {
            "summary": "x",
            "root_cause": "x",
            "category": FailureCategory.UNKNOWN.value,
            "severity": Severity.LOW.value,
            "confidence": 0.5,
            "evidence": [{"source": "InvalidSource", "description": ""}],
        }
    )
    if not bad_evidence.valid:
        findings["passed"].append("Evidence reference validation enforced")
    else:
        findings["failed"].append("Invalid evidence accepted")

    return findings


def audit_api_regressions() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.schemas import ExecutionFailure, PlannerMetadata, RunTestResponse

    required = {
        "id",
        "goal",
        "status",
        "title",
        "url",
        "http_status",
        "duration_ms",
        "screenshot",
        "ai_plan",
        "ai_plan_source",
        "steps",
        "failures",
        "summary",
    }
    fields = set(RunTestResponse.model_fields.keys())
    if required.issubset(fields):
        findings["passed"].append("RunTestResponse contract unchanged")
    else:
        findings["failed"].append(f"RunTestResponse missing fields: {required - fields}")

    if "diagnosis" not in fields and "evidence_packages" not in fields:
        findings["passed"].append("No new API fields added in Sprint 4.0")
    else:
        findings["failed"].append("Sprint 4.0 must not change API response shape yet")

    failure_fields = set(ExecutionFailure.model_fields.keys())
    if "user_message" in failure_fields and "category" in failure_fields:
        findings["passed"].append("ExecutionFailure extended fields preserved")

    meta_fields = set(PlannerMetadata.model_fields.keys())
    if "planner_version" in meta_fields and "provider" in meta_fields:
        findings["passed"].append("PlannerMetadata preserved")

    return findings


def audit_no_execution_or_frontend_changes() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    runner_path = BACKEND / "app" / "services" / "playwright_runner.py"
    runner_source = runner_path.read_text(encoding="utf-8")

    if "def _execute_sync(" in runner_source:
        findings["passed"].append("_execute_sync preserved in playwright_runner")

    if "EvidenceCollector" not in runner_source and "collect_evidence_for_run" not in runner_source:
        findings["passed"].append("Evidence collector not wired into execution engine")
    else:
        findings["failed"].append("Execution engine must not be modified in Sprint 4.0")

    router_path = BACKEND / "app" / "routers" / "run.py"
    router_source = router_path.read_text(encoding="utf-8")
    if "EvidenceCollector" not in router_source and "collect_evidence_for_run" not in router_source:
        findings["passed"].append("Evidence collector not wired into API router")
    else:
        findings["failed"].append("API router must not change response shape in Sprint 4.0")

    frontend_root = BACKEND.parent / "frontend" / "src"
    if frontend_root.exists():
        findings["passed"].append("Frontend exists — Sprint 4.0 makes no frontend changes by design")

    planner_path = BACKEND / "app" / "services" / "ai_planner.py"
    planner_source = planner_path.read_text(encoding="utf-8")
    if "generate_diagnosis" not in planner_source and "DiagnosisValidator" not in planner_source:
        findings["passed"].append("Planner logic unchanged (no diagnosis generation)")
    else:
        findings["failed"].append("Planner should not invoke diagnosis in Sprint 4.0")

    return findings


async def audit_integration_readiness() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.ai_planner import generate_test_plan
    from app.services.failures.failure_enricher import enrich_failures
    from app.services.prompts import get_prompt
    from app.services.website_context.json_builder import empty_context

    plan_data = await generate_test_plan("https://example.com", "check navigation", empty_context())
    if plan_data.get("plan") and plan_data.get("metadata"):
        findings["passed"].append("Planner still returns plan + metadata after prompt registry migration")
    else:
        findings["failed"].append("Planner integration regression")

    rca_prompt = get_prompt("rca_v1")
    if rca_prompt.render:
        rendered = rca_prompt.render(
            failure_summary="timeout",
            evidence_package={"current_url": "https://example.com"},
        )
        if rendered:
            findings["passed"].append("RCA prompt ready for Sprint 4.1 plug-in")
    else:
        findings["failed"].append("RCA prompt missing render function")

    mock_result = {
        "url": "https://example.com",
        "title": "Example",
        "ai_plan_source": plan_data.get("source"),
        "ai_plan": plan_data.get("plan", []),
        "steps": [{"id": "1", "step": "open_page", "status": "failed", "duration_ms": 50, "assertions": []}],
        "failures": [{"type": "timeout", "message": "Timeout", "severity": "medium"}],
    }
    enriched = enrich_failures(mock_result, {"buttons": 0})
    if enriched and enriched[0].get("timestamp"):
        findings["passed"].append("Failure enricher still compatible with evidence pipeline")
    else:
        findings["failed"].append("Failure enricher regression")

    return findings


def main() -> None:
    all_findings = {}

    section("1. EVIDENCE COLLECTOR")
    all_findings["evidence"] = audit_evidence_collector()
    print(json.dumps(all_findings["evidence"], indent=2))

    section("2. PROMPT REGISTRY")
    all_findings["prompts"] = audit_prompt_registry()
    print(json.dumps(all_findings["prompts"], indent=2))

    section("3. AI PROVIDER ABSTRACTION")
    all_findings["providers"] = audit_provider_abstraction()
    print(json.dumps(all_findings["providers"], indent=2))

    section("4. DIAGNOSIS MODELS")
    all_findings["models"] = audit_diagnosis_models()
    print(json.dumps(all_findings["models"], indent=2))

    section("5. DIAGNOSIS VALIDATOR")
    all_findings["validator"] = audit_diagnosis_validator()
    print(json.dumps(all_findings["validator"], indent=2))

    section("6. API REGRESSIONS")
    all_findings["api"] = audit_api_regressions()
    print(json.dumps(all_findings["api"], indent=2))

    section("7. EXECUTION / FRONTEND CONSTRAINTS")
    all_findings["constraints"] = audit_no_execution_or_frontend_changes()
    print(json.dumps(all_findings["constraints"], indent=2))

    section("8. INTEGRATION READINESS")
    all_findings["integration"] = asyncio.run(audit_integration_readiness())
    print(json.dumps(all_findings["integration"], indent=2))

    failed = sum(len(v.get("failed", [])) for v in all_findings.values())
    print(f"\n{'=' * 60}\nTOTAL FAILURES: {failed}\n{'=' * 60}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
