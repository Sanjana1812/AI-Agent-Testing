"""Extracts all anchor links and classifies internal vs external."""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from playwright.sync_api import Page

from app.services.website_context.json_builder import AnchorLink

logger = logging.getLogger(__name__)

_LINKS_SCRIPT = """
(pageOrigin) => {
  const seen = new Set();
  const links = [];

  document.querySelectorAll('a[href]').forEach((anchor) => {
    const href = anchor.href || anchor.getAttribute('href') || '';
    const text = (anchor.innerText || anchor.textContent || '').trim().replace(/\\s+/g, ' ');
    if (!href || href.startsWith('javascript:')) return;
    const key = href + '|' + text;
    if (seen.has(key)) return;
    seen.add(key);

    let internal = false;
    try {
      const url = new URL(href, window.location.href);
      internal = url.origin === pageOrigin || href.startsWith('/') || href.startsWith('#');
    } catch {
      internal = href.startsWith('/') || href.startsWith('#');
    }

    links.push({ text, href, internal });
  });

  return links;
}
"""


def parse(page: Page) -> list[AnchorLink]:
    """Return all anchor links with internal/external classification."""
    logger.debug("[ContextEngine] Parsing anchor links")
    origin = urlparse(page.url).netloc
    page_origin = f"{urlparse(page.url).scheme}://{origin}" if origin else page.url
    raw_links = page.evaluate(_LINKS_SCRIPT, page_origin)

    return [
        AnchorLink(
            text=str(item.get("text", "")),
            href=str(item.get("href", "")),
            internal=bool(item.get("internal", False)),
        )
        for item in raw_links
        if item.get("href")
    ]
