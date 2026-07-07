"""Read-only evidence completeness evaluation."""

from __future__ import annotations

from typing import Any

from app.services.evaluation.explainability import DimensionEvaluation

_EVIDENCE_LABELS = {
    "screenshot": "Screenshots captured",
    "console_logs": "Console logs collected",
    "network_logs": "Network logs collected",
    "dom_snapshot": "DOM snapshot available",
    "assertion_evidence": "Assertion evidence recorded",
    "failure_evidence": "Failure evidence captured",
}


def _evaluate_evidence_detail(
    evidence_package: dict[str, Any] | None,
    result: dict[str, Any] | None = None,
) -> DimensionEvaluation:
    if not evidence_package:
        screenshot = (result or {}).get("screenshot")
        if screenshot:
            return DimensionEvaluation(
                score=40.0,
                summary="Minimal evidence available (screenshot only).",
                strengths=["Screenshot captured."],
                weaknesses=["Evidence package was not fully assembled."],
                reasoning="Only a screenshot was available without a structured evidence package.",
                recommendations=["Enable full evidence capture including logs and DOM snapshot."],
            )
        return DimensionEvaluation(
            score=0.0,
            summary="No evidence package was produced for this run.",
            strengths=["Evidence evaluation completed."],
            weaknesses=["No evidence package was produced for this run."],
            reasoning="No runtime evidence was captured for this test run.",
            recommendations=["Ensure evidence engine runs after execution completes."],
        )

    checks = {
        "screenshot": bool(evidence_package.get("screenshot") or (result or {}).get("screenshot")),
        "console_logs": bool(evidence_package.get("console_logs")),
        "network_logs": bool(evidence_package.get("network_logs")),
        "dom_snapshot": bool(evidence_package.get("dom_snapshot")),
        "assertion_evidence": bool(evidence_package.get("assertions")),
        "failure_evidence": True,
    }
    if evidence_package.get("failure_evidence"):
        checks["failure_evidence"] = True
    elif (result or {}).get("summary", {}).get("failed_steps", 0) == 0:
        checks["failure_evidence"] = True
    else:
        checks["failure_evidence"] = False

    available = sum(1 for value in checks.values() if value)
    score = (available / len(checks)) * 100.0

    strengths: list[str] = []
    weaknesses: list[str] = []
    recommendations: list[str] = []

    for name, ok in checks.items():
        label = _EVIDENCE_LABELS.get(name, name.replace("_", " "))
        if ok:
            strengths.append(f"{label}.")
        else:
            weaknesses.append(f"Missing {label.lower()}.")
            if name == "network_logs":
                recommendations.append(
                    "Capture network request logs for failed actions to improve traceability."
                )
            elif name == "dom_snapshot":
                recommendations.append("Persist a DOM snapshot for post-run inspection.")
            elif name == "failure_evidence":
                recommendations.append("Attach failure-specific evidence when steps fail.")

    if not recommendations:
        recommendations.append("Evidence capture is comprehensive; maintain current settings.")

    parts = [f"{name.replace('_', ' ')}={'yes' if ok else 'no'}" for name, ok in checks.items()]
    evidence_summary = (
        f"Evidence completeness {available}/{len(checks)} ({score:.0f}%). " + "; ".join(parts) + "."
    )

    reasoning = (
        f"Evidence score {score:.0f}% from {available} of {len(checks)} evidence types available: "
        + ", ".join(name.replace("_", " ") for name, ok in checks.items() if ok)
        + "."
    )

    return DimensionEvaluation(
        score=round(score, 1),
        summary=evidence_summary,
        strengths=strengths,
        weaknesses=weaknesses,
        reasoning=reasoning,
        recommendations=recommendations,
    )


def evaluate_evidence(
    evidence_package: dict[str, Any] | None,
    result: dict[str, Any] | None = None,
) -> tuple[float, str]:
    detail = _evaluate_evidence_detail(evidence_package, result)
    return detail.score, detail.summary


def evaluate_evidence_detail(
    evidence_package: dict[str, Any] | None,
    result: dict[str, Any] | None = None,
) -> DimensionEvaluation:
    return _evaluate_evidence_detail(evidence_package, result)
