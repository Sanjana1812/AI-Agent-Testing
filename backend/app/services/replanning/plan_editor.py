"""Edit remaining execution plans — never touch completed steps."""

from __future__ import annotations

import copy
from typing import Any

from app.services.replanning.models import PlanModification


def _clone_plan(plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [copy.deepcopy(step) for step in plan]


def replace_step(
    remaining_plan: list[dict[str, Any]],
    *,
    target_index: int,
    replacement: dict[str, Any],
    reason: str,
    confidence: float,
) -> tuple[list[dict[str, Any]], PlanModification]:
    if target_index < 0 or target_index >= len(remaining_plan):
        raise IndexError("replace_step target_index out of range for remaining plan")

    updated = _clone_plan(remaining_plan)
    updated[target_index] = copy.deepcopy(replacement)
    modification = PlanModification(
        operation="replace_step",
        target_step=target_index,
        replacement=copy.deepcopy(replacement),
        reason=reason,
        confidence=confidence,
    )
    return updated, modification


def insert_step(
    remaining_plan: list[dict[str, Any]],
    *,
    target_index: int,
    step: dict[str, Any],
    reason: str,
    confidence: float,
) -> tuple[list[dict[str, Any]], PlanModification]:
    updated = _clone_plan(remaining_plan)
    updated.insert(target_index, copy.deepcopy(step))
    modification = PlanModification(
        operation="insert_step",
        target_step=target_index,
        replacement=copy.deepcopy(step),
        reason=reason,
        confidence=confidence,
    )
    return updated, modification


def remove_remaining_step(
    remaining_plan: list[dict[str, Any]],
    *,
    target_index: int,
    reason: str,
    confidence: float,
) -> tuple[list[dict[str, Any]], PlanModification]:
    if target_index < 0 or target_index >= len(remaining_plan):
        raise IndexError("remove_remaining_step target_index out of range")

    updated = _clone_plan(remaining_plan)
    removed = updated.pop(target_index)
    modification = PlanModification(
        operation="remove_remaining_step",
        target_step=target_index,
        replacement=removed,
        reason=reason,
        confidence=confidence,
    )
    return updated, modification


def skip_remaining_step(
    remaining_plan: list[dict[str, Any]],
    *,
    target_index: int,
    reason: str,
    confidence: float,
) -> tuple[list[dict[str, Any]], PlanModification]:
    if target_index < 0 or target_index >= len(remaining_plan):
        raise IndexError("skip_remaining_step target_index out of range")

    updated = _clone_plan(remaining_plan)
    skipped = updated.pop(target_index)
    modification = PlanModification(
        operation="skip_remaining_step",
        target_step=target_index,
        replacement=skipped,
        reason=reason,
        confidence=confidence,
    )
    return updated, modification


def reorder_remaining_steps(
    remaining_plan: list[dict[str, Any]],
    *,
    order: list[int],
    reason: str,
    confidence: float,
) -> tuple[list[dict[str, Any]], PlanModification]:
    if sorted(order) != list(range(len(remaining_plan))):
        raise ValueError("reorder_remaining_steps order must be a full permutation")

    updated = [_clone_plan(remaining_plan)[index] for index in order]
    modification = PlanModification(
        operation="reorder_remaining_steps",
        target_step=0,
        replacement=None,
        reason=reason,
        confidence=confidence,
    )
    return updated, modification


def apply_replacement(
    remaining_plan: list[dict[str, Any]],
    *,
    failed_index: int,
    replacement_step: dict[str, Any],
    reason: str,
    confidence: float,
) -> tuple[list[dict[str, Any]], list[PlanModification]]:
    """Primary replan operation: replace the failed remaining step."""
    updated, modification = replace_step(
        remaining_plan,
        target_index=failed_index,
        replacement=replacement_step,
        reason=reason,
        confidence=confidence,
    )
    return updated, [modification]
