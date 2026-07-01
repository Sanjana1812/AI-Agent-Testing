"""Extracts navigation links from semantic navigation regions."""

from __future__ import annotations

import logging

from playwright.sync_api import Page

from app.services.website_context.json_builder import NavigationLink

logger = logging.getLogger(__name__)

_NAVIGATION_SCRIPT = """
() => {
  const escape = (value) => value.replace(/([!"#$%&'()*+,./:;<=>?@[\\\\\\]^`{|}~])/g, '\\\\$1');
  const buildSelector = (el) => {
    if (el.id) return `#${escape(el.id)}`;
    const testId = el.getAttribute('data-testid');
    if (testId) return `[data-testid="${testId}"]`;
    const href = el.getAttribute('href');
    if (href) return `a[href="${href.replace(/"/g, '\\\\"')}"]`;
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
    return 'header';
  };
  const isExternal = (href) => {
    try { return new URL(href, window.location.href).origin !== window.location.origin; }
    catch { return href.startsWith('http'); }
  };

  const regions = Array.from(
    document.querySelectorAll([
      'nav',
      '[role="navigation"]',
      'header nav',
      '.nav',
      '.navbar',
      '.navigation',
      '#nav-main',
      '.header',
      '.topbar',
      '.menu',
      '.main-menu',
      '.sidebar nav',
      '.breadcrumb',
      '.mega-menu',
      '.megamenu',
      '[class*="Navigation"]',
      '[class*="navigation"]',
      '[class*="NavBar"]',
      '[class*="navbar"]',
      '[data-testid*="nav"]',
      '[data-testid*="menu"]',
      'header .menu',
      '.sticky-nav',
      '.sticky-navigation',
      '[class*="TopBar"]',
      '[class*="topbar"]',
    ].join(', '))
  );
  const seen = new Set();
  const links = [];

  const addLink = (anchor) => {
    const href = anchor.getAttribute('href') || anchor.href || '';
    const text = (anchor.innerText || anchor.textContent || '').trim().replace(/\\s+/g, ' ');
    if (!href || href.startsWith('javascript:')) return;
    const key = href + '|' + text;
    if (seen.has(key)) return;
    seen.add(key);
    links.push({
      text,
      href,
      selector: buildSelector(anchor),
      visible: isVisible(anchor),
      external: isExternal(href),
      section: detectSection(anchor),
    });
  };

  for (const region of regions) {
    region.querySelectorAll('a[href]').forEach(addLink);
  }
  if (links.length === 0) {
    document.querySelectorAll('header a[href], .header a[href], .topbar a[href], [role="navigation"] a[href]').forEach(addLink);
  }
  if (links.length === 0) {
    document.querySelectorAll('a[href]').forEach((anchor) => {
      const text = (anchor.innerText || anchor.textContent || '').trim();
      if (text.length >= 2 && text.length <= 40) addLink(anchor);
    });
  }
  return links;
}
"""


def parse(page: Page) -> list[NavigationLink]:
    """Return navigation links with semantic metadata from nav regions."""
    logger.debug("[ContextEngine] Parsing navigation links")
    raw_links = page.evaluate(_NAVIGATION_SCRIPT)
    return [
        NavigationLink(
            text=str(item.get("text", "")),
            href=str(item.get("href", "")),
            selector=str(item.get("selector", "")),
            visible=bool(item.get("visible", False)),
            external=bool(item.get("external", False)),
            section=str(item.get("section", "header")),
        )
        for item in raw_links
        if item.get("href")
    ]
