"""Intent-aware journey builder for deterministic QA plans."""

from __future__ import annotations

import logging
from collections.abc import Callable

from app.services.planner.context_cache import ContextCache
from app.services.planner.context_index import ContextIndex
from app.services.planner.context_validator import validate_plan_against_context
from app.services.planner.display_labels import (
    build_step_label,
    click_button_label,
    click_link_label,
    verify_footer_label,
    verify_form_label,
    verify_hero_label,
    verify_navigation_label,
    verify_section_label,
)
from app.services.planner.intent_classifier import IntentType, classify_intent, intent_from_legacy
from app.services.planner.journey_validator import MAX_STEPS, MIN_STEPS, validate_journey
from app.services.planner.memory import PlannerMemory
from app.services.planner.navigation_graph import GraphNode, NavigationGraph
from app.services.planner.selector_resolver import resolve_plan_selectors
from app.services.website_context.json_builder import WebsiteContext

logger = logging.getLogger(__name__)


def _step(
    action: str,
    *,
    target: str | None = None,
    selector: str | None = None,
    label: str | None = None,
    value: str | None = None,
    text: str | None = None,
    ms: int | None = None,
    classification: str | None = None,
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
    if classification:
        entry["classification"] = classification
    if not entry.get("label"):
        entry["label"] = build_step_label(entry)
    return entry


def _finalize(plan: list[dict]) -> list[dict]:
    if not plan:
        plan = [_step("open_page", label="Open Website")]
    body = [step for step in plan if step.get("action") != "capture"]
    if not body or body[0]["action"] != "open_page":
        body.insert(0, _step("open_page", label="Open Website"))

    if len(body) > MAX_STEPS - 1:
        head = [body[0]]
        tail = body[-(MAX_STEPS - 2) :]
        body = head + tail

    body.append(_step("capture", label="Capture Screenshot"))
    return body[:MAX_STEPS]


def _link_step(action: str, node: GraphNode, *, memory: PlannerMemory) -> dict | None:
    if action == "click" and not memory.can_click_link(
        selector=node.selector,
        label=node.label,
        href=node.href,
        classification=node.classification,
    ):
        return None
    label = click_link_label(node.label) if action == "click" else f'Verify "{node.label}" Page'
    return _step(
        action,
        target="link",
        selector=node.selector,
        label=label,
        classification=node.classification,
    )


def _cta_click_step(graph: NavigationGraph, memory: PlannerMemory) -> dict | None:
    if not graph.cta_node:
        return None
    node = graph.cta_node
    if not memory.can_click_cta(selector=node.selector, label=node.label, classification=node.classification):
        return None
    return _step(
        "click",
        target="button",
        selector=node.selector,
        label=click_button_label(node.label),
        classification=node.classification,
    )


def _hero_verify_step(index: ContextIndex, memory: PlannerMemory) -> dict | None:
    if not index.has_hero():
        return None
    heading = index.hero_heading()
    label = verify_hero_label(heading.get("text") if heading else None)
    if not memory.can_verify_section("hero", label):
        return None
    return _step("verify_visible", target="hero", label=label)


def _section_verify_step(index: ContextIndex, memory: PlannerMemory, *, semantic_type: str | None = None) -> dict | None:
    section = index.highest_priority_section(semantic_type=semantic_type) or index.highest_priority_section()
    if not section:
        return None
    label = verify_section_label(section.get("heading"), section.get("semantic_type"))
    if not memory.can_verify_section("section", label):
        return None
    return _step("verify_visible", target="section", label=label)


def _section_scroll_step(index: ContextIndex, memory: PlannerMemory) -> dict | None:
    section = index.highest_priority_section(semantic_type="features") or index.highest_priority_section()
    if not section:
        return None
    label = verify_section_label(section.get("heading"), section.get("semantic_type"))
    if not memory.can_verify_section("section", label):
        return None
    return _step("scroll", target="section", label=label)


def _footer_steps(index: ContextIndex, memory: PlannerMemory, *, include_click: bool = False) -> list[dict]:
    steps: list[dict] = []
    if not index.has_footer():
        return steps
    label = verify_footer_label()
    if memory.can_verify_section("footer", label):
        steps.append(_step("scroll", target="footer", label=label))
        steps.append(_step("verify_visible", target="footer", label=label))
    if include_click:
        footer = index.highest_priority_footer_link()
        if footer and memory.can_click_link(
            selector=footer.get("selector"),
            label=footer.get("text"),
            href=footer.get("href"),
            classification=footer.get("classification", ""),
        ):
            steps.append(
                _step(
                    "click",
                    target="link",
                    selector=footer.get("selector") or (f"a[href='{footer['href']}']" if footer.get("href") else None),
                    label=click_link_label(footer.get("text") or "footer link"),
                    classification=footer.get("classification", ""),
                )
            )
    return steps


def _navigation_bar_step(index: ContextIndex, memory: PlannerMemory) -> dict | None:
    if not index.has_navigation():
        return None
    label = verify_navigation_label()
    if not memory.can_verify_section("navigation", label):
        return None
    return _step("verify_visible", target="navigation", label=label)


def _form_journey_steps(index: ContextIndex, memory: PlannerMemory, *, contact: bool = False) -> list[dict]:
    steps: list[dict] = []
    forms = index._by_priority(list(index.context.get("forms", [])))
    if not forms:
        return steps
    form = forms[0]
    form_label = verify_form_label(form.get("classification"))
    if memory.can_verify_section("form", form_label):
        steps.append(_step("verify_visible", target="form", label=form_label))
        steps.append(_step("verify_form", target="form", label=form_label))
    if index.has_email_field():
        steps.append(_step("fill", target="email", value="qa@example.com", label='Fill "Email"'))
    if index.has_password_field():
        steps.append(_step("fill", target="password", value="password123", label='Fill "Password"'))
    if index.has_input_field() and not index.has_email_field():
        steps.append(_step("fill", target="input", value="QA Tester", label='Fill "Name"'))
    submit = index.ranked_buttons(button_type="submit") or index.ranked_buttons(classification="Login")
    chosen = submit[0] if submit else index.highest_priority_cta()
    if chosen and memory.can_click_cta(selector=chosen.get("selector"), label=chosen.get("text"), classification=chosen.get("classification", "")):
        steps.append(
            _step(
                "click",
                target="submit" if chosen.get("type") == "submit" else "button",
                selector=chosen.get("selector"),
                label=click_button_label(chosen.get("text") or "Submit"),
                classification=chosen.get("classification", ""),
            )
        )
    steps.append(_step("wait", ms=1000 if contact else 800))
    section = _section_verify_step(index, memory)
    if section:
        steps.append(section)
    return steps


def _build_flow_journey(index: ContextIndex, graph: NavigationGraph, memory: PlannerMemory, *, variant: int = 0) -> list[dict]:
    steps: list[dict] = [_step("open_page", label="Open Website")]

    hero = _hero_verify_step(index, memory)
    if hero:
        steps.append(hero)

    cta = _cta_click_step(graph, memory)
    if cta:
        steps.append(cta)
        destination = _section_verify_step(index, memory, semantic_type="features")
        if not destination:
            destination = _section_verify_step(index, memory)
        if destination:
            steps.append(destination)

    scroll = _section_scroll_step(index, memory)
    if scroll:
        steps.append(scroll)

    if variant >= 1:
        nav = graph.primary_nav_destinations(limit=1)
        if nav:
            click = _link_step("click", nav[0], memory=memory)
            if click:
                steps.append(click)
                steps.append(_step("verify_visible", target="section", label=f'Verify "{nav[0].label}" Page'))

    steps.extend(_footer_steps(index, memory, include_click=variant >= 2))
    return steps


def _build_navigation_journey(index: ContextIndex, graph: NavigationGraph, memory: PlannerMemory, *, variant: int = 0) -> list[dict]:
    steps: list[dict] = [_step("open_page", label="Open Website")]

    nav_bar = _navigation_bar_step(index, memory)
    if nav_bar:
        steps.append(nav_bar)

    destinations = graph.primary_nav_destinations(limit=2 + variant)
    if not destinations:
        destinations = [
            GraphNode(
                node_id=f"fallback:{link.get('href')}",
                label=link.get("text") or "link",
                href=link.get("href"),
                selector=link.get("selector") or (f"a[href='{link['href']}']" if link.get("href") else None),
                source="link",
                classification=link.get("classification", "Link"),
                priority=int(link.get("priority", 0)),
            )
            for link in index.ranked_links(internal_only=True)[:2]
        ]

    for node in destinations[:2]:
        click = _link_step("click", node, memory=memory)
        if not click:
            continue
        steps.append(click)
        steps.append(_step("verify_visible", target="section", label=f'Verify "{node.label}" Page'))

    if len(steps) < MIN_STEPS:
        hero = _hero_verify_step(index, memory)
        if hero:
            steps.append(hero)

    return steps


def _build_login_journey(index: ContextIndex, graph: NavigationGraph, memory: PlannerMemory) -> list[dict]:
    steps: list[dict] = [_step("open_page", label="Open Login Page")]
    steps.extend(_form_journey_steps(index, memory))
    if len(steps) < MIN_STEPS:
        steps.extend(_build_flow_journey(index, graph, memory))
    return steps


def _build_contact_journey(index: ContextIndex, graph: NavigationGraph, memory: PlannerMemory) -> list[dict]:
    steps: list[dict] = [_step("open_page", label="Open Website")]
    contact_links = [
        node
        for node in graph.navigation_nodes + graph.footer_nodes
        if "contact" in node.label.lower()
    ]
    if contact_links:
        click = _link_step("click", contact_links[0], memory=memory)
        if click:
            steps.append(click)
            steps.append(_step("wait", ms=800))
    steps.extend(_form_journey_steps(index, memory, contact=True))
    if len(steps) < MIN_STEPS:
        steps.extend(_build_flow_journey(index, graph, memory))
    return steps


def _build_form_journey(index: ContextIndex, graph: NavigationGraph, memory: PlannerMemory) -> list[dict]:
    steps: list[dict] = [_step("open_page", label="Open Website")]
    steps.extend(_form_journey_steps(index, memory))
    if len(steps) < MIN_STEPS:
        steps.extend(_build_flow_journey(index, graph, memory))
    return steps


def _build_purchase_journey(index: ContextIndex, graph: NavigationGraph, memory: PlannerMemory) -> list[dict]:
    steps: list[dict] = [_step("open_page", label="Open Website")]
    purchase_nodes = [
        node
        for node in graph.navigation_nodes + graph.footer_nodes
        if any(word in node.label.lower() for word in ("shop", "buy", "cart", "pricing", "product"))
    ]
    if purchase_nodes:
        click = _link_step("click", purchase_nodes[0], memory=memory)
        if click:
            steps.append(click)
            steps.append(_step("wait", ms=800))
    cta = _cta_click_step(graph, memory)
    if cta:
        steps.append(cta)
    section = _section_verify_step(index, memory)
    if section:
        steps.append(section)
    if len(steps) < MIN_STEPS:
        steps.extend(_build_flow_journey(index, graph, memory))
    return steps


def _build_search_journey(index: ContextIndex, graph: NavigationGraph, memory: PlannerMemory) -> list[dict]:
    steps: list[dict] = [_step("open_page", label="Open Website")]
    if index.has_input_field():
        steps.append(_step("verify_visible", target="input", label='Verify Search Input'))
        steps.append(_step("fill", target="input", value="test query", label='Fill "Search"'))
    submit = index.ranked_buttons(button_type="submit") or index.ranked_buttons()
    if submit and memory.can_click_cta(selector=submit[0].get("selector"), label=submit[0].get("text")):
        steps.append(
            _step(
                "click",
                target="button",
                selector=submit[0].get("selector"),
                label=click_button_label(submit[0].get("text") or "Search"),
            )
        )
    steps.append(_step("wait", ms=1000))
    section = _section_verify_step(index, memory)
    if section:
        steps.append(section)
    if len(steps) < MIN_STEPS:
        steps.extend(_build_flow_journey(index, graph, memory))
    return steps


def _build_unknown_journey(index: ContextIndex, graph: NavigationGraph, memory: PlannerMemory, *, variant: int = 0) -> list[dict]:
    return _build_flow_journey(index, graph, memory, variant=variant)


def build_journey(
    goal: str,
    intent: IntentType,
    index: ContextIndex,
    graph: NavigationGraph,
    memory: PlannerMemory,
    *,
    variant: int = 0,
) -> list[dict]:
    """Build a journey for the given intent without final validation."""
    builders = {
        IntentType.FLOW: _build_flow_journey,
        IntentType.NAVIGATION: _build_navigation_journey,
        IntentType.LOGIN: _build_login_journey,
        IntentType.CONTACT: _build_contact_journey,
        IntentType.FORM: _build_form_journey,
        IntentType.PURCHASE: _build_purchase_journey,
        IntentType.SEARCH: _build_search_journey,
        IntentType.UNKNOWN: _build_unknown_journey,
    }
    builder = builders.get(intent, _build_unknown_journey)
    if builder in {_build_flow_journey, _build_navigation_journey, _build_unknown_journey}:
        plan = builder(index, graph, memory, variant=variant)
    else:
        plan = builder(index, graph, memory)

    enriched: list[dict] = []
    for step in plan:
        memory.record_step(step)
        enriched.append(step)
    return enriched


def build_validated_journey(
    goal: str,
    intent: IntentType | str,
    index: ContextIndex,
    *,
    base_url: str | None = None,
    cache: ContextCache | None = None,
    loader: Callable[[str], WebsiteContext] | None = None,
    max_attempts: int = 3,
) -> list[dict]:
    """
    Build and validate a journey, regenerating with alternate variants on failure.
    """
    if isinstance(intent, str):
        resolved_intent = intent_from_legacy(intent)
        if resolved_intent == IntentType.UNKNOWN:
            resolved_intent = classify_intent(goal)
    else:
        resolved_intent = intent

    if base_url and cache is not None and loader is not None:
        from app.services.planner.context_cache import normalize_url
        from app.services.planner.multi_page_journey import try_build_adaptive_journey

        cache.put(normalize_url(base_url), index.context)
        adaptive, _stats = try_build_adaptive_journey(
            goal,
            resolved_intent,
            base_url,
            index.context,
            cache,
            loader,
        )
        if adaptive:
            logger.info("[JourneyBuilder] Using adaptive multi-page journey (%d steps)", len(adaptive))
            return adaptive

    graph = NavigationGraph.from_context(index)
    logger.info("[JourneyBuilder] Intent=%s graph=%s", resolved_intent.value, graph.tree_summary())

    last_reasons: list[str] = []
    for attempt in range(max_attempts):
        memory = PlannerMemory()
        plan = build_journey(goal, resolved_intent, index, graph, memory, variant=attempt)
        plan = _finalize(plan)
        plan = resolve_plan_selectors(plan, index)
        valid, reasons = validate_journey(plan, resolved_intent, index)
        if not valid:
            last_reasons = reasons
            logger.warning("[JourneyBuilder] Attempt %s rejected: %s", attempt + 1, reasons)
            continue

        context_validated, rejections = validate_plan_against_context(plan, index)
        if rejections:
            logger.warning("[JourneyBuilder] Context rejected %d step(s)", len(rejections))
        if len(context_validated) >= MIN_STEPS:
            final_plan = resolve_plan_selectors(_finalize(context_validated), index)
            ok, _ = validate_journey(final_plan, resolved_intent, index)
            if ok:
                return final_plan

    logger.warning("[JourneyBuilder] Falling back to simplified flow after failures: %s", last_reasons)
    memory = PlannerMemory(allow_repetition=True)
    minimal = [_step("open_page", label="Open Website")]
    heading = index.hero_heading()
    if heading and heading.get("text") and index.supports_text(heading["text"]):
        minimal.append(
            _step(
                "verify_text",
                text=heading["text"],
                label=verify_hero_label(heading["text"]),
            )
        )
    elif index.has_hero():
        minimal.append(_step("verify_visible", target="hero", label=verify_hero_label()))
    minimal.append(_step("wait", ms=800))
    return resolve_plan_selectors(_finalize(minimal), index)
