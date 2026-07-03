"""Sprint 5.0 verification harness — Execution Intelligence Foundation."""

from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))


def section(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def audit_package_modules() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    modules = [
        "__init__",
        "models",
        "observer",
        "execution_context",
        "decision_engine",
        "decision_rules",
        "validator",
        "orchestrator",
        "prompts",
    ]
    base = BACKEND / "app" / "services" / "execution_intelligence"
    for module in modules:
        path = base / f"{module}.py"
        if path.exists():
            findings["passed"].append(f"{module}.py present")
        else:
            findings["failed"].append(f"{module}.py missing")
    return findings


def audit_observer() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.execution_intelligence.observer import ExecutionObserver

    observation = ExecutionObserver().observe(
        {
            "step_index": 1,
            "step_name": "open_page:Homepage",
            "status": "passed",
            "current_url": "https://example.com/",
            "page_title": "Example",
            "selector": None,
            "selector_found": True,
            "http_status": 200,
            "console_error_count": 0,
            "network_error_count": 0,
            "modal_detected": False,
            "execution_time_ms": 120,
        }
    )
    if observation.step_name == "open_page:Homepage" and observation.status == "passed":
        findings["passed"].append("Observer builds Observation from step payload")
    else:
        findings["failed"].append("Observer returned unexpected observation")

    source = inspect.getsource(ExecutionObserver)
    if "from playwright" not in source and "import playwright" not in source and ".retry(" not in source:
        findings["passed"].append("Observer does not call Playwright or retry")
    else:
        findings["failed"].append("Observer must only observe")
    return findings


def audit_decision_engine() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.execution_intelligence.decision_engine import DecisionEngine
    from app.services.execution_intelligence.execution_context import build_execution_context
    from app.services.execution_intelligence.models import DecisionType, Observation

    context = build_execution_context(goal="Verify homepage")
    engine = DecisionEngine()

    passed_obs = Observation(
        step_index=1,
        step_name="open_page:Homepage",
        status="passed",
        current_url="https://example.com/",
        page_title="Example",
        selector=None,
        selector_found=True,
        http_status=200,
        console_error_count=0,
        network_error_count=0,
        modal_detected=False,
        execution_time_ms=100,
    )
    failed_obs = Observation(
        step_index=2,
        step_name="click:Missing",
        status="failed",
        current_url="https://example.com/",
        page_title="Example",
        selector="button.missing",
        selector_found=False,
        http_status=200,
        console_error_count=1,
        network_error_count=0,
        modal_detected=False,
        execution_time_ms=200,
    )

    continue_decision = engine.decide(passed_obs, context)
    abort_decision = engine.decide(failed_obs, context)

    if continue_decision.decision_type == DecisionType.CONTINUE:
        findings["passed"].append("Passed step yields CONTINUE")
    else:
        findings["failed"].append(f"Expected CONTINUE, got {continue_decision.decision_type}")

    if abort_decision.decision_type == DecisionType.ABORT:
        findings["passed"].append("Failed step yields ABORT")
    else:
        findings["failed"].append(f"Expected ABORT, got {abort_decision.decision_type}")

    if continue_decision.reason and abort_decision.confidence > 0:
        findings["passed"].append("Decision includes reason and confidence")
    else:
        findings["failed"].append("Decision missing reason or confidence")
    return findings


def audit_execution_context() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.execution_intelligence.execution_context import (
        build_execution_context,
        update_execution_context,
    )
    from app.services.execution_intelligence.models import Observation

    context = build_execution_context(
        goal="Verify navigation",
        website_analysis={"website_type": "Corporate"},
        strategy={"testing_strategy": "Smoke navigation"},
        planner_metadata={"planner_version": "4.1.0"},
    )
    if context.goal == "Verify navigation" and context.website_analysis:
        findings["passed"].append("ExecutionContext created with planner inputs")
    else:
        findings["failed"].append("ExecutionContext missing expected fields")

    observation = Observation(
        step_index=1,
        step_name="verify_visible:Navigation",
        status="passed",
        current_url="https://example.com/",
        page_title="Example",
        selector="nav",
        selector_found=True,
        http_status=200,
        console_error_count=0,
        network_error_count=0,
        modal_detected=False,
        execution_time_ms=80,
    )
    update_execution_context(context, observation)
    if len(context.observations) == 1 and len(context.completed_steps) == 1:
        findings["passed"].append("ExecutionContext updates after observation")
    else:
        findings["failed"].append("ExecutionContext not updated correctly")
    return findings


def audit_orchestrator() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.execution_intelligence.models import DecisionType
    from app.services.execution_intelligence.orchestrator import ExecutionIntelligenceOrchestrator
    from app.services.execution_intelligence.validator import DecisionValidator

    orchestrator = ExecutionIntelligenceOrchestrator()
    orchestrator.start(goal="Verify homepage", website_analysis={"website_type": "Corporate"})
    record = orchestrator.after_step(
        {
            "step_index": 1,
            "step_name": "open_page:Homepage",
            "status": "passed",
            "current_url": "https://example.com/",
            "page_title": "Example",
            "selector": None,
            "selector_found": True,
            "http_status": 200,
            "console_error_count": 0,
            "network_error_count": 0,
            "modal_detected": False,
            "execution_time_ms": 90,
        }
    )
    export = orchestrator.export()

    if record.decision.decision_type == DecisionType.CONTINUE and record.validated:
        findings["passed"].append("Orchestrator coordinates observer → engine → validator")
    else:
        findings["failed"].append("Orchestrator pipeline failed for passed step")

    if export.get("decision_count") == 1 and export.get("execution_context"):
        findings["passed"].append("Orchestrator exports trace and context")
    else:
        findings["failed"].append("Orchestrator export incomplete")

    validator = DecisionValidator()
    if validator.validate(record.decision).allowed:
        findings["passed"].append("Validator allows CONTINUE in Sprint 5.0")
    else:
        findings["failed"].append("Validator rejected CONTINUE")
    return findings


def audit_runner_integration() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    runner_path = BACKEND / "app" / "services" / "playwright_runner.py"
    source = runner_path.read_text(encoding="utf-8")

    required_tokens = (
        "ExecutionIntelligenceOrchestrator",
        "intelligence_orchestrator.after_step",
        "_execution_intelligence",
        "intelligence_input",
    )
    for token in required_tokens:
        if token in source:
            findings["passed"].append(f"Runner integrates {token}")
        else:
            findings["failed"].append(f"Runner missing integration token: {token}")

    blocked_tokens = (
        "decision.decision_type == DecisionType.RETRY",
        "abort_execution = intelligence",
    )
    for token in blocked_tokens:
        if token in source:
            findings["failed"].append(f"Runner must not add adaptive behaviour via intelligence: {token}")

    if "def _execute_sync(" in source:
        findings["passed"].append("_execute_sync preserved in playwright_runner")
    else:
        findings["failed"].append("_execute_sync missing")

    if "intelligence_orchestrator" in source and "abort_execution = intelligence" not in source:
        findings["passed"].append("Intelligence does not replace runner abort logic")
    else:
        findings["failed"].append("Intelligence must not control abort_execution")

    return findings


def audit_api_backward_compat() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.schemas import RunTestResponse

    fields = set(RunTestResponse.model_fields.keys())
    required = {
        "id",
        "goal",
        "status",
        "steps",
        "failures",
        "summary",
        "ai_plan",
        "ai_plan_source",
    }
    if required.issubset(fields):
        findings["passed"].append("RunTestResponse contract unchanged")
    else:
        findings["failed"].append("RunTestResponse core fields changed")

    if "execution_intelligence" not in fields:
        findings["passed"].append("No breaking execution_intelligence API field added")
    else:
        findings["warnings"].append("execution_intelligence exposed on API (optional metadata only)")
    return findings


def run_regression(script_name: str) -> tuple[str, int]:
    import subprocess

    proc = subprocess.run(
        [sys.executable, str(BACKEND / "scripts" / script_name)],
        cwd=str(BACKEND),
        capture_output=True,
        text=True,
    )
    output = proc.stdout + proc.stderr
    failures = 0
    for line in output.splitlines():
        if "TOTAL FAILURES:" in line:
            try:
                failures = int(line.split(":")[-1].strip())
            except ValueError:
                failures = 1
    return output, failures


def main() -> None:
    all_findings: dict[str, dict] = {}

    section("1. Execution Intelligence package")
    all_findings["modules"] = audit_package_modules()
    print(json.dumps(all_findings["modules"], indent=2))

    section("2. Observer")
    all_findings["observer"] = audit_observer()
    print(json.dumps(all_findings["observer"], indent=2))

    section("3. Decision Engine")
    all_findings["decision_engine"] = audit_decision_engine()
    print(json.dumps(all_findings["decision_engine"], indent=2))

    section("4. Execution Context")
    all_findings["execution_context"] = audit_execution_context()
    print(json.dumps(all_findings["execution_context"], indent=2))

    section("5. Orchestrator")
    all_findings["orchestrator"] = audit_orchestrator()
    print(json.dumps(all_findings["orchestrator"], indent=2))

    section("6. Runner integration")
    all_findings["integration"] = audit_runner_integration()
    print(json.dumps(all_findings["integration"], indent=2))

    section("7. API backward compatibility")
    all_findings["api"] = audit_api_backward_compat()
    print(json.dumps(all_findings["api"], indent=2))

    section("8. Regression audits")
    regression_scripts = [
        "sprint42_audit.py",
        "sprint41b_audit.py",
        "sprint41a_audit.py",
        "sprint41_audit.py",
        "sprint40_audit.py",
        "sprint391_audit.py",
    ]
    regression_failures = 0
    for script in regression_scripts:
        output, failures = run_regression(script)
        if failures == 0:
            all_findings.setdefault("regression", {"passed": [], "failed": [], "warnings": []})
            all_findings["regression"]["passed"].append(f"{script} passed")
        else:
            all_findings.setdefault("regression", {"passed": [], "failed": [], "warnings": []})
            all_findings["regression"]["failed"].append(f"{script} reported {failures} failure(s)")
            regression_failures += failures
            print(output[-2000:])
    print(json.dumps(all_findings.get("regression", {}), indent=2))

    total_failures = sum(
        len(bucket.get("failed", []))
        for bucket in all_findings.values()
        if isinstance(bucket, dict)
    ) + regression_failures

    print(f"\n{'=' * 60}\nTOTAL FAILURES: {total_failures}\n{'=' * 60}")

    if total_failures:
        sys.exit(1)

    print("\nSprint 5.0 audit passed.")


if __name__ == "__main__":
    main()
