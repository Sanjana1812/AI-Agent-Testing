"""Cache Website Context by normalized URL."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

from app.services.website_context.json_builder import WebsiteContext

logger = logging.getLogger(__name__)


def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    scheme = parsed.scheme or "https"
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/") or "/"
    return f"{scheme}://{netloc}{path}"


def resolve_href(base_url: str, href: str | None) -> str | None:
    if not href:
        return None
    href = href.strip()
    if href.startswith("#") or href.lower().startswith("javascript:"):
        return None
    return normalize_url(urljoin(base_url, href))


@dataclass
class ContextCacheStats:
    cache_hits: int = 0
    cache_misses: int = 0
    context_refreshes: int = 0
    pages_visited: list[str] = field(default_factory=list)


class ContextCache:
    """In-memory cache of Website Context keyed by normalized URL."""

    def __init__(self) -> None:
        self._entries: dict[str, WebsiteContext] = {}
        self.stats = ContextCacheStats()

    def get(self, url: str) -> WebsiteContext | None:
        key = normalize_url(url)
        return self._entries.get(key)

    def put(self, url: str, context: WebsiteContext) -> None:
        key = normalize_url(url)
        self._entries[key] = context
        if key not in self.stats.pages_visited:
            self.stats.pages_visited.append(key)

    def get_or_load(
        self,
        url: str,
        loader: Callable[[str], WebsiteContext],
    ) -> tuple[WebsiteContext, bool]:
        """Return (context, cache_hit)."""
        key = normalize_url(url)
        cached = self._entries.get(key)
        if cached is not None:
            self.stats.cache_hits += 1
            logger.info("[ContextCache] Cache hit for %s", key)
            return cached, True

        self.stats.cache_misses += 1
        logger.info("[ContextCache] Cache miss — loading context for %s", key)
        context = loader(key)
        self.put(key, context)
        return context, False

    def refresh(
        self,
        url: str,
        loader: Callable[[str], WebsiteContext],
    ) -> tuple[WebsiteContext, bool]:
        """Force-refresh context for a URL (still counts cache reuse if unchanged URL revisited)."""
        key = normalize_url(url)
        context, hit = self.get_or_load(key, loader)
        self.stats.context_refreshes += 1
        return context, hit


def contexts_from_cache(cache: ContextCache, fallback: WebsiteContext) -> dict[str, "ContextIndex"]:
    """Build ContextIndex map for every URL stored in the cache."""
    from app.services.planner.context_index import ContextIndex

    contexts: dict[str, ContextIndex] = {}
    for visited_url in cache.stats.pages_visited:
        context = cache.get(visited_url) or fallback
        contexts[normalize_url(visited_url)] = ContextIndex(context)
    return contexts
