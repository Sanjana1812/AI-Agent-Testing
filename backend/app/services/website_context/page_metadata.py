"""Extracts page-level metadata from a loaded Playwright page."""

from __future__ import annotations

import logging

from playwright.sync_api import Page

from app.services.website_context.json_builder import PageMetadata

logger = logging.getLogger(__name__)

_METADATA_SCRIPT = """
() => {
  const description = document.querySelector('meta[name="description"]');
  const viewport = document.querySelector('meta[name="viewport"]');
  const canonical = document.querySelector('link[rel="canonical"]');
  const lang = document.documentElement.getAttribute('lang') || '';

  return {
    title: document.title || '',
    meta_description: description ? (description.getAttribute('content') || '') : '',
    language: lang,
    viewport: viewport ? (viewport.getAttribute('content') || '') : '',
    canonical_url: canonical ? (canonical.getAttribute('href') || '') : '',
    current_url: window.location.href,
  };
}
"""


def parse(page: Page, current_url: str | None = None) -> PageMetadata:
    """
    Extract title, meta tags, language, viewport, canonical URL, and current URL.

    Args:
        page: Loaded Playwright page.
        current_url: Optional override for the resolved URL after redirects.
    """
    logger.debug("[ContextEngine] Parsing page metadata")

    data = page.evaluate(_METADATA_SCRIPT)
    metadata: PageMetadata = {
        "title": str(data.get("title", "")),
        "meta_description": str(data.get("meta_description", "")),
        "language": str(data.get("language", "")),
        "viewport": str(data.get("viewport", "")),
        "canonical_url": str(data.get("canonical_url", "")),
        "current_url": current_url or str(data.get("current_url", page.url)),
    }
    return metadata
