"""Extracts forms and their fields from the page."""

from __future__ import annotations

import logging

from playwright.sync_api import Page

from app.services.website_context.json_builder import FormField, FormInfo

logger = logging.getLogger(__name__)

_FORMS_SCRIPT = """
() => {
  const escape = (value) => value.replace(/([!"#$%&'()*+,./:;<=>?@[\\\\\\]^`{|}~])/g, '\\\\$1');
  const isVisible = (el) => {
    const style = window.getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
  };
  const detectSection = (el) => {
    if (el.closest('footer, [role="contentinfo"], .footer, #footer')) return 'footer';
    if (el.closest('aside, [role="complementary"]')) return 'sidebar';
    if (el.closest('header, nav, [role="navigation"]')) return 'header';
    return 'body';
  };
  const buildSelector = (el) => {
    if (el.id) return `#${escape(el.id)}`;
    return 'form';
  };

  const forms = [];
  document.querySelectorAll('form').forEach((form) => {
    const fields = [];
    const seen = new Set();
    form.querySelectorAll('input, textarea, select').forEach((field) => {
      const type = (field.getAttribute('type') || field.tagName.toLowerCase()).toLowerCase();
      if (type === 'hidden') return;
      const name = field.getAttribute('name') || field.getAttribute('id') || '';
      const placeholder = field.getAttribute('placeholder') || '';
      const required = field.required || field.getAttribute('aria-required') === 'true';
      const key = type + '|' + name + '|' + placeholder;
      if (seen.has(key)) return;
      seen.add(key);
      fields.push({ type, name, placeholder, required });
    });

    forms.push({
      action: form.getAttribute('action') || '',
      method: (form.getAttribute('method') || 'get').toLowerCase(),
      fields,
      visible: isVisible(form),
      section: detectSection(form),
      selector: buildSelector(form),
    });
  });

  return forms;
}
"""


def parse(page: Page) -> list[FormInfo]:
    """Return forms with action, method, field metadata, and visibility."""
    logger.debug("[ContextEngine] Parsing forms")
    raw_forms = page.evaluate(_FORMS_SCRIPT)
    forms: list[FormInfo] = []

    for item in raw_forms:
        fields = [
            FormField(
                type=str(field.get("type", "")),
                name=str(field.get("name", "")),
                placeholder=str(field.get("placeholder", "")),
                required=bool(field.get("required", False)),
            )
            for field in item.get("fields", [])
        ]
        forms.append(
            FormInfo(
                action=str(item.get("action", "")),
                method=str(item.get("method", "get")),
                fields=fields,
                visible=bool(item.get("visible", True)),
                section=str(item.get("section", "body")),
                selector=str(item.get("selector", "form")),
            )
        )

    return forms
