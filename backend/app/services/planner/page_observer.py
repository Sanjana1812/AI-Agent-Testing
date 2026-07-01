"""Detect when page context should be refreshed after planner actions."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.planner.dom_fingerprint import (
    fingerprint_from_context,
    hero_heading_text,
    significantly_changed,
)
from app.services.website_context.json_builder import WebsiteContext

IGNORED_ACTIONS = frozenset({"scroll", "wait", "capture", "verify_visible", "verify_text", "verify_form"})
NAVIGATION_ACTIONS = frozenset({"open_page", "click", "fill"})


@dataclass
class PageSnapshot:
    url: str
    title: str
    hero_heading: str | None
    fingerprint: dict


class PageObserver:
    """Compare page snapshots to decide whether context refresh is required."""

    def __init__(self) -> None:
        self.previous: PageSnapshot | None = None

    @staticmethod
    def from_context(context: WebsiteContext, url: str) -> PageSnapshot:
        metadata = context.get("metadata", {})
        return PageSnapshot(
            url=url,
            title=str(metadata.get("title", "")).strip(),
            hero_heading=hero_heading_text(context),
            fingerprint=fingerprint_from_context(context),
        )

    def observe(self, context: WebsiteContext, url: str) -> PageSnapshot:
        snapshot = self.from_context(context, url)
        self.previous = snapshot
        return snapshot

    def should_refresh(
        self,
        action: dict,
        *,
        before: PageSnapshot,
        after: PageSnapshot,
    ) -> bool:
        action_type = action.get("action", "")

        if action_type in IGNORED_ACTIONS and action_type != "fill":
            return False

        if before.url != after.url:
            return True
        if before.title and after.title and before.title != after.title:
            return True
        if before.hero_heading and after.hero_heading and before.hero_heading != after.hero_heading:
            return True
        if significantly_changed(before.fingerprint, after.fingerprint):
            return True

        if action_type == "click" and action.get("target") in {"link", "button", "submit"}:
            return before.url != after.url or significantly_changed(before.fingerprint, after.fingerprint)

        if action_type == "open_page":
            return True

        if action_type == "fill" and action.get("target") in {"email", "password", "input"}:
            target = action.get("target")
            if target == "password" or action.get("value") and "submit" in str(action.get("label", "")).lower():
                return True

        return False
