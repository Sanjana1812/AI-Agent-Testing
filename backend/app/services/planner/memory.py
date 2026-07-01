"""Lightweight planner memory to avoid repetitive interactions."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.planner.context_index import ContextIndex


def _normalize_key(value: str | None) -> str:
    return (value or "").strip().lower()


@dataclass
class PlannerMemory:
    visited_pages: set[str] = field(default_factory=set)
    visited_buttons: set[str] = field(default_factory=set)
    visited_links: set[str] = field(default_factory=set)
    verified_sections: set[str] = field(default_factory=set)
    clicked_ctas: set[str] = field(default_factory=set)
    visited_selectors: set[str] = field(default_factory=set)
    verified_selectors: set[str] = field(default_factory=set)
    allow_repetition: bool = False

    @staticmethod
    def selector_key(selector: str | None) -> str:
        return _normalize_key(selector)

    @staticmethod
    def link_key(link: dict | None = None, *, selector: str | None = None, label: str | None = None, href: str | None = None) -> str:
        if link:
            selector = link.get("selector")
            label = link.get("text")
            href = link.get("href")
        return _normalize_key(selector or href or label)

    @staticmethod
    def button_key(button: dict | None = None, *, selector: str | None = None, label: str | None = None) -> str:
        if button:
            selector = button.get("selector")
            label = button.get("text")
        return _normalize_key(selector or label)

    @staticmethod
    def section_key(target: str | None, label: str | None = None, selector: str | None = None) -> str:
        if selector:
            return _normalize_key(selector)
        return _normalize_key(f"{target}:{label}")

    def can_use_selector(self, selector: str | None, *, action: str) -> bool:
        if self.allow_repetition or not selector:
            return bool(selector)
        key = self.selector_key(selector)
        if action == "click":
            return key not in self.visited_selectors
        if action in {"verify_visible", "verify_form", "scroll"}:
            return key not in self.verified_selectors
        return key not in self.visited_selectors and key not in self.verified_selectors

    def can_click_link(self, *, selector: str | None = None, label: str | None = None, href: str | None = None, classification: str = "") -> bool:
        if self.allow_repetition:
            return True
        if classification in ContextIndex.LOGO_CLASSIFICATIONS:
            return False
        if selector and not self.can_use_selector(selector, action="click"):
            return False
        key = self.link_key(selector=selector, label=label, href=href)
        return bool(key) and key not in self.visited_links

    def can_click_cta(self, *, selector: str | None = None, label: str | None = None, classification: str = "") -> bool:
        if self.allow_repetition:
            return True
        if classification in ContextIndex.LOGO_CLASSIFICATIONS:
            return False
        if selector and not self.can_use_selector(selector, action="click"):
            return False
        key = self.button_key(selector=selector, label=label)
        return bool(key) and key not in self.clicked_ctas and key not in self.visited_buttons

    def can_verify_section(self, target: str | None, label: str | None = None, selector: str | None = None) -> bool:
        if self.allow_repetition:
            return True
        if selector and not self.can_use_selector(selector, action="verify_visible"):
            return False
        key = self.section_key(target, label, selector)
        return key not in self.verified_sections

    def record_step(self, step: dict) -> None:
        action = step.get("action")
        target = step.get("target")
        label = step.get("label")
        selector = step.get("selector")
        selector_key = self.selector_key(selector)

        if selector_key:
            if action == "click":
                self.visited_selectors.add(selector_key)
            elif action in {"verify_visible", "verify_form", "scroll"}:
                self.verified_selectors.add(selector_key)

        if action == "click":
            if target in {"link", "navigation"}:
                self.visited_links.add(self.link_key(selector=selector, label=label))
            elif target in {"button", "submit"}:
                key = self.button_key(selector=selector, label=label)
                self.visited_buttons.add(key)
                self.clicked_ctas.add(key)
        elif action in {"verify_visible", "verify_form", "scroll"}:
            self.verified_sections.add(self.section_key(target, label, selector))

    def clone(self) -> PlannerMemory:
        return PlannerMemory(
            visited_pages=set(self.visited_pages),
            visited_buttons=set(self.visited_buttons),
            visited_links=set(self.visited_links),
            verified_sections=set(self.verified_sections),
            clicked_ctas=set(self.clicked_ctas),
            visited_selectors=set(self.visited_selectors),
            verified_selectors=set(self.verified_selectors),
            allow_repetition=self.allow_repetition,
        )
