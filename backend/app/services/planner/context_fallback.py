"""Context-aware deterministic test plan builder using priority-ranked elements."""

from __future__ import annotations

from app.services.planner.context_index import ContextIndex
from app.services.planner.display_labels import (
    click_button_label,
    click_link_label,
    verify_button_label,
    verify_footer_label,
    verify_form_label,
    verify_hero_label,
    verify_navigation_label,
    verify_section_label,
)

MAX_STEPS = 8
MIN_STEPS = 4


def _step(
    action: str,
    *,
    target: str | None = None,
    selector: str | None = None,
    label: str | None = None,
    value: str | None = None,
    text: str | None = None,
    ms: int | None = None,
) -> dict:
    entry: dict = {"action": action}
    if target:
        entry["target"] = target
    if selector:
        entry["selector"] = selector
    if label:
        entry["label"] = label
    if value is not None:
        entry["value"] = value
    if text is not None:
        entry["text"] = text
    if ms is not None:
        entry["ms"] = ms
    return entry


def _finalize(plan: list[dict]) -> list[dict]:
    if not plan:
        plan = [_step("open_page")]
    if plan[-1]["action"] != "capture":
        plan.append(_step("capture", label="Capture Screenshot"))
    return plan[:MAX_STEPS]


def _link_selector(link: dict) -> str | None:
    if link.get("selector"):
        return str(link["selector"])
    href = link.get("href", "")
    return f"a[href='{href}']" if href else None


def _button_step(action: str, index: ContextIndex, *, prefer_submit: bool = False) -> dict | None:
    if prefer_submit:
        submit_buttons = index.ranked_buttons(button_type="submit") or index.ranked_buttons(classification="Login")
        chosen = submit_buttons[0] if submit_buttons else index.highest_priority_cta()
    else:
        chosen = index.highest_priority_cta()
    if not chosen:
        return None
    text = chosen.get("text") or "button"
    target = "submit" if prefer_submit and chosen.get("type") == "submit" else "button"
    display = click_button_label(text) if action == "click" else verify_button_label(text)
    return _step(
        action,
        target=target,
        selector=chosen.get("selector"),
        label=display,
    )


def _nav_flow_steps(index: ContextIndex) -> list[dict]:
    steps: list[dict] = []
    if index.has_navigation():
        steps.append(_step("verify_visible", target="navigation", label=verify_navigation_label()))
        nav = index.highest_priority_nav_link()
        if nav:
            text = nav.get("text") or "navigation link"
            steps.append(
                _step(
                    "click",
                    target="link",
                    selector=_link_selector(nav),
                    label=click_link_label(text),
                )
            )
            steps.append(_step("wait", ms=800))
    if index.has_header():
        steps.append(_step("verify_visible", target="header", label="Verify Header"))
    return steps


def _hero_flow_steps(index: ContextIndex) -> list[dict]:
    steps: list[dict] = []
    heading = index.hero_heading()
    hero_section = index.hero_section()
    if heading and heading.get("text"):
        if index.has_sections():
            label = verify_hero_label(heading["text"])
            steps.append(_step("verify_visible", target="hero", label=label))
        else:
            steps.append(
                _step(
                    "verify_text",
                    text=heading["text"],
                    label=verify_hero_label(heading["text"]),
                )
            )
    elif hero_section:
        steps.append(
            _step(
                "verify_visible",
                target="hero",
                label=verify_section_label(hero_section.get("heading"), hero_section.get("semantic_type")),
            )
        )
    cta_step = _button_step("verify_visible", index)
    if cta_step:
        steps.append(cta_step)
    return steps


def _section_flow_steps(index: ContextIndex) -> list[dict]:
    steps: list[dict] = []
    section = index.highest_priority_section(semantic_type="features") or index.highest_priority_section()
    if section:
        label = verify_section_label(section.get("heading"), section.get("semantic_type"))
        steps.append(_step("scroll", target="section", label=label))
        steps.append(_step("verify_visible", target="section", label=label))
    return steps


def _footer_flow_steps(index: ContextIndex) -> list[dict]:
    steps: list[dict] = []
    has_footer_element = any(
        section.get("tag") == "footer" or section.get("semantic_type") == "footer"
        for section in index.context.get("sections", [])
    )
    if has_footer_element:
        steps.append(_step("scroll", target="footer", label=verify_footer_label()))
        steps.append(_step("verify_visible", target="footer", label=verify_footer_label()))
    footer = index.highest_priority_footer_link()
    if footer:
        text = footer.get("text") or "footer link"
        steps.append(
            _step(
                "click",
                target="link",
                selector=_link_selector(footer),
                label=click_link_label(text),
            )
        )
    return steps


def _form_flow_steps(index: ContextIndex, *, contact: bool = False) -> list[dict]:
    steps: list[dict] = []
    forms = index._by_priority(list(index.context.get("forms", [])))
    if not forms:
        return steps
    form = forms[0]
    form_label = verify_form_label(form.get("classification"))
    steps.append(_step("verify_visible", target="form", label=form_label))
    steps.append(_step("verify_form", target="form", label=form_label))
    if index.has_input_field():
        steps.append(_step("fill", target="input", value="QA Tester", label='Fill "Name"'))
    if index.has_email_field():
        steps.append(_step("fill", target="email", value="qa@example.com", label='Fill "Email"'))
    if index.has_password_field():
        steps.append(_step("fill", target="password", value="password123", label='Fill "Password"'))
    submit = _button_step("click", index, prefer_submit=True)
    if submit:
        steps.append(submit)
    elif index.has_buttons():
        fallback = _button_step("click", index)
        if fallback:
            steps.append(fallback)
    steps.append(_step("wait", ms=1000 if contact else 800))
    return steps


def build_context_plan(goal: str, intent: str, index: ContextIndex) -> list[dict]:
    """Build a plan using highest-priority discovered elements."""
    goal_lower = goal.lower()
    steps: list[dict] = [_step("open_page", label="Open Website")]

    if intent in {"login", "signup"} or any(w in goal_lower for w in ("login", "sign in", "signup", "register")):
        steps.extend(_form_flow_steps(index))
        section = index.highest_priority_section()
        if section:
            steps.append(
                _step(
                    "verify_visible",
                    target="section",
                    label=verify_section_label(section.get("heading"), section.get("semantic_type")),
                )
            )
    elif intent in {"contact", "form"} or "form" in goal_lower:
        steps.extend(_form_flow_steps(index, contact=True))
    elif intent == "search" or "search" in goal_lower:
        if index.has_input_field():
            steps.append(_step("verify_visible", target="input", label='Verify Search Input'))
            steps.append(_step("fill", target="input", value="test query", label='Fill "Search"'))
        btn = _button_step("click", index, prefer_submit=True)
        if btn:
            steps.append(btn)
        steps.append(_step("wait", ms=1000))
        section = index.highest_priority_section()
        if section:
            steps.append(
                _step(
                    "verify_visible",
                    target="section",
                    label=verify_section_label(section.get("heading"), "general"),
                )
            )
    elif intent == "navigation" or any(w in goal_lower for w in ("navbar", "navigation", "menu")):
        steps.extend(_nav_flow_steps(index))
    elif "footer" in goal_lower:
        steps.extend(_footer_flow_steps(index))
    elif "hero" in goal_lower:
        steps.extend(_hero_flow_steps(index))
    else:
        steps.extend(_nav_flow_steps(index))
        steps.extend(_hero_flow_steps(index))
        cta = _button_step("click", index)
        if cta:
            steps.append(cta)
        steps.extend(_section_flow_steps(index))
        steps.extend(_footer_flow_steps(index))

    if len(steps) < MIN_STEPS:
        has_heading_step = any(s.get("target") == "hero" or s.get("action") == "verify_text" for s in steps)
        if index.has_hero() and not has_heading_step:
            heading = index.hero_heading()
            steps.append(
                _step(
                    "verify_visible",
                    target="hero",
                    label=verify_hero_label(heading.get("text") if heading else None),
                )
            )
        if not any(s.get("action") == "click" for s in steps):
            link = index.highest_priority_footer_link() or index.highest_priority_nav_link()
            if link:
                steps.append(
                    _step(
                        "click",
                        target="link",
                        selector=_link_selector(link),
                        label=click_link_label(link.get("text") or "link"),
                    )
                )
        steps.append(_step("wait", ms=800))

    return _finalize(steps)
