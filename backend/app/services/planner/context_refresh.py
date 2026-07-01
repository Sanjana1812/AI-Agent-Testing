"""Context refresh orchestration for multi-page journeys."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.services.planner.context_cache import ContextCache, normalize_url, resolve_href
from app.services.planner.context_index import ContextIndex
from app.services.planner.dom_fingerprint import hero_heading_text
from app.services.planner.page_observer import PageObserver, PageSnapshot
from app.services.website_context.json_builder import WebsiteContext

logger = logging.getLogger(__name__)


@dataclass
class RefreshResult:
    context: WebsiteContext
    index: ContextIndex
    url: str
    cache_hit: bool
    refreshed: bool


def should_refresh_after_navigation(action: dict, *, before: PageSnapshot, after: PageSnapshot) -> bool:
    """Public helper used by planner validation and adaptive journey builder."""
    return PageObserver().should_refresh(action, before=before, after=after)


def predict_post_click_url(base_url: str, action: dict) -> str | None:
    """Best-effort target URL after a link click."""
    href = action.get("href") or action.get("target_href")
    if not href and action.get("selector"):
        selector = str(action["selector"])
        if "href=" in selector:
            fragment = selector.split("href=", 1)[1].strip("'\"[]")
            href = fragment.split("'")[0].split('"')[0]
    return resolve_href(base_url, href)


def refresh_for_url(
    url: str,
    cache: ContextCache,
    loader: Callable[[str], WebsiteContext],
    *,
    force: bool = False,
) -> RefreshResult:
    key = normalize_url(url)
    if force:
        context, cache_hit = cache.refresh(key, loader)
    else:
        context, cache_hit = cache.get_or_load(key, loader)
    return RefreshResult(
        context=context,
        index=ContextIndex(context),
        url=key,
        cache_hit=cache_hit,
        refreshed=True,
    )


def simulate_refresh_after_action(
    *,
    current_url: str,
    action: dict,
    current_context: WebsiteContext,
    cache: ContextCache,
    loader: Callable[[str], WebsiteContext],
) -> RefreshResult | None:
    """
    Simulate context refresh after a navigation-like action during planning.
    Returns None when refresh is not required.
    """
    observer = PageObserver()
    before = observer.from_context(current_context, current_url)

    next_url = current_url
    if action.get("action") == "click":
        predicted = predict_post_click_url(current_url, action)
        if predicted:
            next_url = predicted
    elif action.get("action") == "open_page":
        next_url = normalize_url(current_url)

    if action.get("action") not in {"click", "open_page"}:
        if action.get("action") == "fill" and action.get("target") == "password":
            next_url = current_url
        else:
            return None

    if action.get("action") == "click" and not predict_post_click_url(current_url, action):
        return None

    try:
        after_context, cache_hit = cache.get_or_load(next_url, loader)
    except Exception as exc:
        logger.warning("[ContextRefresh] Failed to load context for %s: %s", next_url, exc)
        return None

    after = observer.from_context(after_context, next_url)
    if not should_refresh_after_navigation(action, before=before, after=after):
        return None

    cache.stats.context_refreshes += 1
    logger.info("[ContextRefresh] Refresh simulated for %s after %s", next_url, action.get("action"))
    return RefreshResult(
        context=after_context,
        index=ContextIndex(after_context),
        url=next_url,
        cache_hit=cache_hit,
        refreshed=True,
    )


def validate_step_for_active_context(
    step: dict,
    active_index: ContextIndex,
    *,
    active_url: str,
) -> tuple[bool, str | None]:
    """Reject steps that reference elements from a stale page context."""
    from app.services.planner.context_validator import validate_step_against_context

    step_url = step.get("context_url") or active_url
    if step.get("context_url") and step["context_url"] != active_url:
        return False, f"Step targets stale context {step.get('context_url')} (active {active_url})"

    ok, reason = validate_step_against_context(step, active_index)
    if not ok:
        return ok, reason

    action = step.get("action")
    if action in {"verify_visible", "verify_text"} and step.get("target") == "hero":
        hero = hero_heading_text(active_index.context)
        label = step.get("label", "")
        if hero and hero not in label and step.get("action") != "verify_text":
            return False, f"Hero verification '{label}' does not match active page hero '{hero}'"

    return True, None


def cache_stats_dict(cache: ContextCache) -> dict[str, Any]:
    return {
        "context_refreshes": cache.stats.context_refreshes,
        "pages_visited": list(cache.stats.pages_visited),
        "cache_hits": cache.stats.cache_hits,
        "cache_misses": cache.stats.cache_misses,
    }
