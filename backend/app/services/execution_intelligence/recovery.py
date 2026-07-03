"""Runtime recovery helpers for execution intelligence (modal dismissal only)."""

from __future__ import annotations

import logging

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)

DEFAULT_DISMISS_SELECTORS = [
    'button[id*="accept"]',
    'button[id*="cookie"]',
    'button[class*="accept"]',
    'button[class*="cookie"]',
    '[aria-label*="Accept"]',
    '[aria-label*="Close"]',
    'button[class*="close"]',
    'button[class*="dismiss"]',
    '[data-dismiss]',
    '.modal-close',
    '.popup-close',
    'button:has-text("Accept")',
    'button:has-text("OK")',
    'button:has-text("Got it")',
    'button:has-text("Close")',
    'button:has-text("No thanks")',
]


def dismiss_modal_overlay(page: Page, selectors: list[str] | None = None) -> bool:
    """Try dismiss selectors in order. Returns True if one click succeeded."""
    candidates = selectors or DEFAULT_DISMISS_SELECTORS
    for selector in candidates:
        try:
            locator = page.locator(selector).first
            if locator.count() == 0:
                continue
            locator.click(timeout=1500)
            page.wait_for_timeout(300)
            logger.info("[ExecutionIntelligence] Dismissed overlay via %s", selector)
            return True
        except (PlaywrightTimeoutError, PlaywrightError):
            continue
    return False
