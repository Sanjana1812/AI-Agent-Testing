"""Resolve deterministic selectors from enriched Website Context elements."""

from __future__ import annotations

import logging
import re
from typing import Any

from app.services.planner.context_index import ContextIndex
from app.services.planner.selector_ranker import (
    CONFIDENCE_BY_TYPE,
    MIN_CONFIDENCE_THRESHOLD,
    RankedSelector,
    SelectorType,
    meets_confidence_threshold,
    rank_selectors,
)
from app.services.planner.selector_validator import is_generic_selector, pick_valid_selector, validate_selector

logger = logging.getLogger(__name__)

GENERIC_LITERALS = frozenset({"button", "a", "div", "section", "input", "form", "footer"})

NON_ELEMENT_ACTIONS = frozenset({"open_page", "wait", "capture"})
INTERACTIVE_ACTIONS = frozenset({"click", "fill", "verify_visible", "verify_form", "scroll"})


def _escape_attr(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _escape_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def build_candidates(element: dict[str, Any]) -> list[RankedSelector]:
    """Build ranked selector candidates from a context element record."""
    candidates: list[RankedSelector] = []
    tag = str(element.get("tag") or element.get("element_tag") or "").lower()

    data_testid = element.get("data-testid") or element.get("data_testid")
    if data_testid:
        candidates.append(
            RankedSelector(
                selector=f'[data-testid="{_escape_attr(str(data_testid))}"]',
                selector_type=SelectorType.DATA_TESTID,
                confidence=CONFIDENCE_BY_TYPE[SelectorType.DATA_TESTID],
            )
        )

    element_id = element.get("id")
    if element_id:
        candidates.append(
            RankedSelector(
                selector=f"#{str(element_id).lstrip('#')}",
                selector_type=SelectorType.ID,
                confidence=CONFIDENCE_BY_TYPE[SelectorType.ID],
            )
        )

    href = element.get("href")
    if href:
        candidates.append(
            RankedSelector(
                selector=f'a[href="{_escape_attr(str(href))}"]',
                selector_type=SelectorType.HREF,
                confidence=CONFIDENCE_BY_TYPE[SelectorType.HREF],
            )
        )

    aria_label = element.get("aria-label") or element.get("aria_label")
    if aria_label:
        prefix = tag if tag else "*"
        candidates.append(
            RankedSelector(
                selector=f'{prefix}[aria-label="{_escape_attr(str(aria_label))}"]',
                selector_type=SelectorType.ARIA_LABEL,
                confidence=CONFIDENCE_BY_TYPE[SelectorType.ARIA_LABEL],
            )
        )

    text = element.get("text")
    if text and str(text).strip():
        text_value = str(text).strip()
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            prefix = tag
        elif tag in {"a", "button", "input"}:
            prefix = tag
        else:
            prefix = "button"
        candidates.append(
            RankedSelector(
                selector=f'{prefix}:has-text("{_escape_text(text_value)}")',
                selector_type=SelectorType.TEXT,
                confidence=CONFIDENCE_BY_TYPE[SelectorType.TEXT],
            )
        )

    name = element.get("name")
    if name:
        input_tag = tag if tag else "input"
        candidates.append(
            RankedSelector(
                selector=f'{input_tag}[name="{_escape_attr(str(name))}"]',
                selector_type=SelectorType.NAME,
                confidence=CONFIDENCE_BY_TYPE[SelectorType.NAME],
            )
        )

    placeholder = element.get("placeholder")
    if placeholder:
        candidates.append(
            RankedSelector(
                selector=f'input[placeholder="{_escape_attr(str(placeholder))}"]',
                selector_type=SelectorType.PLACEHOLDER,
                confidence=CONFIDENCE_BY_TYPE[SelectorType.PLACEHOLDER],
            )
        )

    css_selector = element.get("selector")
    if css_selector and not is_generic_selector(str(css_selector)):
        candidates.append(
            RankedSelector(
                selector=str(css_selector),
                selector_type=SelectorType.CSS,
                confidence=CONFIDENCE_BY_TYPE[SelectorType.CSS],
            )
        )

    role = element.get("role")
    if role:
        prefix = tag if tag else "*"
        candidates.append(
            RankedSelector(
                selector=f'{prefix}[role="{_escape_attr(str(role))}"]',
                selector_type=SelectorType.ROLE,
                confidence=CONFIDENCE_BY_TYPE[SelectorType.ROLE],
            )
        )

    if tag and tag not in GENERIC_LITERALS:
        candidates.append(
            RankedSelector(
                selector=tag,
                selector_type=SelectorType.TAG,
                confidence=CONFIDENCE_BY_TYPE[SelectorType.TAG],
            )
        )

    return rank_selectors(candidates)


def resolve_element(
    element: dict[str, Any],
    *,
    used_selectors: set[str] | None = None,
) -> RankedSelector | None:
    """Resolve the strongest valid selector for a context element."""
    valid_candidates: list[RankedSelector] = []
    for candidate in build_candidates(element):
        valid, reason = validate_selector(candidate.selector, used_selectors=used_selectors)
        if valid and meets_confidence_threshold(candidate):
            valid_candidates.append(candidate)
        else:
            logger.debug("[SelectorResolver] Skipped candidate %s — %s", candidate.selector, reason)

    if valid_candidates:
        return valid_candidates[0]
    return None


def resolve_element_alternatives(
    element: dict[str, Any],
    *,
    used_selectors: set[str] | None = None,
    limit: int = 5,
) -> list[str]:
    alternatives: list[str] = []
    for candidate in build_candidates(element):
        valid, _ = validate_selector(candidate.selector, used_selectors=used_selectors)
        if valid and candidate.selector not in alternatives:
            alternatives.append(candidate.selector)
        if len(alternatives) >= limit:
            break
    return alternatives


def _label_text(label: str | None) -> str | None:
    if not label:
        return None
    match = re.search(r'"([^"]+)"', label)
    if match:
        return match.group(1)
    return label.strip() or None


def _match_text(needle: str | None, haystack: str | None) -> bool:
    if not needle or not haystack:
        return False
    return needle.strip().lower() in haystack.strip().lower() or haystack.strip().lower() in needle.strip().lower()


def _find_button(index: ContextIndex, *, label: str | None = None, selector_hint: str | None = None) -> dict | None:
    if selector_hint:
        for button in index.ranked_buttons():
            if button.get("selector") == selector_hint:
                return button
    label_text = _label_text(label)
    for button in index.ranked_buttons():
        if label_text and _match_text(label_text, button.get("text")):
            return button
    return index.highest_priority_cta()


def _find_link(
    index: ContextIndex,
    *,
    label: str | None = None,
    selector_hint: str | None = None,
    href_hint: str | None = None,
) -> dict | None:
    pools = [
        index.ranked_nav_links(exclude_logo=True),
        index.ranked_footer_links(exclude_logo=True),
        index.ranked_links(exclude_logo=True),
    ]
    if selector_hint:
        for pool in pools:
            for link in pool:
                if link.get("selector") == selector_hint:
                    return link
    if href_hint:
        for pool in pools:
            for link in pool:
                if link.get("href") == href_hint:
                    return link
    label_text = _label_text(label)
    for pool in pools:
        for link in pool:
            if label_text and _match_text(label_text, link.get("text")):
                return link
    return index.highest_priority_nav_link() or index.highest_priority_footer_link()


def _section_record(section: dict) -> dict[str, Any]:
    record: dict[str, Any] = {
        "tag": section.get("tag"),
        "role": section.get("role"),
        "id": section.get("id"),
        "class_name": section.get("class_name"),
        "text": section.get("heading"),
    }
    if section.get("id"):
        record["selector"] = f"#{section['id']}"
    elif section.get("class_name"):
        tag = section.get("tag") or "section"
        first_class = str(section["class_name"]).split()[0]
        record["selector"] = f"{tag}.{first_class}"
    elif section.get("tag"):
        record["selector"] = str(section["tag"])
    return record


def _find_section(index: ContextIndex, *, semantic_type: str | None = None, label: str | None = None) -> dict | None:
    sections = index.ranked_sections(semantic_type=semantic_type) or index.ranked_sections()
    label_text = _label_text(label)
    for section in sections:
        if label_text and _match_text(label_text, section.get("heading")):
            return _section_record(section)
    if sections:
        return _section_record(sections[0])
    return None


def _find_form(index: ContextIndex) -> dict | None:
    forms = index._by_priority(list(index.context.get("forms", [])))
    if not forms:
        return None
    form = forms[0]
    record = dict(form)
    if form.get("selector") and not is_generic_selector(form.get("selector")):
        record["selector"] = form.get("selector")
    elif form.get("id"):
        record["id"] = form.get("id")
    return record


def _find_form_field(index: ContextIndex, field_kind: str) -> dict | None:
    for form in index.context.get("forms", []):
        for field in form.get("fields", []):
            field_type = str(field.get("type", "")).lower()
            field_name = str(field.get("name", "")).lower()
            if field_kind == "email" and (field_type == "email" or "email" in field_name):
                return {"tag": "input", "name": field.get("name"), "placeholder": field.get("placeholder"), "type": "email"}
            if field_kind == "password" and field_type == "password":
                return {"tag": "input", "name": field.get("name"), "placeholder": field.get("placeholder"), "type": "password"}
            if field_kind == "input" and field_type in {"text", "search", ""}:
                return {"tag": "input", "name": field.get("name"), "placeholder": field.get("placeholder"), "type": field_type or "text"}
    return None


def _find_navigation(index: ContextIndex) -> dict | None:
    nav_links = index.ranked_nav_links(exclude_logo=False)
    if nav_links:
        link = nav_links[0]
        selector = link.get("selector")
        if selector and not is_generic_selector(selector):
            parent_match = re.match(r"^(nav[^ ]*)", selector)
            if parent_match:
                return {"selector": parent_match.group(1), "tag": "nav"}
        return {"selector": "nav", "tag": "nav", "text": "Navigation"}
    for section in index.ranked_sections():
        if section.get("tag") == "header" or section.get("role") == "banner":
            return _section_record(section)
    return None


def _find_footer(index: ContextIndex) -> dict | None:
    for section in index.ranked_sections():
        if section.get("tag") == "footer" or section.get("semantic_type") == "footer":
            record = _section_record(section)
            if record.get("id") or record.get("class_name"):
                return record
    footer_links = index.ranked_footer_links(exclude_logo=True)
    if footer_links:
        return dict(footer_links[0], tag="a")
    return None


def _find_hero(index: ContextIndex) -> dict | None:
    heading = index.hero_heading()
    if heading:
        record: dict[str, Any] = {
            "text": heading.get("text"),
            "tag": f"h{heading.get('level', 1)}",
        }
        if heading.get("selector"):
            record["selector"] = heading["selector"]
        return record

    hero = index.hero_section()
    if hero:
        record = _section_record(hero)
        if hero.get("heading"):
            record["text"] = hero.get("heading")
            record["tag"] = "h1"
        return record
    return None


def _source_element_for_step(step: dict, index: ContextIndex) -> dict | None:
    action = step.get("action")
    target = step.get("target")
    label = step.get("label")
    selector_hint = step.get("selector")

    if action == "click":
        if target in {"button", "submit"}:
            return _find_button(index, label=label, selector_hint=selector_hint)
        return _find_link(index, label=label, selector_hint=selector_hint)

    if action in {"verify_visible", "scroll"}:
        if target == "hero":
            return _find_hero(index)
        if target == "navigation":
            return _find_navigation(index)
        if target == "footer":
            return _find_footer(index)
        if target == "section":
            return _find_section(index, label=label)
        if target == "form":
            return _find_form(index)
        if target == "button":
            return _find_button(index, label=label, selector_hint=selector_hint)
        if target == "link":
            return _find_link(index, label=label, selector_hint=selector_hint)
        if target == "input":
            return _find_form_field(index, "input")

    if action == "verify_form" or target == "form":
        return _find_form(index)

    if action == "fill":
        if target == "email":
            return _find_form_field(index, "email")
        if target == "password":
            return _find_form_field(index, "password")
        return _find_form_field(index, "input")

    return None


def resolve_step(
    step: dict,
    index: ContextIndex,
    *,
    used_selectors: set[str],
) -> dict:
    """Attach resolved selector metadata to a plan step."""
    action = step.get("action")
    if action in NON_ELEMENT_ACTIONS or action == "verify_text":
        return step

    if action not in INTERACTIVE_ACTIONS:
        return step

    resolved_step = dict(step)
    existing = resolved_step.get("selector")
    if existing and not is_generic_selector(str(existing)):
        valid, _ = validate_selector(str(existing), used_selectors=used_selectors)
        if valid:
            resolved_step.setdefault("selector_strategy", "context")
            resolved_step.setdefault("selector_type", "css")
            resolved_step.setdefault("selector_confidence", 65)
            used_selectors.add(str(existing).strip().lower())
            return resolved_step

    element = _source_element_for_step(step, index)
    if not element:
        return resolved_step

    ranked = resolve_element(element, used_selectors=used_selectors)
    if not ranked:
        fallback_candidates = [str(existing)] if existing else []
        if element.get("selector"):
            fallback_candidates.append(str(element["selector"]))
        if element.get("href"):
            fallback_candidates.append(f'a[href="{_escape_attr(str(element["href"]))}"]')
        picked = pick_valid_selector(fallback_candidates, used_selectors=used_selectors)
        if picked:
            ranked = RankedSelector(selector=picked, selector_type=SelectorType.CSS, confidence=65)
        else:
            logger.warning("[SelectorResolver] Skipping step — no selector above confidence threshold")
            return resolved_step

    if ranked.confidence < MIN_CONFIDENCE_THRESHOLD:
        logger.warning(
            "[SelectorResolver] Skipping unreliable selector (confidence=%s): %s",
            ranked.confidence,
            ranked.selector,
        )
        return resolved_step

    resolved_step["selector"] = ranked.selector
    resolved_step["selector_strategy"] = ranked.strategy
    resolved_step["selector_type"] = ranked.selector_type.value
    resolved_step["selector_confidence"] = ranked.confidence
    alternatives = resolve_element_alternatives(element, used_selectors=used_selectors | {ranked.selector.strip().lower()})
    if alternatives:
        resolved_step["selector_alternatives"] = alternatives
    used_selectors.add(ranked.selector.strip().lower())
    return resolved_step


def resolve_plan_selectors(plan: list[dict], index: ContextIndex) -> list[dict]:
    """Resolve selectors for every interactive step in a plan."""
    used_selectors: set[str] = set()
    resolved: list[dict] = []
    for step in plan:
        resolved.append(resolve_step(step, index, used_selectors=used_selectors))
    return resolved
