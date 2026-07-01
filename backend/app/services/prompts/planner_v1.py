"""Planning prompt v1 — test plan generation."""

from __future__ import annotations

import json

VERSION = "1.0.0"
PURPOSE = "Generate a grounded Playwright test plan from website context and a testing goal."

TEMPLATE = """You are a Senior QA Automation Engineer.

Convert the natural language testing goal into a Playwright test plan using ONLY elements discovered on the page.

URL: {url}
Testing goal: {goal}
Detected intent: {intent}

Website Context (discovered elements with priority — use ONLY these):
{context_json}

Priority rules:
- Prefer highest priority elements (priority field, higher = more important)
- NEVER click Logo elements (classification Logo or priority <= 5)
- Prefer CTA buttons (classification CTA, type cta) over generic buttons
- Prefer Primary Navigation links over logo/home links
- Include selector from context when available
- Include label with human-readable element text (e.g. Click "About", Verify "GET STARTED" button)

Return ONLY JSON. No explanations. No markdown.

Allowed actions:
open_page, wait, click, scroll, fill, verify_visible, verify_form, verify_text, capture

Allowed semantic targets (only if present in Website Context):
navigation, menu, header, footer, hero, section, button, submit, form, input, email, password, link, image

Optional fields per step:
- selector: use exact selector from buttons[].selector or build a[href="..."] from navigation/footer/links
- label: human-readable element name from discovered text

Rules:
- Generate 4-8 meaningful actions grounded in Website Context
- NEVER reference elements absent from Website Context
- Every plan MUST end with capture
- Match intent: {intent}

Example output shape:
{{"plan":[
  {{"action":"open_page","label":"Open Website"}},
  {{"action":"verify_visible","target":"hero","label":"Verify Hero Section"}},
  {{"action":"click","target":"link","selector":"a[href='...']","label":"Click \\"About\\""}},
  {{"action":"capture","label":"Capture Screenshot"}}
]}}
"""


def render(*, url: str, goal: str, intent: str, website_context: dict) -> str:
    context_json = json.dumps(website_context, indent=2)
    return TEMPLATE.format(
        url=url,
        goal=goal,
        intent=intent,
        context_json=context_json,
    )
