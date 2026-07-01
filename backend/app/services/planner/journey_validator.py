"""Validate generated QA journeys before execution."""

from __future__ import annotations

from app.services.planner.context_index import ContextIndex
from app.services.planner.intent_classifier import IntentType
from app.services.planner.memory import PlannerMemory

from app.services.planner.semantic_filter import is_ignored_label
from app.services.planner.selector_ranker import MIN_CONFIDENCE_THRESHOLD
from app.services.planner.selector_validator import is_generic_selector

MIN_STEPS = 4
MAX_STEPS = 8

LOGO_CLASSIFICATIONS = ContextIndex.LOGO_CLASSIFICATIONS


def _step_signature(step: dict) -> str:
    action = step.get("action", "")
    target = step.get("target", "")
    selector = step.get("selector", "")
    label = step.get("label", "")
    text = step.get("text", "")
    return "|".join([action, target, selector, label, text]).lower()


def validate_journey(
    plan: list[dict],
    intent: IntentType,
    index: ContextIndex,
) -> tuple[bool, list[str]]:
    """Return (is_valid, rejection_reasons)."""
    reasons: list[str] = []

    if len(plan) < MIN_STEPS:
        reasons.append(f"Plan has fewer than {MIN_STEPS} actions")
    if len(plan) > MAX_STEPS:
        reasons.append(f"Plan exceeds {MAX_STEPS} actions")

    if not plan or plan[-1].get("action") != "capture":
        reasons.append("Plan must end with capture")

    click_signatures: list[str] = []
    selector_usage: dict[str, int] = {}
    verify_targets: dict[str, int] = {}
    nav_clicks: list[str] = []
    breadcrumb_clicks: list[str] = []
    memory = PlannerMemory()
    pending_navigation = False

    meaningful_actions = 0
    has_navigation_progression = intent != IntentType.NAVIGATION

    for step in plan:
        action = step.get("action")
        target = step.get("target")
        label = (step.get("label") or "").lower()
        selector = step.get("selector")

        if action in {"click", "verify_visible", "verify_form", "scroll", "fill"}:
            meaningful_actions += 1

        if action == "click":
            signature = _step_signature(step)
            if signature in click_signatures:
                reasons.append(f"Duplicate click detected: {step.get('label') or target}")
            click_signatures.append(signature)
            pending_navigation = True

            if is_ignored_label(step.get("label")):
                reasons.append(f"Accessibility or low-value click rejected: {step.get('label')}")

            if any(token in label for token in ("breadcrumb", "facebook", "instagram", "twitter", "linkedin")):
                reasons.append(f"Low-value navigation click rejected: {step.get('label')}")

            if not selector:
                reasons.append(f"Click action missing resolved selector: {step.get('label') or target}")
            elif is_generic_selector(selector):
                reasons.append(f"Generic click selector rejected: {selector}")
            elif float(step.get("selector_confidence") or 100) < MIN_CONFIDENCE_THRESHOLD:
                reasons.append(f"Click selector below confidence threshold: {selector}")

            if selector:
                selector_key = selector.strip().lower()
                selector_usage[selector_key] = selector_usage.get(selector_key, 0) + 1
                if selector_usage[selector_key] > 1:
                    reasons.append(f"Duplicate selector detected: {selector}")

            if target in {"button", "link"} and not selector:
                reasons.append(f"Generic click target without selector: {target}")

            if "logo" in label or step.get("classification") in LOGO_CLASSIFICATIONS:
                reasons.append("Logo interaction detected")

            if target == "link" or selector:
                link_key = memory.selector_key(selector) or memory.link_key(selector=selector, label=step.get("label"))
                if link_key in nav_clicks:
                    reasons.append(f"Navigation loop detected for link '{step.get('label')}'")
                nav_clicks.append(link_key)
                if "breadcrumb" in label:
                    if link_key in breadcrumb_clicks:
                        reasons.append("Breadcrumb loop detected")
                    breadcrumb_clicks.append(link_key)

        if action == "wait":
            pending_navigation = False

        if action in {"verify_visible", "verify_form", "scroll", "fill"} and action != "fill":
            if selector and is_generic_selector(selector):
                reasons.append(f"Generic verification selector rejected: {selector}")
            if selector:
                selector_key = selector.strip().lower()
                selector_usage[selector_key] = selector_usage.get(selector_key, 0) + 1
                if selector_usage[selector_key] > 1 and target != "section":
                    reasons.append(f"Duplicate selector detected: {selector}")

        if action == "fill" and not selector and target in {"email", "password", "input"}:
            reasons.append(f"Fill action missing resolved selector for {target}")

        if action == "verify_visible":
            if pending_navigation and target == "hero" and not step.get("context_refresh"):
                reasons.append("Hero verification before navigation completed")
            section_key = memory.section_key(target, step.get("label"))
            verify_targets[section_key] = verify_targets.get(section_key, 0) + 1
            if target == "hero" and verify_targets[section_key] > 1:
                reasons.append("Repeated hero verification")
            if target == "footer" and verify_targets[section_key] > 1:
                reasons.append("Repeated footer verification")
            if target == "navigation" and verify_targets[section_key] > 1:
                reasons.append("Repeated navigation verification")

        memory.record_step(step)

        if action in {"verify_visible", "verify_form", "verify_text", "scroll", "wait", "capture"}:
            pending_navigation = False

    if meaningful_actions < 2:
        reasons.append("Plan lacks meaningful interactions")

    if intent == IntentType.NAVIGATION:
        link_clicks = [step for step in plan if step.get("action") == "click" and step.get("selector")]
        verifies_after_nav = any(step.get("action") in {"verify_visible", "verify_form", "verify_text"} for step in plan)
        if len(link_clicks) < 1 and index.has_navigation():
            reasons.append("Navigation intent requires at least one meaningful link transition")
        elif link_clicks and not verifies_after_nav:
            reasons.append("Navigation journey missing destination verification")
        else:
            has_navigation_progression = len(link_clicks) >= 1 or not index.has_navigation()

    if intent == IntentType.FLOW:
        has_cta_or_nav = any(step.get("action") == "click" and step.get("selector") for step in plan)
        has_content_verify = any(
            step.get("target") in {"hero", "section", "footer"}
            or step.get("action") == "verify_text"
            for step in plan
        )
        if not has_cta_or_nav and index.has_buttons():
            reasons.append("Flow journey missing primary interaction")
        if not has_content_verify and (index.has_hero() or index.has_sections()):
            reasons.append("Flow journey missing content verification")

    if intent in {IntentType.LOGIN, IntentType.CONTACT, IntentType.FORM}:
        has_form_step = any(step.get("target") == "form" or step.get("action") == "verify_form" for step in plan)
        if index.has_forms() and not has_form_step:
            reasons.append("Form intent requires form verification")

    isolated_click = False
    for idx, step in enumerate(plan):
        if step.get("action") != "click":
            continue
        next_steps = plan[idx + 1 : idx + 3]
        if not any(
            follow.get("action") in {"verify_visible", "verify_form", "verify_text", "wait", "scroll", "capture", "fill"}
            for follow in next_steps
        ):
            isolated_click = True
    if isolated_click and intent not in {IntentType.SEARCH, IntentType.PURCHASE}:
        reasons.append("Isolated click without follow-up verification")

    if intent == IntentType.NAVIGATION and not has_navigation_progression:
        reasons.append("Meaningless navigation sequence")

    return len(reasons) == 0, reasons
