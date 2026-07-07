"""Read-only execution quality evaluation."""

from __future__ import annotations

from typing import Any

from app.services.evaluation.explainability import DimensionEvaluation


def _evaluate_execution_detail(result: dict[str, Any]) -> DimensionEvaluation:
    summary_data = result.get("summary") or {}
    execution_summary_data = result.get("execution_summary") or {}
    steps = result.get("steps") or []

    total = int(
        execution_summary_data.get("total_steps")
        or summary_data.get("total_steps")
        or len(steps)
        or 0
    )
    passed = int(
        execution_summary_data.get("completed_steps")
        or summary_data.get("passed_steps")
        or 0
    )
    skipped = int(execution_summary_data.get("skipped_steps") or 0)

    completion = (passed / total * 100.0) if total else 0.0

    retries = int(execution_summary_data.get("retry_count") or 0)
    recoveries = int(execution_summary_data.get("recovery_count") or 0)
    replanned = int(execution_summary_data.get("replan_count") or 0)
    skipped_adaptive = 0

    assertion_passed = 0
    assertion_failed = 0
    for step in steps:
        for assertion in step.get("assertions") or []:
            if assertion.get("passed"):
                assertion_passed += 1
            else:
                assertion_failed += 1

    score = completion
    if assertion_passed:
        assertion_rate = assertion_passed / (assertion_passed + assertion_failed) * 100.0
        score = (score * 0.7) + (assertion_rate * 0.3)
    if retries > 0:
        score = max(score - min(retries * 3, 15), 0)
    if replanned > 0:
        score = max(score - min(replanned * 2, 10), 0)
    if recoveries > 0:
        score = min(score + min(recoveries * 2, 6), 100.0)
    if skipped or skipped_adaptive:
        score = max(score - min((skipped + skipped_adaptive) * 4, 20), 0)

    strengths: list[str] = []
    weaknesses: list[str] = []
    recommendations: list[str] = []

    if total:
        strengths.append(f"{passed} of {total} steps executed successfully.")
    if retries > 0:
        strengths.append("Retry mechanism engaged and completed.")
        if retries > 1:
            weaknesses.append(f"{retries} selector retries required.")
            recommendations.append("Stabilize selectors to reduce retry overhead.")
    if recoveries > 0:
        strengths.append("Modal recovery worked during execution.")
    if replanned > 0:
        weaknesses.append(f"{replanned} step(s) required dynamic replanning.")
        recommendations.append("Review replanned steps for upstream planner improvements.")
    if skipped or skipped_adaptive:
        count = skipped + skipped_adaptive
        weaknesses.append(f"{count} unnecessary or adaptive skip(s) detected.")
        recommendations.append("Reduce skipped steps by improving step relevance and selectors.")
    if assertion_passed:
        strengths.append(f"{assertion_passed} assertion(s) passed.")
    if assertion_failed:
        weaknesses.append(f"{assertion_failed} assertion(s) failed.")
        recommendations.append("Investigate failed assertions and update validation targets.")

    if not strengths:
        strengths.append("Execution pipeline completed.")
    if not weaknesses:
        weaknesses.append("No significant execution weaknesses detected.")
    if not recommendations:
        recommendations.append("Maintain current execution stability and assertion coverage.")

    execution_summary = (
        f"Completed {passed}/{total} steps ({completion:.0f}%); "
        f"{assertion_passed} assertions passed, {assertion_failed} failed; "
        f"retries={retries}, recoveries={recoveries}, skipped={skipped + skipped_adaptive}, "
        f"replanned={replanned}, run health={execution_summary_data.get('final_status') or summary_data.get('health', 'UNKNOWN')}."
    )

    reasoning = (
        f"Execution score {score:.0f}% based on {completion:.0f}% step completion"
        + (f", {assertion_passed} successful assertions" if assertion_passed else "")
        + (f", {retries} retries" if retries else "")
        + (f", {recoveries} recoveries" if recoveries else "")
        + (f", {skipped + skipped_adaptive} skipped steps" if skipped or skipped_adaptive else "")
        + (f", {replanned} replanned steps" if replanned else "")
        + "."
    )

    return DimensionEvaluation(
        score=round(score, 1),
        summary=execution_summary,
        strengths=strengths,
        weaknesses=weaknesses,
        reasoning=reasoning,
        recommendations=recommendations,
    )


def evaluate_execution(result: dict[str, Any]) -> tuple[float, str]:
    detail = _evaluate_execution_detail(result)
    return detail.score, detail.summary


def evaluate_execution_detail(result: dict[str, Any]) -> DimensionEvaluation:
    return _evaluate_execution_detail(result)
