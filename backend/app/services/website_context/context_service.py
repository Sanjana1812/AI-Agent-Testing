"""Orchestrates crawlers and parsers to produce Website Context."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
from typing import Any

from playwright.sync_api import Page

from app.services.website_context import (
    button_parser,
    components_parser,
    footer_parser,
    form_parser,
    heading_parser,
    link_parser,
    navigation_parser,
    page_metadata,
    section_parser,
)
from app.services.website_context.crawler import CrawlError, crawl
from app.services.website_context.context_enricher import enrich
from app.services.website_context.json_builder import WebsiteContext, empty_context, merge_partial

logger = logging.getLogger(__name__)

_executor = ProcessPoolExecutor(max_workers=2)


def _extract_worker(url: str) -> WebsiteContext:
    """Top-level worker entrypoint for process pool context extraction."""
    return ContextService().extract(url)


def pool_context_loader(url: str) -> WebsiteContext:
    """
    Load website context via the process pool.

    Safe to call from FastAPI async handlers during planning refreshes.
    """
    future = _executor.submit(_extract_worker, url)
    return future.result(timeout=120)

ParserFn = Callable[[Page], Any]


class ContextService:
    """
    High-level service that crawls a URL and runs all context parsers.

    Each parser is isolated — a failure in one parser does not prevent the
    others from running. The final result always matches the Website Context
    schema with sensible empty defaults.
    """

    PARSERS: dict[str, ParserFn] = {
        "navigation": navigation_parser.parse,
        "headings": heading_parser.parse,
        "buttons": button_parser.parse,
        "forms": form_parser.parse,
        "sections": section_parser.parse,
        "footer": footer_parser.parse,
        "links": link_parser.parse,
        "components": components_parser.parse,
    }

    def extract(self, url: str) -> WebsiteContext:
        """
        Synchronously crawl *url* and return structured Website Context.

        Raises:
            CrawlError: If the page cannot be loaded.
        """
        logger.info("[ContextService] Extracting context for %s", url)

        with crawl(url) as session:
            context = empty_context()

            try:
                metadata = page_metadata.parse(session.page, current_url=session.final_url)
                merge_partial(context, "metadata", metadata)
            except Exception as exc:
                logger.error("[ContextService] metadata parser failed: %s", exc, exc_info=True)
                context["metadata"] = {"current_url": session.final_url}

            for key, parser in self.PARSERS.items():
                try:
                    result = parser(session.page)
                    merge_partial(context, key, result)
                    logger.debug("[ContextService] %s parser returned %s items", key, len(result))
                except Exception as exc:
                    logger.error(
                        "[ContextService] %s parser failed: %s",
                        key,
                        exc,
                        exc_info=True,
                    )

        logger.info(
            "[ContextService] Context extracted — nav=%d headings=%d buttons=%d forms=%d sections=%d footer=%d links=%d components=%d",
            len(context["navigation"]),
            len(context["headings"]),
            len(context["buttons"]),
            len(context["forms"]),
            len(context["sections"]),
            len(context["footer"]),
            len(context["links"]),
            len(context.get("components", [])),
        )
        enriched = enrich(context)
        logger.info("[ContextService] Context enriched with classification and priority scores")
        return enriched

    async def extract_async(self, url: str) -> WebsiteContext:
        """Async wrapper suitable for FastAPI — runs sync Playwright in a process pool."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(_executor, self.extract, url)


def extract_website_context(url: str) -> WebsiteContext:
    """Module-level convenience function."""
    return ContextService().extract(url)
