"""Human-readable labels for planner steps."""

from __future__ import annotations

TARGET_DISPLAY_NAMES = {
    "navigation": "Navigation Bar",
    "menu": "Menu",
    "header": "Header",
    "footer": "Footer",
    "hero": "Hero Section",
    "section": "Main Content",
    "button": "Button",
    "submit": "Submit Button",
    "form": "Form",
    "input": "Input Field",
    "email": "Email Field",
    "password": "Password Field",
    "link": "Link",
    "image": "Image",
}


def verify_navigation_label() -> str:
    return "Verify Navigation Bar"


def verify_hero_label(heading: str | None = None) -> str:
    if heading:
        return f'Verify Hero Section "{heading}"'
    return "Verify Hero Section"


def verify_section_label(heading: str | None = None, semantic_type: str | None = None) -> str:
    if semantic_type and semantic_type != "general":
        return f"Verify {semantic_type.title()} Section"
    if heading:
        return f'Verify Section "{heading}"'
    return "Verify Main Content"


def verify_footer_label() -> str:
    return "Verify Footer"


def verify_form_label(classification: str | None = None) -> str:
    if classification in {"Login", "Signup", "Contact"}:
        return f"Verify {classification} Form"
    return "Verify Contact Form"


def verify_button_label(text: str) -> str:
    return f'Verify "{text}" button'


def click_link_label(text: str) -> str:
    return f'Click "{text}"'


def click_button_label(text: str) -> str:
    return f'Click "{text}"'


def fill_field_label(field_name: str) -> str:
    return f'Fill "{field_name}"'


def open_page_label() -> str:
    return "Open Page"


def wait_label(ms: int = 1000) -> str:
    return f"Wait {ms}ms"


def scroll_label(target: str | None = None, text: str | None = None) -> str:
    if text:
        return f'Scroll to "{text}"'
    if target:
        return f"Scroll to {TARGET_DISPLAY_NAMES.get(target, target.replace('_', ' ').title())}"
    return "Scroll Page"


def verify_visible_label(
    target: str | None = None,
    *,
    heading: str | None = None,
    semantic_type: str | None = None,
    text: str | None = None,
) -> str:
    if target == "navigation":
        return verify_navigation_label()
    if target == "hero":
        return verify_hero_label(heading or text)
    if target == "footer":
        return verify_footer_label()
    if target == "form":
        return verify_form_label(semantic_type)
    if target == "section":
        return verify_section_label(heading, semantic_type)
    if target in {"button", "submit"} and text:
        return verify_button_label(text)
    if target and target in TARGET_DISPLAY_NAMES:
        return f"Verify {TARGET_DISPLAY_NAMES[target]}"
    if text:
        return f'Verify "{text}"'
    return "Verify Element Visible"


def verify_text_label(text: str) -> str:
    return f'Verify Text "{text}"'


def capture_label() -> str:
    return "Capture Screenshot"


def build_step_label(step: dict) -> str | None:
    """Build a human-readable label for any supported plan step."""
    if step.get("label"):
        return str(step["label"])

    action = step.get("action")
    target = step.get("target")
    text = step.get("text")

    if action == "open_page":
        return open_page_label()
    if action == "wait":
        return wait_label(int(step.get("ms", 1000)))
    if action == "capture":
        return capture_label()
    if action == "verify_text" and text:
        return verify_text_label(str(text))
    if action == "click":
        if text:
            return click_button_label(str(text))
        if target == "link":
            return click_link_label("Link")
        if target in {"button", "submit"}:
            return click_button_label(TARGET_DISPLAY_NAMES.get(target, "Button"))
    if action == "fill":
        field = text or TARGET_DISPLAY_NAMES.get(str(target), str(target or "Field"))
        return fill_field_label(field)
    if action == "scroll":
        return scroll_label(target, text)
    if action == "verify_form":
        return verify_form_label(step.get("classification"))
    if action == "verify_visible":
        return verify_visible_label(
            target,
            heading=step.get("heading"),
            semantic_type=step.get("semantic_type"),
            text=text,
        )

    return None
