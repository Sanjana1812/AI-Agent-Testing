"""Smart wait strategy for dynamic production websites."""

from __future__ import annotations

import logging

from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)

DOM_READY_TIMEOUT_MS = 10_000
NETWORK_IDLE_TIMEOUT_MS = 4_000
LAYOUT_STABLE_TIMEOUT_MS = 2_000
CONTENT_RENDER_TIMEOUT_MS = 3_000
HYDRATION_POLL_MS = 250
HYDRATION_MAX_POLLS = 12

INTERACTIVE_ACTIONS = frozenset({"click", "fill", "scroll", "verify_visible", "verify_form", "verify_text"})
POST_NAVIGATION_ACTIONS = frozenset({"click", "open_page"})


def wait_for_dom_ready(page: Page, *, timeout_ms: int = DOM_READY_TIMEOUT_MS) -> None:
    try:
        page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
    except PlaywrightTimeoutError:
        logger.debug("[WaitStrategy] DOMContentLoaded timeout — continuing")


def wait_for_network_idle(page: Page, *, timeout_ms: int = NETWORK_IDLE_TIMEOUT_MS) -> None:
    try:
        page.wait_for_load_state("networkidle", timeout=timeout_ms)
    except PlaywrightTimeoutError:
        logger.debug("[WaitStrategy] networkidle timeout — continuing with partial load")


def wait_for_layout_stabilization(page: Page, *, timeout_ms: int = LAYOUT_STABLE_TIMEOUT_MS) -> None:
    """Wait until document height stops changing (lazy load / SPA render)."""
    script = """
    async (timeoutMs) => {
      const start = Date.now();
      let lastHeight = document.body?.scrollHeight || 0;
      while (Date.now() - start < timeoutMs) {
        await new Promise((r) => setTimeout(r, 150));
        const height = document.body?.scrollHeight || 0;
        if (height === lastHeight) return true;
        lastHeight = height;
      }
      return false;
    }
    """
    try:
        page.evaluate(script, timeout_ms)
    except Exception:
        page.wait_for_timeout(min(timeout_ms, 800))


def wait_for_hydration(page: Page) -> None:
    """Detect React/Next/Vue/Angular hydration completion heuristically."""
    script = """
    () => {
      const root = document.querySelector('#__next, #root, #app, [ng-version], [data-reactroot]');
      if (!root) return true;
      const busy = root.getAttribute('aria-busy') === 'true';
      const skeletons = document.querySelectorAll('[class*="skeleton"], [class*="placeholder"], [data-loading="true"]');
      return !busy && skeletons.length === 0;
    }
    """
    for _ in range(HYDRATION_MAX_POLLS):
        try:
            ready = page.evaluate(script)
            if ready:
                return
        except Exception:
            return
        page.wait_for_timeout(HYDRATION_POLL_MS)


def wait_for_major_content(page: Page, *, timeout_ms: int = CONTENT_RENDER_TIMEOUT_MS) -> None:
    """Wait for primary content landmarks before verification."""
    selectors = (
        "main, [role='main'], h1, [role='banner'], .hero, .main-content, "
        "#content, .content, [data-testid*='hero'], [data-testid*='content']"
    )
    try:
        page.locator(selectors).first.wait_for(state="attached", timeout=timeout_ms)
    except PlaywrightTimeoutError:
        logger.debug("[WaitStrategy] Major content landmark not found — continuing")


def stabilize_page(page: Page, action: dict | None = None) -> None:
    """Full stabilization pipeline before interactions and verifications."""
    action_type = (action or {}).get("action", "")
    wait_for_dom_ready(page)
    if action_type in POST_NAVIGATION_ACTIONS or action_type == "open_page":
        wait_for_network_idle(page)
    wait_for_hydration(page)
    wait_for_layout_stabilization(page)
    if action_type in INTERACTIVE_ACTIONS or action_type == "open_page":
        wait_for_major_content(page)


def wait_before_action(page: Page, action: dict) -> None:
    """Pre-action wait hook used by the execution engine."""
    action_type = action.get("action", "")
    if action_type == "wait":
        return
    if action_type == "capture":
        wait_for_layout_stabilization(page, timeout_ms=800)
        return
    if action_type in INTERACTIVE_ACTIONS or action_type == "open_page":
        stabilize_page(page, action)
