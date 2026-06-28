"""Extracts footer links from the page."""

from __future__ import annotations

import logging

from playwright.sync_api import Page

from app.services.website_context.json_builder import FooterLink

logger = logging.getLogger(__name__)

_FOOTER_SCRIPT = """
() => {
  const regions = Array.from(
    document.querySelectorAll('footer, [role="contentinfo"], .footer, #footer')
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

  if (regions.length > 0) {
    regions.forEach((region) => region.querySelectorAll('a[href]').forEach(addLink));
  } else {
    const bodyLinks = Array.from(document.querySelectorAll('a[href]'));
    const cutoff = Math.max(0, bodyLinks.length - 20);
    bodyLinks.slice(cutoff).forEach(addLink);
  }

  return links;
}
"""


def parse(page: Page) -> list[FooterLink]:
    """Return footer link text and href values."""
    logger.debug("[ContextEngine] Parsing footer links")
    raw_links = page.evaluate(_FOOTER_SCRIPT)
    return [
        FooterLink(
            text=str(item.get("text", "")),
            href=str(item.get("href", "")),
        )
        for item in raw_links
        if item.get("href")
    ]
