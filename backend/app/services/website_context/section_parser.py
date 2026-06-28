"""Extracts semantic page sections."""

from __future__ import annotations

import logging

from playwright.sync_api import Page

from app.services.website_context.json_builder import SectionInfo

logger = logging.getLogger(__name__)

_SECTIONS_SCRIPT = """
() => {
  const selectors = 'main, section, article, aside, header, footer, [role="main"], [role="region"], [role="banner"], [role="complementary"], [role="contentinfo"]';
  const seen = new Set();
  const sections = [];

  document.querySelectorAll(selectors).forEach((el) => {
    const tag = el.tagName.toLowerCase();
    const role = el.getAttribute('role') || '';
    const id = el.id || '';
    const className = typeof el.className === 'string' ? el.className.trim() : '';
    const headingEl = el.querySelector('h1, h2, h3, h4');
    const heading = headingEl
      ? (headingEl.innerText || headingEl.textContent || '').trim().replace(/\\s+/g, ' ')
      : '';
    const key = tag + '|' + role + '|' + id + '|' + className + '|' + heading;
    if (seen.has(key)) return;
    seen.add(key);
    sections.push({
      tag,
      role,
      id,
      class_name: className,
      heading,
      buttons_count: el.querySelectorAll('button, [role="button"], input[type="submit"]').length,
      links_count: el.querySelectorAll('a[href]').length,
      forms_count: el.querySelectorAll('form').length,
    });
  });

  return sections;
}
"""


def parse(page: Page) -> list[SectionInfo]:
    """Return semantic sections with counts and heading metadata."""
    logger.debug("[ContextEngine] Parsing semantic sections")
    raw_sections = page.evaluate(_SECTIONS_SCRIPT)
    sections: list[SectionInfo] = []

    for item in raw_sections:
        section: SectionInfo = {
            "tag": str(item.get("tag", "")),
            "buttons_count": int(item.get("buttons_count", 0)),
            "links_count": int(item.get("links_count", 0)),
            "forms_count": int(item.get("forms_count", 0)),
        }
        if item.get("role"):
            section["role"] = str(item["role"])
        if item.get("id"):
            section["id"] = str(item["id"])
        if item.get("class_name"):
            section["class_name"] = str(item["class_name"])
        if item.get("heading"):
            section["heading"] = str(item["heading"])
        sections.append(section)

    return sections
