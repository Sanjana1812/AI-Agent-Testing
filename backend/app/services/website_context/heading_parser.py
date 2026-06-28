"""Extracts heading hierarchy (H1–H3) from the page."""

from __future__ import annotations

import logging

from playwright.sync_api import Page

from app.services.website_context.json_builder import Heading

logger = logging.getLogger(__name__)

_HEADINGS_SCRIPT = """
() => {
  const headings = [];
  const seen = new Set();

  document.querySelectorAll('h1, h2, h3').forEach((el) => {
    const text = (el.innerText || el.textContent || '').trim().replace(/\\s+/g, ' ');
    if (!text) return;
    const level = parseInt(el.tagName.substring(1), 10);
    const key = level + '|' + text;
    if (seen.has(key)) return;
    seen.add(key);
    headings.push({ level, text });
  });

  return headings;
}
"""


def parse(page: Page) -> list[Heading]:
    """Return visible H1, H2, and H3 headings with their level and text."""
    logger.debug("[ContextEngine] Parsing headings")
    raw_headings = page.evaluate(_HEADINGS_SCRIPT)
    return [
        Heading(
            level=int(item.get("level", 0)),
            text=str(item.get("text", "")),
        )
        for item in raw_headings
        if item.get("text")
    ]
