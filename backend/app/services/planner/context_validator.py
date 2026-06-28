"""Validate AI plans against discovered Website Context."""

from __future__ import annotations

import logging

from app.services.planner.context_index import ContextIndex

logger = logging.getLogger(__name__)

NON_ELEMENT_ACTIONS = frozenset({"open_page", "wait", "capture"})


def validate_step_against_context(step: dict, index: ContextIndex) -> tuple[bool, str | None]:
    """Return (valid, reason) for a single plan step."""
    action = step.get("action")
    if action in NON_ELEMENT_ACTIONS:
        return True, None

    if action == "verify_text":
        text = step.get("text", "")
        if index.supports_text(text):
            return True, None
        return False, f"Text '{text}' was not discovered on the page"

    target = step.get("target")
    if not target:
        return False, f"Action '{action}' is missing a target"

    if index.supports_target(target):
        return True, None

    return False, f"Target '{target}' is not present in Website Context"


def validate_plan_against_context(plan: list[dict], index: ContextIndex) -> tuple[list[dict], list[str]]:
    """
    Filter plan steps to those supported by context.

    Returns the validated plan and a list of rejection reasons for dropped steps.
    """
    validated: list[dict] = []
    rejections: list[str] = []

    for step in plan:
        ok, reason = validate_step_against_context(step, index)
        if ok:
            validated.append(step)
        elif reason:
            rejections.append(f"{step.get('action')}: {reason}")
            logger.warning("[Planner] Rejected step %s — %s", step, reason)

    return validated, rejections
