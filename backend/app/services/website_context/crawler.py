"""Playwright-based page crawler for the Website Context Engine."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Generator

from playwright.sync_api import Browser, Page, sync_playwright
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from app.services.playwright_bootstrap import launch_chromium

logger = logging.getLogger(__name__)

NAVIGATION_TIMEOUT_MS = 30_000
NETWORK_IDLE_TIMEOUT_MS = 15_000


class CrawlError(Exception):
    """Raised when the crawler cannot load the target page."""


@dataclass(frozen=True)
class CrawlSession:
    """Active browser session after a successful crawl."""

    page: Page
    browser: Browser
    final_url: str
    http_status: int


@contextmanager
def crawl(url: str) -> Generator[CrawlSession, None, None]:
    """
    Launch Chromium, navigate to *url*, and wait for the DOM to settle.

    Waits for ``networkidle`` after initial navigation. If network idle times
    out (common on sites with persistent connections), falls back to ``load``.
    """
    logger.info("[ContextEngine] Crawling %s", url)

    with sync_playwright() as playwright:
        try:
            browser = launch_chromium(playwright)
        except PlaywrightError as exc:
            raise CrawlError(f"Failed to launch Chromium: {exc}") from exc

        page = browser.new_page()
        http_status = 0
        final_url = url

        try:
            try:
                response = page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=NAVIGATION_TIMEOUT_MS,
                )
                http_status = response.status if response else 0
                final_url = page.url

                page.wait_for_load_state("load", timeout=NAVIGATION_TIMEOUT_MS)
                try:
                    page.wait_for_load_state("networkidle", timeout=NETWORK_IDLE_TIMEOUT_MS)
                except PlaywrightTimeoutError:
                    logger.warning(
                        "[ContextEngine] networkidle timed out for %s — continuing with loaded DOM",
                        url,
                    )
            except PlaywrightTimeoutError as exc:
                raise CrawlError(f"Timed out loading {url}: {exc}") from exc
            except PlaywrightError as exc:
                raise CrawlError(f"Failed to load {url}: {exc}") from exc

            logger.info(
                "[ContextEngine] Page loaded (status=%s, url=%s)",
                http_status,
                final_url,
            )
            yield CrawlSession(
                page=page,
                browser=browser,
                final_url=final_url,
                http_status=http_status,
            )
        finally:
            browser.close()
            logger.debug("[ContextEngine] Browser closed for %s", url)
