"""Multi-page adaptive journey builder with dynamic context refresh."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from app.services.planner.context_cache import ContextCache, contexts_from_cache, normalize_url, resolve_href
from app.services.planner.context_index import ContextIndex
from app.services.planner.context_refresh import (
    cache_stats_dict,
    simulate_refresh_after_action,
    validate_step_for_active_context,
)
from app.services.planner.display_labels import (
    verify_footer_label,
    verify_form_label,
    verify_hero_label,
    verify_section_label,
)
from app.services.planner.intent_classifier import IntentType
from app.services.planner.journey_builder import (
    MAX_STEPS,
    MIN_STEPS,
    _finalize,
    _link_step,
    _navigation_bar_step,
    _step,
)
from app.services.planner.journey_validator import validate_journey
from app.services.planner.memory import PlannerMemory
from app.services.planner.navigation_graph import GraphNode, NavigationGraph
from app.services.planner.selector_resolver import resolve_step
from app.services.website_context.json_builder import WebsiteContext

logger = logging.getLogger(__name__)


def _contexts_from_cache(cache: ContextCache, fallback: WebsiteContext) -> dict[str, ContextIndex]:
    return contexts_from_cache(cache, fallback)


def resolve_plan_for_contexts(
    plan: list[dict],
    contexts_by_url: dict[str, ContextIndex],
    default_index: ContextIndex,
) -> list[dict]:
    """Resolve selectors using the context active for each step."""
    used_selectors: set[str] = set()
    resolved: list[dict] = []
    for step in plan:
        index = contexts_by_url.get(step.get("context_url", ""), default_index)
        resolved.append(resolve_step(step, index, used_selectors=used_selectors))
    return resolved

ADAPTIVE_INTENTS = frozenset({IntentType.FLOW, IntentType.NAVIGATION, IntentType.CONTACT})


def _attach_context(step: dict, context_url: str, *, refreshed: bool = False) -> dict:
    enriched = dict(step)
    enriched["context_url"] = context_url
    if refreshed:
        enriched["context_refresh"] = True
    return enriched


def _pick_flow_targets(graph: NavigationGraph, limit: int = 2) -> list[GraphNode]:
    preferred_keywords = ("service", "about", "contact", "product", "work")
    ranked: list[GraphNode] = []
    for node in graph.primary_nav_destinations(limit=6):
        label = node.label.lower()
        if any(keyword in label for keyword in preferred_keywords):
            ranked.append(node)
    if not ranked:
        ranked = graph.primary_nav_destinations(limit=limit)
    seen: set[str] = set()
    unique: list[GraphNode] = []
    for node in ranked:
        key = node.label.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(node)
        if len(unique) >= limit:
            break
    return unique


def _page_segment_steps(
    index: ContextIndex,
    memory: PlannerMemory,
    *,
    page_label: str,
    include_form: bool = False,
) -> list[dict]:
    steps: list[dict] = []
    heading = index.hero_heading()
    hero_text = heading.get("text") if heading else page_label
    hero_label = verify_hero_label(hero_text) if hero_text else f"Verify {page_label} Hero"
    if memory.can_verify_section("hero", hero_label):
        steps.append(_step("verify_visible", target="hero", label=hero_label))

    section = index.highest_priority_section(semantic_type="features") or index.highest_priority_section()
    if section:
        label = verify_section_label(section.get("heading"), section.get("semantic_type"))
        if memory.can_verify_section("section", label):
            steps.append(_step("scroll", target="section", label=label))

    if include_form and index.has_forms():
        form_label = verify_form_label(index.context.get("forms", [{}])[0].get("classification"))
        if memory.can_verify_section("form", form_label):
            steps.append(_step("verify_visible", target="form", label=form_label))
            steps.append(_step("verify_form", target="form", label=form_label))

    if index.has_footer():
        footer_label = verify_footer_label()
        if memory.can_verify_section("footer", footer_label):
            steps.append(_step("verify_visible", target="footer", label=footer_label))

    return steps


def _link_node_with_href(node: GraphNode, base_url: str) -> GraphNode:
    href = resolve_href(base_url, node.href)
    if href and not node.href:
        return GraphNode(
            node_id=node.node_id,
            label=node.label,
            href=href,
            selector=node.selector,
            source=node.source,
            classification=node.classification,
            priority=node.priority,
            is_internal=node.is_internal,
        )
    return node


def build_multi_page_journey(
    goal: str,
    intent: IntentType,
    base_url: str,
    initial_context: WebsiteContext,
    cache: ContextCache,
    loader: Callable[[str], WebsiteContext],
) -> tuple[list[dict], dict[str, Any]]:
    """
    Build a multi-page journey using context cache + simulated refresh after navigation.
    """
    base_key = normalize_url(base_url)
    cache.put(base_key, initial_context)

    current_url = base_key
    current_index = ContextIndex(initial_context)
    current_graph = NavigationGraph.from_context(current_index)
    memory = PlannerMemory()
    steps: list[dict] = []

    steps.append(_attach_context(_step("open_page", label="Open Website"), current_url))

    if intent in {IntentType.FLOW, IntentType.NAVIGATION}:
        nav_bar = _navigation_bar_step(current_index, memory)
        if nav_bar and intent == IntentType.NAVIGATION:
            steps.append(_attach_context(nav_bar, current_url))

    hero = current_index.hero_heading()
    if hero and hero.get("text"):
        hero_step = _step("verify_visible", target="hero", label=verify_hero_label(hero["text"]))
        if memory.can_verify_section("hero", hero_step["label"]):
            steps.append(_attach_context(hero_step, current_url))
    elif current_index.has_hero():
        hero_step = _step("verify_visible", target="hero", label=verify_hero_label())
        steps.append(_attach_context(hero_step, current_url))

    targets = _pick_flow_targets(current_graph, limit=2 if intent == IntentType.FLOW else 2)
    if intent == IntentType.CONTACT:
        targets = [
            node
            for node in current_graph.navigation_nodes + current_graph.footer_nodes
            if "contact" in node.label.lower()
        ] or targets[:1]

    for node in targets:
        if len(steps) >= MAX_STEPS - 2:
            break

        link_node = _link_node_with_href(node, current_url)
        click = _link_step("click", link_node, memory=memory)
        if not click:
            continue
        click["href"] = link_node.href
        steps.append(_attach_context(click, current_url))

        refresh = simulate_refresh_after_action(
            current_url=current_url,
            action=click,
            current_context=current_index.context,
            cache=cache,
            loader=loader,
        )
        if refresh:
            current_url = refresh.url
            current_index = refresh.index
            memory = PlannerMemory()
            include_form = "contact" in node.label.lower() or intent == IntentType.CONTACT
            segment = _page_segment_steps(
                current_index,
                memory,
                page_label=node.label,
                include_form=include_form,
            )
            for segment_step in segment:
                steps.append(_attach_context(segment_step, current_url, refreshed=True))
        else:
            fallback_label = f'Verify "{node.label}" Page'
            steps.append(_attach_context(_step("verify_visible", target="section", label=fallback_label), current_url))

    if len(steps) < MIN_STEPS:
        return [], cache_stats_dict(cache)

    contexts_by_url = _contexts_from_cache(cache, initial_context)
    contexts_by_url.setdefault(base_key, ContextIndex(initial_context))

    plan = _finalize(steps)
    plan = resolve_plan_for_contexts(plan, contexts_by_url, ContextIndex(initial_context))

    active_url = base_key
    for step in plan:
        if step.get("context_url"):
            active_url = step["context_url"]
        active_index = contexts_by_url.get(active_url, current_index)
        ok, reason = validate_step_for_active_context(step, active_index, active_url=active_url)
        if not ok and reason:
            logger.warning("[MultiPageJourney] Cross-page validation failed: %s", reason)
            return [], cache_stats_dict(cache)

    valid, reasons = validate_journey(plan, intent, ContextIndex(initial_context))
    if not valid:
        logger.warning("[MultiPageJourney] Journey validation failed: %s", reasons)
        return [], cache_stats_dict(cache)

    return plan[:MAX_STEPS], cache_stats_dict(cache)


def try_build_adaptive_journey(
    goal: str,
    intent: IntentType,
    base_url: str,
    initial_context: WebsiteContext,
    cache: ContextCache,
    loader: Callable[[str], WebsiteContext],
) -> tuple[list[dict] | None, dict[str, Any]]:
    if intent not in ADAPTIVE_INTENTS:
        return None, cache_stats_dict(cache)

    plan, stats = build_multi_page_journey(goal, intent, base_url, initial_context, cache, loader)
    if plan:
        logger.info(
            "[MultiPageJourney] Built adaptive plan with %d steps, refreshes=%s pages=%s",
            len(plan),
            stats.get("context_refreshes"),
            stats.get("pages_visited"),
        )
        return plan, stats
    return None, stats
