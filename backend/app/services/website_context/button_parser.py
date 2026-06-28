"""Extracts interactive buttons from the page."""

from __future__ import annotations

import logging

from playwright.sync_api import Page

from app.services.website_context.json_builder import ButtonInfo

logger = logging.getLogger(__name__)

_BUTTONS_SCRIPT = """
() => {
  const escape = (value) => value.replace(/([!"#$%&'()*+,./:;<=>?@[\\\\\\]^`{|}~])/g, '\\\\$1');
  const buildSelector = (el) => {
    if (el.id) return `#${escape(el.id)}`;
    const testId = el.getAttribute('data-testid');
    if (testId) return `[data-testid="${testId}"]`;
    const name = el.getAttribute('name');
    if (name) return `${el.tagName.toLowerCase()}[name="${name}"]`;
    const aria = el.getAttribute('aria-label');
    if (aria) return `${el.tagName.toLowerCase()}[aria-label="${aria}"]`;
    const text = (el.innerText || el.value || '').trim().slice(0, 40);
    if (text) return `${el.tagName.toLowerCase()}:has-text("${text.replace(/"/g, '\\\\"')}")`;
    return el.tagName.toLowerCase();
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
    if (el.closest('main, section, [role="main"]')) return 'main';
    return 'body';
  };

  const selectors = 'button, [role="button"], input[type="submit"], input[type="button"], input[type="reset"]';
  const seen = new Set();
  const buttons = [];

  document.querySelectorAll(selectors).forEach((el) => {
    const text = (el.innerText || el.value || el.getAttribute('aria-label') || '').trim().replace(/\\s+/g, ' ');
    const selector = buildSelector(el);
    const key = selector + '|' + text;
    if (seen.has(key)) return;
    seen.add(key);
    const disabled = !!el.disabled || el.getAttribute('aria-disabled') === 'true';
    buttons.push({
      text,
      selector,
      disabled,
      visible: isVisible(el),
      enabled: !disabled,
      role: el.getAttribute('role') || el.tagName.toLowerCase(),
      section: detectSection(el),
      class_name: typeof el.className === 'string' ? el.className.trim() : '',
      tag: el.tagName.toLowerCase(),
    });
  });

  return buttons;
}
"""


def parse(page: Page) -> list[ButtonInfo]:
    """Return buttons with selector, visibility, section, and role metadata."""
    logger.debug("[ContextEngine] Parsing buttons")
    raw_buttons = page.evaluate(_BUTTONS_SCRIPT)
    return [
        ButtonInfo(
            text=str(item.get("text", "")),
            selector=str(item.get("selector", "")),
            disabled=bool(item.get("disabled", False)),
            visible=bool(item.get("visible", False)),
            enabled=bool(item.get("enabled", True)),
            role=str(item.get("role", "")),
            section=str(item.get("section", "body")),
            class_name=str(item.get("class_name", "")),
            tag=str(item.get("tag", "button")),
        )
        for item in raw_buttons
        if item.get("selector")
    ]
