"""Compute explainable diffs between original and modified remaining plans."""

from __future__ import annotations

from typing import Any


def _step_signature(step: dict[str, Any]) -> str:
    action = step.get("action", "")
    label = step.get("label") or step.get("target") or ""
    return f"{action}:{label}".lower()


def diff_remaining_plans(
    original_remaining: list[dict[str, Any]],
    modified_remaining: list[dict[str, Any]],
) -> dict[str, Any]:
    original_labels = [_step_signature(step) for step in original_remaining]
    modified_labels = [_step_signature(step) for step in modified_remaining]

    replaced: list[dict[str, Any]] = []
    for index, original in enumerate(original_remaining):
        if index >= len(modified_remaining):
            replaced.append(
                {
                    "index": index,
                    "original": _step_signature(original),
                    "replacement": None,
                    "change": "removed",
                }
            )
            continue
        modified = modified_remaining[index]
        if _step_signature(original) != _step_signature(modified):
            replaced.append(
                {
                    "index": index,
                    "original": _step_signature(original),
                    "replacement": _step_signature(modified),
                    "change": "replaced",
                }
            )

    inserted = []
    if len(modified_remaining) > len(original_remaining):
        for index in range(len(original_remaining), len(modified_remaining)):
            inserted.append(
                {
                    "index": index,
                    "replacement": _step_signature(modified_remaining[index]),
                    "change": "inserted",
                }
            )

    return {
        "original_steps": original_labels,
        "modified_steps": modified_labels,
        "replacements": replaced,
        "insertions": inserted,
        "affected_remaining_steps": modified_labels,
    }
