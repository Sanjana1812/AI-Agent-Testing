"""Extracts navigation links from semantic navigation regions."""

from __future__ import annotations

import logging

from playwright.sync_api import Page

from app.services.website_context.json_builder import NavigationLink

logger = logging.getLogger(__name__)

_NAVIGATION_SCRIPT = """
() => {
  const regions = Array.from(
    document.querySelectorAll('nav, [role="navigation"], header nav, .nav, .navbar, .navigation')
  );
  const seen = new Set();
  const links = [];

  const addLink = (anchor) => {
    const href = anchor.getAttribute('href') || '';
    const text = (anchor.innerText || anchor.textContent || '').trim().replace(/\\s+/g, ' ');
    if (!href || href.startsWith('javascript:')) return;
    const key = href + '|' + text;
    if (seen.has(key)) return;
    seen.add(key);
    links.push({ text, href });
  };

  for (const region of regions) {
    region.querySelectorAll('a[href]').forEach(addLink);
  }

  if (links.length === 0) {
    document.querySelectorAll('header a[href]').forEach(addLink);
  }

  return links;
}
"""


def parse(page: Page) -> list[NavigationLink]:
    """Return navigation link text and href values from nav regions."""
    logger.debug("[ContextEngine] Parsing navigation links")
    raw_links = page.evaluate(_NAVIGATION_SCRIPT)
    return [
        NavigationLink(
            text=str(item.get("text", "")),
            href=str(item.get("href", "")),
        )
        for item in raw_links
        if item.get("href")
    ]
