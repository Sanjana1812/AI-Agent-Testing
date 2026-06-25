from __future__ import annotations

import json
import urllib.request

from app.config import settings

OLLAMA_GENERATE_PATH = "/api/generate"


def _build_prompt(url: str, goal: str) -> str:
    return f"""You are an AI browser testing planner.

Return ONLY JSON.
Never return explanations.
Never invent CSS selectors.
Use semantic targets instead.

URL: {url}
Goal: {goal}

Allowed targets:
navigation
header
footer
hero
button
form
input
image
text
page

Allowed actions:
open_page
wait
verify_visible
verify_text
capture

Rules:
- max 6 steps
- deterministic
- avoid click unless explicitly requested
- if uncertain use verify_visible

Example 1:
Goal: verify navbar
Output:
{{"plan":[{{"action":"open_page"}},{{"action":"verify_visible","target":"navigation"}},{{"action":"capture"}}]}}

Example 2:
Goal: check homepage
Output:
{{"plan":[{{"action":"open_page"}},{{"action":"verify_visible","target":"header"}},{{"action":"capture"}}]}}
"""


def generate_plan(url: str, goal: str) -> str:
    endpoint = f"{settings.ollama_base_url.rstrip('/')}{OLLAMA_GENERATE_PATH}"
    payload = json.dumps(
        {
            "model": settings.model_name,
            "prompt": _build_prompt(url, goal),
            "stream": False,
            "format": "json",
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=settings.ollama_timeout_seconds) as response:
        data = json.loads(response.read().decode("utf-8"))

    text = data.get("response", "")
    if not text:
        raise ValueError("Ollama returned an empty response")

    return text
