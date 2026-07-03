"""Sprint 5.1 verification harness — adaptive execution intelligence."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))


def section(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def audit_smart_skip_rule() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.execution_intelligence.decision_rules import SmartSkipRule
    from app.services.execution_intelligence.execution_context import build_execution_context
    from app.services.execution_intelligence.models import DecisionType, Observation

    rule = SmartSkipRule()
    context = build_execution_context(
        goal="Verify shopping cart",
        strategy={"execution_priority": ["Cart", "Checkout", "Product"]},
        total_steps=8,
    )
    obs = Observation(
        step_index=3,
        step_name='click:Show/Hide shortcuts shift + alt + Z',
        status="failed",
        current_url="https://shop.example/",
        page_title="Shop",
        selector="button.shortcut",
        selector_found=False,
        http_status=200,
        console_error_count=0,
        network_error_count=0,
        modal_detected=False,
        execution_time_ms=100,
        step_action="click",
        error_message="element not found",
        total_steps=8,
    )
    decision = rule.evaluate(obs, context)
    if decision and decision.decision_type == DecisionType.SKIP:
        findings["passed"].append("TEST_DESIGN non-priority failure yields SKIP")
    else:
        findings["failed"].append("Expected SKIP for non-priority TEST_DESIGN failure")

    priority_obs = Observation(
        step_index=2,
        step_name="click:Cart",
        status="failed",
        current_url="https://shop.example/",
        page_title="Shop",
        selector="a.cart",
        selector_found=False,
        http_status=200,
        console_error_count=0,
        network_error_count=0,
        modal_detected=False,
        execution_time_ms=100,
        step_action="click",
        error_message="not found",
        total_steps=8,
    )
    if rule.evaluate(priority_obs, context) is None:
        findings["passed"].append("Priority step failure is not skipped")
    else:
        findings["failed"].append("Priority step should not be skipped")
    return findings


def audit_selector_retry_rule() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.execution_intelligence.decision_rules import SelectorRetryRule
    from app.services.execution_intelligence.execution_context import build_execution_context
    from app.services.execution_intelligence.models import DecisionType, Observation

    rule = SelectorRetryRule()
    context = build_execution_context(goal="Verify navigation", total_steps=5)
    obs = Observation(
        step_index=2,
        step_name="verify_visible:Navigation",
        status="failed",
        current_url="https://example.com/",
        page_title="Example",
        selector="#main-nav",
        selector_found=False,
        http_status=200,
        console_error_count=0,
        network_error_count=0,
        modal_detected=False,
        execution_time_ms=80,
        step_action="verify_visible",
        error_message="Target not found",
        total_steps=5,
    )
    decision = rule.evaluate(obs, context)
    if decision and decision.decision_type == DecisionType.RETRY:
        findings["passed"].append("Selector failure with retries remaining yields RETRY")
        if decision.metadata.get("alternative_selector"):
            findings["passed"].append("RETRY includes alternative_selector metadata")
        else:
            findings["failed"].append("RETRY missing alternative_selector")
    else:
        findings["failed"].append("Expected RETRY for selector failure")

    context.retry_count["step_2"] = 2
    if rule.evaluate(obs, context) is None:
        findings["passed"].append("Selector retry budget exhausted returns None")
    else:
        findings["failed"].append("Expected no RETRY when budget exhausted")
    return findings


def audit_modal_dismiss_rule() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.execution_intelligence.decision_rules import ModalDismissRule
    from app.services.execution_intelligence.execution_context import build_execution_context
    from app.services.execution_intelligence.models import DecisionType, Observation

    rule = ModalDismissRule()
    context = build_execution_context(goal="Verify homepage", total_steps=4)
    obs = Observation(
        step_index=2,
        step_name="click:Sign in",
        status="failed",
        current_url="https://example.com/",
        page_title="Example",
        selector="a.signin",
        selector_found=False,
        http_status=200,
        console_error_count=0,
        network_error_count=0,
        modal_detected=True,
        execution_time_ms=90,
        step_action="click",
        error_message="blocked",
        total_steps=4,
    )
    decision = rule.evaluate(obs, context)
    if decision and decision.decision_type == DecisionType.RECOVER:
        findings["passed"].append("modal_detected=True yields RECOVER")
    else:
        findings["failed"].append("Expected RECOVER when modal detected")

    obs.modal_detected = False
    if rule.evaluate(obs, context) is None:
        findings["passed"].append("modal_detected=False yields None")
    else:
        findings["failed"].append("Expected None without modal")
    return findings


def audit_validator() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.execution_intelligence.models import Decision, DecisionType, Observation
    from app.services.execution_intelligence.execution_context import build_execution_context
    from app.services.execution_intelligence.validator import DecisionValidator

    validator = DecisionValidator()
    context = build_execution_context(
        goal="Verify cart",
        strategy={"execution_priority": ["Cart"]},
        total_steps=5,
    )
    obs = Observation(
        step_index=3,
        step_name="click:Shortcut",
        status="failed",
        current_url="https://example.com/",
        page_title="Example",
        selector=None,
        selector_found=False,
        http_status=200,
        console_error_count=0,
        network_error_count=0,
        modal_detected=False,
        execution_time_ms=50,
        step_action="click",
        error_message="not found",
        total_steps=5,
    )

    low_conf_skip = Decision(decision_type=DecisionType.SKIP, reason="test", confidence=0.3)
    if not validator.validate(low_conf_skip, obs, context).valid:
        findings["passed"].append("SKIP with confidence 0.3 rejected")
    else:
        findings["failed"].append("SKIP with low confidence should be rejected")

    high_retry = Decision(
        decision_type=DecisionType.RETRY,
        reason="retry",
        confidence=0.7,
        metadata={"alternative_selector": "nav", "retry_number": 3},
    )
    if not validator.validate(high_retry, obs, context).valid:
        findings["passed"].append("RETRY with retry_number 3 rejected")
    else:
        findings["failed"].append("RETRY with retry_number 3 should be rejected")

    recover = Decision(
        decision_type=DecisionType.RECOVER,
        reason="dismiss",
        confidence=0.8,
        metadata={
            "recovery_type": "modal_dismiss",
            "retry_after_recovery": True,
            "dismiss_selectors": ["button.close"],
        },
    )
    if validator.validate(recover, obs, context).valid:
        findings["passed"].append("RECOVER with modal_dismiss accepted")
    else:
        findings["failed"].append("RECOVER with modal_dismiss should be accepted")
    return findings


def audit_orchestrator_actions() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.execution_intelligence.models import DecisionType
    from app.services.execution_intelligence.orchestrator import ExecutionIntelligenceOrchestrator

    orchestrator = ExecutionIntelligenceOrchestrator()
    orchestrator.start(
        goal="Verify flows",
        strategy={"execution_priority": ["Cart", "Checkout"]},
        total_steps=6,
    )

    skip_outcome = orchestrator.process_step(
        {
            "step_index": 3,
            "step_name": 'click:Show/Hide shortcuts shift + alt + Z',
            "status": "failed",
            "current_url": "https://shop.example/",
            "page_title": "Shop",
            "selector": "button.shortcut",
            "selector_found": False,
            "http_status": 200,
            "console_error_count": 0,
            "network_error_count": 0,
            "modal_detected": False,
            "execution_time_ms": 120,
            "step_action": "click",
            "error_message": "element not found",
            "total_steps": 6,
        }
    )
    if skip_outcome.decision.decision_type == DecisionType.SKIP:
        findings["passed"].append("Orchestrator can produce SKIP for irrelevant failure")
        if orchestrator.context and orchestrator.context.skipped_steps:
            findings["passed"].append("SKIP recorded in skipped_steps")
        else:
            findings["failed"].append("skipped_steps not updated")
    else:
        findings["warnings"].append(f"Orchestrator skip path returned {skip_outcome.decision.decision_type}")

    orchestrator.record_retry(4)
    if orchestrator.context and orchestrator.context.retry_count.get("step_4") == 1:
        findings["passed"].append("retry_count incremented")
    else:
        findings["failed"].append("retry_count not incremented")

    orchestrator.record_recovery(4)
    if orchestrator.context and orchestrator.context.recovery_attempts.get("modal_4") == 1:
        findings["passed"].append("recovery_attempts incremented")
    else:
        findings["failed"].append("recovery_attempts not incremented")
    return findings


def audit_persistence_and_api() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.models.entities import TestRun
    from app.schemas import RunTestResponse

    if "execution_intelligence_log" in TestRun.__table__.columns:
        findings["passed"].append("TestRun has execution_intelligence_log column")
    else:
        findings["failed"].append("TestRun missing execution_intelligence_log")

    if "execution_intelligence" in RunTestResponse.model_fields:
        findings["passed"].append("RunTestResponse includes optional execution_intelligence")
    else:
        findings["failed"].append("RunTestResponse missing execution_intelligence field")

    runner = (BACKEND / "app" / "services" / "playwright_runner.py").read_text(encoding="utf-8")
    if "execution_intelligence_log" in runner and "_apply_adaptive_actions" in runner:
        findings["passed"].append("Runner exports execution intelligence log")
    else:
        findings["failed"].append("Runner missing intelligence log export")
    return findings


def run_regression(script_name: str) -> tuple[str, int]:
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

    section("1. SmartSkipRule")
    all_findings["smart_skip"] = audit_smart_skip_rule()
    print(json.dumps(all_findings["smart_skip"], indent=2))

    section("2. SelectorRetryRule")
    all_findings["selector_retry"] = audit_selector_retry_rule()
    print(json.dumps(all_findings["selector_retry"], indent=2))

    section("3. ModalDismissRule")
    all_findings["modal_dismiss"] = audit_modal_dismiss_rule()
    print(json.dumps(all_findings["modal_dismiss"], indent=2))

    section("4. Validator")
    all_findings["validator"] = audit_validator()
    print(json.dumps(all_findings["validator"], indent=2))

    section("5. Orchestrator")
    all_findings["orchestrator"] = audit_orchestrator_actions()
    print(json.dumps(all_findings["orchestrator"], indent=2))

    section("6. Persistence and API")
    all_findings["persistence"] = audit_persistence_and_api()
    print(json.dumps(all_findings["persistence"], indent=2))

    section("7. Regression audits")
    scripts = [
        "sprint50_audit.py",
        "sprint42_audit.py",
        "sprint41b_audit.py",
        "sprint41a_audit.py",
        "sprint41_audit.py",
        "sprint40_audit.py",
        "sprint391_audit.py",
    ]
    regression_failures = 0
    for script in scripts:
        output, failures = run_regression(script)
        if failures == 0:
            all_findings.setdefault("regression", {"passed": [], "failed": []})
            all_findings["regression"]["passed"].append(f"{script} passed")
        else:
            all_findings.setdefault("regression", {"passed": [], "failed": []})
            all_findings["regression"]["failed"].append(f"{script} reported {failures} failure(s)")
            regression_failures += failures
            print(output[-1500:])
    print(json.dumps(all_findings.get("regression", {}), indent=2))

    sprint51_failures = sum(
        len(v.get("failed", []))
        for key, v in all_findings.items()
        if key != "regression"
    )
    total_failures = sprint51_failures + regression_failures
    print(f"\n{'=' * 60}\nTOTAL FAILURES: {total_failures}\n{'=' * 60}")
    if total_failures:
        sys.exit(1)
    print("\nSprint 5.1 audit passed.")


if __name__ == "__main__":
    main()
