"""Extracts all anchor links and classifies internal vs external."""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from playwright.sync_api import Page

from app.services.website_context.json_builder import AnchorLink

logger = logging.getLogger(__name__)

_LINKS_SCRIPT = """
(pageOrigin) => {
  const escape = (value) => value.replace(/([!"#$%&'()*+,./:;<=>?@[\\\\\\]^`{|}~])/g, '\\\\$1');
  const buildSelector = (el) => {
    const href = el.getAttribute('href') || el.href || '';
    if (href) return `a[href="${href.replace(/"/g, '\\\\"')}"]`;
    if (el.id) return `#${escape(el.id)}`;
    return 'a';
  };
  const isVisible = (el) => {
    const style = window.getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
  };
  const detectSection = (el) => {
    if (el.closest('footer, [role="contentinfo"], .footer, #footer')) return 'footer';
    if (el.closest('aside, [role="complementary"]')) return 'sidebar';
    if (el.closest('header, nav, [role="navigation"], [role="banner"]')) return 'header';
    return 'body';
  };

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
    let external = false;
    try {
      const url = new URL(href, window.location.href);
      internal = url.origin === pageOrigin || href.startsWith('/') || href.startsWith('#');
      external = !internal;
    } catch {
      internal = href.startsWith('/') || href.startsWith('#');
      external = !internal;
    }

    links.push({
      text,
      href,
      internal,
      external,
      selector: buildSelector(anchor),
      visible: isVisible(anchor),
      section: detectSection(anchor),
    });
  });

  return links;
}
"""


def parse(page: Page) -> list[AnchorLink]:
    """Return all anchor links with semantic metadata."""
    logger.debug("[ContextEngine] Parsing anchor links")
    origin = urlparse(page.url).netloc
    page_origin = f"{urlparse(page.url).scheme}://{origin}" if origin else page.url
    raw_links = page.evaluate(_LINKS_SCRIPT, page_origin)

    return [
        AnchorLink(
            text=str(item.get("text", "")),
            href=str(item.get("href", "")),
            internal=bool(item.get("internal", False)),
            selector=str(item.get("selector", "")),
            visible=bool(item.get("visible", False)),
            external=bool(item.get("external", False)),
            section=str(item.get("section", "body")),
        )
        for item in raw_links
        if item.get("href")
    ]
