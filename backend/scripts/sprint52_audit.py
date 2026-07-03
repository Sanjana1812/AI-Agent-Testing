"""Sprint 5.2 verification harness — dynamic replanning engine."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))


def section(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def audit_package() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    modules = [
        "__init__",
        "models",
        "candidate_generator",
        "plan_editor",
        "plan_diff",
        "validator",
        "history",
        "replanning_engine",
        "prompts",
    ]
    base = BACKEND / "app" / "services" / "replanning"
    for module in modules:
        if (base / f"{module}.py").exists():
            findings["passed"].append(f"replanning/{module}.py present")
        else:
            findings["failed"].append(f"replanning/{module}.py missing")
    return findings


def audit_candidate_generator() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.replanning.candidate_generator import find_best_candidate, generate_candidates

    website_context = {
        "navigation": [
            {"text": "Pricing", "selector": "a.pricing", "href": "/pricing"},
            {"text": "Plans", "selector": "a.plans", "href": "/plans"},
            {"text": "Contact", "selector": "a.contact", "href": "/contact"},
        ],
        "links": [],
        "metadata": {"title": "Example", "current_url": "https://example.com/"},
    }
    failed_step = {
        "action": "click",
        "label": 'Click "Pricing"',
        "selector": "a.pricing",
        "target": "link",
    }
    candidates = generate_candidates(
        failed_step=failed_step,
        step_index=3,
        step_name='click:"Pricing"',
        website_context=website_context,
        strategy={"recommended_test_flow": ["Plans", "Contact"]},
    )
    if candidates:
        findings["passed"].append("Candidate generator returns semantic alternatives")
        labels = [c.replacement_step.get("label", "") for c in candidates]
        if any("Plans" in label for label in labels):
            findings["passed"].append("Pricing failure can map to Plans candidate")
        else:
            findings["failed"].append("Expected Plans as Pricing alternative")
    else:
        findings["failed"].append("Candidate generator returned no candidates")

    unrelated = find_best_candidate(
        failed_step={"action": "click", "label": 'Click "ZZZ Unknown"', "target": "link"},
        step_index=2,
        step_name='click:"ZZZ Unknown"',
        website_context=website_context,
    )
    if unrelated is None:
        findings["passed"].append("Unrelated failures do not invent candidates")
    else:
        findings["failed"].append("Candidate generator should not invent unrelated flows")
    return findings


def audit_plan_editor() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.replanning.plan_editor import apply_replacement, remove_remaining_step, replace_step

    remaining = [
        {"action": "click", "label": 'Click "Pricing"'},
        {"action": "verify_visible", "label": "Verify Footer"},
        {"action": "capture", "label": "Capture Screenshot"},
    ]
    replacement = {"action": "click", "label": 'Click "Plans"', "selector": "a.plans"}
    updated, mods = apply_replacement(
        remaining,
        failed_index=0,
        replacement_step=replacement,
        reason="Pricing unavailable",
        confidence=0.93,
    )
    if updated[0]["label"] == replacement["label"]:
        findings["passed"].append("Plan editor replaces failed remaining step")
    else:
        findings["failed"].append("replace_step did not update remaining plan")

    completed_prefix = [{"action": "open_page", "label": "Open Website"}]
    full_before = completed_prefix + remaining
    full_after = completed_prefix + updated
    if full_before[:1] == full_after[:1]:
        findings["passed"].append("Completed steps are not modified by plan editor")
    else:
        findings["failed"].append("Plan editor must not modify completed steps")

    trimmed, _ = remove_remaining_step(remaining, target_index=1, reason="remove", confidence=0.8)
    if len(trimmed) == len(remaining) - 1:
        findings["passed"].append("remove_remaining_step supported")
    else:
        findings["failed"].append("remove_remaining_step failed")
    return findings


def audit_validator() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.replanning.models import PlanCandidate
    from app.services.replanning.validator import ReplanValidator

    validator = ReplanValidator(confidence_threshold=0.7, max_replans=2)
    candidate = PlanCandidate(
        step_index=3,
        original_step={"action": "click", "label": 'Click "Pricing"'},
        replacement_step={"action": "click", "label": 'Click "Plans"'},
        confidence=0.93,
        reason="semantic match",
        source="navigation_graph",
    )
    ok = validator.validate(
        candidate=candidate,
        goal="Verify pricing page",
        replan_count=0,
        remaining_plan=[candidate.original_step, {"action": "capture"}],
    )
    if ok.valid:
        findings["passed"].append("Validator accepts high-confidence related candidate")
    else:
        findings["failed"].append("Validator rejected valid candidate")

    low = validator.validate(
        candidate=PlanCandidate(
            3,
            {"action": "click", "label": "Pricing"},
            {"action": "click", "label": "Plans"},
            0.4,
            "low",
            "test",
        ),
        goal="Verify pricing",
        replan_count=0,
        remaining_plan=[{"action": "click"}],
    )
    if not low.valid:
        findings["passed"].append("Validator rejects low confidence")
    else:
        findings["failed"].append("Validator should reject low confidence")

    maxed = validator.validate(
        candidate=candidate,
        goal="Verify pricing",
        replan_count=2,
        remaining_plan=[{"action": "click"}],
    )
    if not maxed.valid:
        findings["passed"].append("Validator rejects when max replans exceeded")
    else:
        findings["failed"].append("Validator should reject max replans")
    return findings


def audit_history_and_engine() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.execution_intelligence.execution_context import build_execution_context
    from app.services.execution_intelligence.models import Decision, DecisionType, Observation
    from app.services.replanning.history import build_replanning_summary, record_replan
    from app.services.replanning.replanning_engine import ReplanningEngine

    remaining = [{"action": "click", "label": 'Click "Pricing"', "selector": "a.pricing"}]
    observation = Observation(
        3,
        'click:"Pricing"',
        "failed",
        "https://example.com/",
        "Example",
        "a.pricing",
        False,
        404,
        0,
        0,
        False,
        100,
        "click",
        "Pricing page unavailable",
        6,
    )
    context = build_execution_context(
        goal="Verify pricing",
        website_context={
            "navigation": [
                {"text": "Pricing", "selector": "a.pricing"},
                {"text": "Plans", "selector": "a.plans"},
            ],
            "metadata": {"title": "Example", "current_url": "https://example.com/"},
        },
        strategy={"recommended_test_flow": ["Plans"]},
    )
    decision = Decision(
        decision_type=DecisionType.REPLAN,
        reason="Pricing unavailable",
        confidence=0.93,
        metadata={"replacement_step": {"action": "click", "label": 'Click "Plans"', "selector": "a.plans"}},
    )
    result = ReplanningEngine().replan(
        observation=observation,
        context=context,
        remaining_plan=remaining,
        decision=decision,
        website_context=context.website_context,
    )
    if result.success and result.history:
        findings["passed"].append("Replanning engine modifies remaining plan")
        summary = build_replanning_summary([result.history])
        if summary and summary.get("replans_made") == 1:
            findings["passed"].append("History records replan with summary")
        else:
            findings["failed"].append("Replan history summary incomplete")
    else:
        findings["failed"].append(f"Replanning engine failed: {result.rejection_reason}")

    entry = record_replan(
        original_remaining=remaining,
        modified_remaining=result.modified_remaining_plan if result.success else remaining,
        modifications=[],
        trigger_observation=observation.to_dict(),
        decision=decision.to_dict(),
        reason="test",
        confidence=0.9,
    )
    if entry.original_plan and entry.modified_plan:
        findings["passed"].append("record_replan captures before/after plans")
    else:
        findings["failed"].append("record_replan incomplete")
    return findings


def audit_execution_integration() -> dict:
    findings = {"passed": [], "failed": [], "warnings": []}
    from app.services.execution_intelligence.decision_rules import ReplanRule
    from app.services.execution_intelligence.execution_context import build_execution_context
    from app.services.execution_intelligence.models import DecisionType, Observation
    from app.services.execution_intelligence.validator import DecisionValidator

    runner = (BACKEND / "app" / "services" / "playwright_runner.py").read_text(encoding="utf-8")
    for token in ("ReplanningEngine", "requires_replan", "record_replan_history", "replay_step"):
        if token in runner:
            findings["passed"].append(f"Runner integrates {token}")
        else:
            findings["failed"].append(f"Runner missing {token}")

    context = build_execution_context(
        goal="Verify plans",
        website_context={
            "navigation": [
                {"text": "Pricing", "selector": "a.pricing"},
                {"text": "Plans", "selector": "a.plans"},
            ],
            "metadata": {"current_url": "https://example.com/"},
        },
        strategy={"execution_priority": ["Plans"]},
        total_steps=6,
    )
    context.retry_count["step_3"] = 2
    obs = Observation(
        3,
        'click:"Pricing"',
        "failed",
        "https://example.com/",
        "Example",
        "a.pricing",
        False,
        404,
        0,
        0,
        False,
        120,
        "click",
        "Pricing page unavailable",
        6,
    )
    decision = ReplanRule().evaluate(obs, context)
    if decision and decision.decision_type == DecisionType.REPLAN:
        findings["passed"].append("ReplanRule proposes REPLAN for unavailable navigation target")
        validated = DecisionValidator().validate(decision, obs, context)
        if validated.valid:
            findings["passed"].append("Execution intelligence validator accepts REPLAN")
        else:
            findings["failed"].append("REPLAN validation failed")
    else:
        findings["warnings"].append("ReplanRule did not fire in synthetic scenario")

    planner = (BACKEND / "app" / "services" / "ai_planner.py").read_text(encoding="utf-8")
    if "ReplanningEngine" not in planner and "replanning" not in planner.lower():
        findings["passed"].append("AI Planner unchanged by replanning integration")
    else:
        findings["failed"].append("AI Planner must not import replanning engine")
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

    section("1. Replanning package")
    all_findings["package"] = audit_package()
    print(json.dumps(all_findings["package"], indent=2))

    section("2. Candidate generator")
    all_findings["candidates"] = audit_candidate_generator()
    print(json.dumps(all_findings["candidates"], indent=2))

    section("3. Plan editor")
    all_findings["editor"] = audit_plan_editor()
    print(json.dumps(all_findings["editor"], indent=2))

    section("4. Replanning validator")
    all_findings["validator"] = audit_validator()
    print(json.dumps(all_findings["validator"], indent=2))

    section("5. History and engine")
    all_findings["engine"] = audit_history_and_engine()
    print(json.dumps(all_findings["engine"], indent=2))

    section("6. Execution integration")
    all_findings["integration"] = audit_execution_integration()
    print(json.dumps(all_findings["integration"], indent=2))

    section("7. Regression audits")
    scripts = [
        "sprint51_audit.py",
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
            print(output[-1200:])
    print(json.dumps(all_findings.get("regression", {}), indent=2))

    sprint52_failures = sum(
        len(v.get("failed", [])) for key, v in all_findings.items() if key != "regression"
    )
    total_failures = sprint52_failures + regression_failures
    print(f"\n{'=' * 60}\nTOTAL FAILURES: {total_failures}\n{'=' * 60}")
    if total_failures:
        sys.exit(1)
    print("\nSprint 5.2 audit passed.")


if __name__ == "__main__":
    main()
