from __future__ import annotations

import json
import re
import urllib.error

from app.services.ollama_client import generate_plan

ALLOWED_ACTIONS = frozenset({"open_page", "wait", "verify_visible", "verify_text", "capture"})
ALLOWED_TARGETS = frozenset(
    {"navigation", "header", "footer", "hero", "button", "form", "input", "image", "text", "page"}
)
MAX_STEPS = 6

LEGACY_SELECTOR_TO_TARGET = {
    "nav": "navigation",
    "navigation": "navigation",
    "header": "header",
    "footer": "footer",
    "hero": "hero",
    "button": "button",
    "form": "form",
    "input": "input",
    "img": "image",
    "image": "image",
    "body": "page",
    "page": "page",
    "main": "hero",
}


def _deterministic_plan(goal: str) -> list[dict]:
    goal_lower = goal.lower()
    plan: list[dict] = [{"action": "open_page"}]

    if any(word in goal_lower for word in ("navbar", "nav bar", "navigation", "menu")):
        plan.append({"action": "verify_visible", "target": "navigation"})
    elif any(word in goal_lower for word in ("homepage", "home page", "home")):
        plan.append({"action": "verify_visible", "target": "header"})
    elif "footer" in goal_lower:
        plan.append({"action": "verify_visible", "target": "footer"})
    elif any(word in goal_lower for word in ("hero", "banner")):
        plan.append({"action": "verify_visible", "target": "hero"})
    elif any(word in goal_lower for word in ("signup", "sign up", "login", "form")):
        plan.append({"action": "verify_visible", "target": "form"})
    elif "button" in goal_lower:
        plan.append({"action": "verify_visible", "target": "button"})
    elif any(word in goal_lower for word in ("image", "images", "photo")):
        plan.append({"action": "verify_visible", "target": "image"})
    else:
        plan.append({"action": "verify_visible", "target": "page"})

    plan.append({"action": "capture"})
    return plan[:MAX_STEPS]


def _normalize_target(step: dict) -> str | None:
    if "target" in step and step["target"]:
        return str(step["target"]).strip().lower()

    selector = step.get("selector")
    if selector:
        key = str(selector).strip().lower()
        return LEGACY_SELECTOR_TO_TARGET.get(key, key if key in ALLOWED_TARGETS else None)

    return None


def _parse_json_response(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    return json.loads(cleaned)


def _validate_plan(plan: list, goal: str) -> list:
    if not plan or not isinstance(plan, list):
        raise ValueError("Plan must be a non-empty list")

    goal_lower = goal.lower()
    validated: list[dict] = []
        if not isinstance(step, dict):
            raise ValueError("Each plan step must be an object")

        action = step.get("action")
        if action not in ALLOWED_ACTIONS:
            raise ValueError(f"Unsupported action: {action}")

        if action == "click" or (action not in ALLOWED_ACTIONS):
            raise ValueError(f"Unsupported action: {action}")

        entry: dict = {"action": action}

        if action == "verify_visible":
            target = _normalize_target(step)
            if not target or target not in ALLOWED_TARGETS:
                raise ValueError(f"Invalid target for verify_visible: {step}")
            entry["target"] = target

        if action == "verify_text":
            target = _normalize_target(step)
            text = step.get("text")
            if target and target in ALLOWED_TARGETS:
                entry["target"] = target
            if text:
                entry["text"] = str(text)
            if "target" not in entry and "text" not in entry:
                raise ValueError("verify_text requires target or text")

        if action == "wait":
            entry["ms"] = int(step.get("ms", 1000))

        validated.append(entry)

    return validated


def generate_test_plan(url: str, goal: str) -> dict:
    try:
        text = generate_plan(url, goal)
        data = _parse_json_response(text)
        plan = _validate_plan(data.get("plan", []), goal)
        return {"plan": plan, "source": "ollama"}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError, KeyError):
        return {"plan": _deterministic_plan(goal), "source": "fallback"}
    except Exception:
        return {"plan": _deterministic_plan(goal), "source": "fallback"}
