"""DOM snapshot capture for failure evidence."""

from __future__ import annotations

from typing import Any

from playwright.sync_api import Page


def capture_dom_snapshot(page: Page, *, max_nodes: int = 250) -> dict[str, Any]:
    """Capture a compact DOM snapshot suitable for RCA consumption."""
    try:
        snapshot = page.evaluate(
            """(maxNodes) => {
                const title = document.title || '';
                const url = window.location.href;
                const headings = Array.from(document.querySelectorAll('h1,h2,h3'))
                    .slice(0, 12)
                    .map((node) => ({
                        tag: node.tagName.toLowerCase(),
                        text: (node.textContent || '').trim().slice(0, 120),
                    }));
                const links = Array.from(document.querySelectorAll('a[href]'))
                    .slice(0, 20)
                    .map((node) => ({
                        text: (node.textContent || '').trim().slice(0, 80),
                        href: node.getAttribute('href'),
                    }));
                const buttons = Array.from(document.querySelectorAll('button,[role="button"],input[type="submit"]'))
                    .slice(0, 15)
                    .map((node) => ({
                        text: (node.textContent || node.getAttribute('value') || '').trim().slice(0, 80),
                        tag: node.tagName.toLowerCase(),
                    }));
                const forms = Array.from(document.querySelectorAll('form'))
                    .slice(0, 5)
                    .map((node) => ({
                        action: node.getAttribute('action'),
                        inputs: node.querySelectorAll('input,textarea,select').length,
                    }));
                const nodes = Array.from(document.querySelectorAll('body *'))
                    .slice(0, maxNodes)
                    .map((node) => ({
                        tag: node.tagName.toLowerCase(),
                        id: node.id || null,
                        classes: (node.className || '').toString().slice(0, 80) || null,
                    }));
                return {
                    title,
                    url,
                    headings,
                    links,
                    buttons,
                    forms,
                    node_count: nodes.length,
                    nodes,
                };
            }""",
            max_nodes,
        )
        return snapshot if isinstance(snapshot, dict) else {"url": page.url}
    except Exception as exc:
        return {"url": page.url, "capture_error": str(exc)}


def build_context_dom_snapshot(website_context: dict | None) -> dict[str, Any] | None:
    """Fallback DOM-like snapshot from extracted website context."""
    if not website_context:
        return None
    return {
        "source": "website_context",
        "metadata": website_context.get("metadata"),
        "navigation": website_context.get("navigation", [])[:20],
        "buttons": website_context.get("buttons", [])[:20],
        "forms": website_context.get("forms", [])[:10],
        "sections": website_context.get("sections", [])[:15],
        "headings": website_context.get("headings", [])[:20],
    }
