"""Generate semantic step replacement candidates from known site structure."""

from __future__ import annotations

import re
from typing import Any

from app.services.planner.context_index import ContextIndex
from app.services.planner.display_labels import click_link_label
from app.services.planner.navigation_graph import NavigationGraph
from app.services.replanning.models import PlanCandidate

# Deterministic semantic synonyms — never invent business flows.
SEMANTIC_ALTERNATIVES: dict[str, list[str]] = {
    "pricing": ["plans", "subscriptions", "compare plans", "packages", "billing"],
    "price": ["plans", "subscriptions", "packages"],
    "plans": ["pricing", "subscriptions", "compare plans"],
    "subscriptions": ["plans", "pricing", "packages"],
    "search": ["product search", "find products", "browse products", "shop", "catalog"],
    "product search": ["search", "find products", "browse products"],
    "find products": ["search", "browse products", "shop"],
    "browse products": ["search", "find products", "shop"],
    "contact": ["support", "help", "get in touch", "customer service"],
    "support": ["contact", "help", "customer service"],
    "help": ["support", "contact", "faq"],
    "login": ["sign in", "account", "my account"],
    "sign in": ["login", "account", "my account"],
    "signup": ["register", "create account", "join"],
    "register": ["signup", "create account", "join"],
    "about": ["company", "our story", "who we are"],
    "home": ["homepage", "main"],
    "cart": ["basket", "bag", "shopping cart"],
    "checkout": ["payment", "place order", "buy"],
    "store": ["shop", "products", "catalog"],
    "shop": ["store", "products", "catalog"],
}


def _normalize_label(value: str) -> str:
    text = re.sub(r"^(click|verify|open_page|fill|scroll):\s*", "", value, flags=re.I)
    text = text.strip().strip('"').lower()
    return text


def _extract_step_label(step: dict[str, Any], step_name: str = "") -> str:
    if step.get("label"):
        return _normalize_label(str(step["label"]))
    if step_name:
        return _normalize_label(step_name)
    return _normalize_label(str(step.get("target") or ""))


def _collect_navigation_labels(
    *,
    website_context: dict[str, Any] | None,
    website_analysis: dict[str, Any] | None,
    strategy: dict[str, Any] | None,
    planner_metadata: dict[str, Any] | None,
) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(label: str, selector: str | None = None, href: str | None = None, source: str = "") -> None:
        key = label.strip().lower()
        if not key or key in seen:
            return
        seen.add(key)
        entries.append(
            {
                "label": label.strip(),
                "selector": selector or "",
                "href": href or "",
                "source": source,
            }
        )

    if website_context:
        index = ContextIndex(website_context)
        graph = NavigationGraph.from_context(index)
        for node in (
            graph.navigation_nodes
            + graph.footer_nodes
            + graph.primary_nav_destinations(limit=8)
        ):
            add(node.label, node.selector, node.href, f"navigation_graph:{node.source}")

        for link in website_context.get("navigation", []) + website_context.get("links", []):
            text = str(link.get("text") or "").strip()
            add(text, link.get("selector"), link.get("href"), "website_context")

    if website_analysis:
        for journey in website_analysis.get("critical_user_journeys") or []:
            if isinstance(journey, str):
                add(journey, source="website_analysis:journey")
        for flow in website_analysis.get("recommended_test_flow") or []:
            if isinstance(flow, str):
                add(flow, source="website_analysis:flow")

    if strategy:
        for item in strategy.get("recommended_test_flow") or strategy.get("execution_priority") or []:
            if isinstance(item, str):
                add(item, source="strategy")

    if planner_metadata:
        for item in planner_metadata.get("primary_navigation") or []:
            if isinstance(item, str):
                add(item, source="planner_metadata:navigation")
        journey = planner_metadata.get("generated_journey")
        if isinstance(journey, list):
            for item in journey:
                if isinstance(item, str):
                    add(item, source="planner_metadata:journey")

    return entries


def _synonym_candidates(original_label: str) -> list[str]:
    normalized = original_label.lower()
    candidates: list[str] = []
    for key, synonyms in SEMANTIC_ALTERNATIVES.items():
        if key in normalized:
            candidates.extend(synonyms)
        for synonym in synonyms:
            if synonym in normalized:
                candidates.append(key)
                candidates.extend(synonyms)
    return candidates


def _build_click_step(label: str, nav_entry: dict[str, str]) -> dict[str, Any]:
    step: dict[str, Any] = {
        "action": "click",
        "target": "link",
        "label": click_link_label(label),
        "classification": "Link",
    }
    if nav_entry.get("selector"):
        step["selector"] = nav_entry["selector"]
    if nav_entry.get("href"):
        step["href"] = nav_entry["href"]
    return step


def _score_match(original: str, candidate_label: str, source: str) -> float:
    original_norm = original.lower()
    candidate_norm = candidate_label.lower()
    if original_norm == candidate_norm:
        return 0.0
    if candidate_norm in _synonym_candidates(original_norm):
        score = 0.88
        if source.startswith("navigation_graph"):
            score = 0.93
        elif source.startswith("strategy"):
            score = 0.9
        return score
    for synonym in _synonym_candidates(original_norm):
        if synonym in candidate_norm or candidate_norm in synonym:
            return 0.85
    return 0.0


def generate_candidates(
    *,
    failed_step: dict[str, Any],
    step_index: int,
    step_name: str,
    website_context: dict[str, Any] | None = None,
    website_analysis: dict[str, Any] | None = None,
    strategy: dict[str, Any] | None = None,
    planner_metadata: dict[str, Any] | None = None,
    visited_pages: list[str] | None = None,
) -> list[PlanCandidate]:
    """Return ranked semantic replacement candidates for a failed step."""
    original_label = _extract_step_label(failed_step, step_name)
    if not original_label:
        return []

    nav_entries = _collect_navigation_labels(
        website_context=website_context,
        website_analysis=website_analysis,
        strategy=strategy,
        planner_metadata=planner_metadata,
    )
    visited = {page.lower() for page in (visited_pages or [])}
    candidates: list[PlanCandidate] = []

    for entry in nav_entries:
        label = entry["label"]
        if label.lower() == original_label:
            continue
        if entry.get("href") and entry["href"].lower() in visited:
            continue
        score = _score_match(original_label, label, entry.get("source", ""))
        if score < 0.85:
            continue
        replacement = _build_click_step(label, entry)
        candidates.append(
            PlanCandidate(
                step_index=step_index,
                original_step=dict(failed_step),
                replacement_step=replacement,
                confidence=score,
                reason=f"Semantic alternative '{label}' matches unavailable target '{original_label}'.",
                source=entry.get("source", "semantic_map"),
            )
        )

    candidates.sort(key=lambda item: item.confidence, reverse=True)
    return candidates


def find_best_candidate(
    *,
    failed_step: dict[str, Any],
    step_index: int,
    step_name: str,
    website_context: dict[str, Any] | None = None,
    website_analysis: dict[str, Any] | None = None,
    strategy: dict[str, Any] | None = None,
    planner_metadata: dict[str, Any] | None = None,
    visited_pages: list[str] | None = None,
) -> PlanCandidate | None:
    candidates = generate_candidates(
        failed_step=failed_step,
        step_index=step_index,
        step_name=step_name,
        website_context=website_context,
        website_analysis=website_analysis,
        strategy=strategy,
        planner_metadata=planner_metadata,
        visited_pages=visited_pages,
    )
    return candidates[0] if candidates else None
