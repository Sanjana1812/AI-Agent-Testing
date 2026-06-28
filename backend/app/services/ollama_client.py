from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

OLLAMA_GENERATE_PATH = "/api/generate"

INTENT_EXAMPLES: dict[str, str] = {
    "navigation": """Goal: check navigation
{"plan":[
  {"action":"open_page"},
  {"action":"wait","ms":800},
  {"action":"verify_visible","target":"navigation"},
  {"action":"click","target":"link"},
  {"action":"wait","ms":800},
  {"action":"verify_visible","target":"header"},
  {"action":"capture"}
]}""",
    "flow": """Goal: check the flow
{"plan":[
  {"action":"open_page"},
  {"action":"verify_visible","target":"navigation"},
  {"action":"verify_visible","target":"hero"},
  {"action":"scroll","target":"section"},
  {"action":"verify_visible","target":"section"},
  {"action":"verify_visible","target":"footer"},
  {"action":"capture"}
]}""",
    "login": """Goal: check login
{"plan":[
  {"action":"open_page"},
  {"action":"verify_visible","target":"form"},
  {"action":"fill","target":"email","value":"test@example.com"},
  {"action":"fill","target":"password","value":"password123"},
  {"action":"click","target":"submit"},
  {"action":"wait","ms":1000},
  {"action":"verify_visible","target":"section"},
  {"action":"capture"}
]}""",
    "signup": """Goal: check signup
{"plan":[
  {"action":"open_page"},
  {"action":"verify_visible","target":"form"},
  {"action":"verify_form","target":"form"},
  {"action":"fill","target":"email","value":"user@example.com"},
  {"action":"fill","target":"password","value":"Password123!"},
  {"action":"click","target":"submit"},
  {"action":"wait","ms":1000},
  {"action":"capture"}
]}""",
    "contact": """Goal: check contact form
{"plan":[
  {"action":"open_page"},
  {"action":"verify_visible","target":"form"},
  {"action":"verify_form","target":"form"},
  {"action":"fill","target":"input","value":"QA Tester"},
  {"action":"fill","target":"email","value":"qa@example.com"},
  {"action":"click","target":"submit"},
  {"action":"wait","ms":1000},
  {"action":"capture"}
]}""",
    "form": """Goal: check form validation
{"plan":[
  {"action":"open_page"},
  {"action":"verify_visible","target":"form"},
  {"action":"verify_form","target":"form"},
  {"action":"fill","target":"input","value":"test value"},
  {"action":"click","target":"submit"},
  {"action":"wait","ms":800},
  {"action":"capture"}
]}""",
    "search": """Goal: check search
{"plan":[
  {"action":"open_page"},
  {"action":"verify_visible","target":"input"},
  {"action":"fill","target":"input","value":"test query"},
  {"action":"click","target":"button"},
  {"action":"wait","ms":1000},
  {"action":"verify_visible","target":"section"},
  {"action":"capture"}
]}""",
    "general": """Goal: explore homepage
{"plan":[
  {"action":"open_page"},
  {"action":"verify_visible","target":"navigation"},
  {"action":"verify_visible","target":"hero"},
  {"action":"scroll","target":"section"},
  {"action":"verify_visible","target":"footer"},
  {"action":"capture"}
]}""",
}


@dataclass
class PlanGenerationResult:
    success: bool
    text: str = ""
    error: str = ""


def _build_prompt(url: str, goal: str, intent: str) -> str:
    example = INTENT_EXAMPLES.get(intent, INTENT_EXAMPLES["general"])

    return f"""You are a Senior QA Automation Engineer.

Convert the natural language testing goal into a meaningful Playwright test plan.

URL: {url}
Testing goal: {goal}
Detected intent: {intent}

Return ONLY JSON. No explanations. No markdown.

Allowed semantic targets (use these ONLY):
navigation, menu, header, footer, hero, section, button, submit, form, input, email, password, link, image

Allowed actions:
open_page, wait, click, scroll, fill, verify_visible, verify_form, capture

FORBIDDEN — never use these unless absolutely no alternative:
- verify_text
- target "page", "body", "text", "content", "main"
- generic steps with no specific target

Planner rules:
- Generate 4-8 meaningful actions
- Every plan MUST end with capture
- Prefer section-specific verification: navigation, hero, section, footer, form, button
- Prefer interactions: click link, click button, scroll section, fill form fields
- Match the detected intent: {intent}
- Think like a QA engineer naming real test steps (Verify Navbar, Verify Hero, Scroll, Verify Footer)

Intent guidance:
- navigation: verify nav, click nav links, confirm header updates
- flow: open site, verify navbar, verify hero, scroll, verify sections, verify footer
- login: verify form, fill credentials, submit, verify post-login content
- signup: verify form, validate fields, fill and submit
- contact: verify contact form, fill fields, submit
- form: verify and validate form structure, fill and submit
- search: find input, enter query, submit, verify results section
- checkout: verify cart/button, proceed, fill checkout form, submit
- dashboard/profile: verify nav, navigate, verify account/dashboard sections
- responsive/performance: verify key sections after load, scroll through page
- accessibility: verify nav, header, interactive elements, forms

Follow this example for intent "{intent}":
{example}
"""


async def generate_plan(url: str, goal: str, intent: str = "general") -> PlanGenerationResult:
    endpoint = f"{settings.ollama_base_url.rstrip('/')}{OLLAMA_GENERATE_PATH}"
    payload = {
        "model": settings.model_name,
        "prompt": _build_prompt(url, goal, intent),
        "stream": False,
        "format": "json",
    }

    try:
        async with httpx.AsyncClient(timeout=settings.ollama_timeout_seconds) as client:
            response = await client.post(endpoint, json=payload)
            response.raise_for_status()
            data = response.json()

        text = data.get("response", "")
        if not text:
            return PlanGenerationResult(success=False, error="Ollama returned an empty response")

        return PlanGenerationResult(success=True, text=text)
    except httpx.TimeoutException as exc:
        logger.error("[Planner] Ollama request timed out: %s", exc)
        return PlanGenerationResult(success=False, error=f"Timeout: {exc}")
    except httpx.HTTPStatusError as exc:
        logger.error("[Planner] Ollama HTTP error: %s", exc)
        return PlanGenerationResult(success=False, error=f"HTTP error: {exc.response.status_code}")
    except Exception as exc:
        logger.error("[Planner] Ollama request failed: %s", exc)
        return PlanGenerationResult(success=False, error=str(exc))
