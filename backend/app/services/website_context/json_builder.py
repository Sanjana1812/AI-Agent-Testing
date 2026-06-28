"""Builds the final Website Context JSON from individual parser outputs."""

from __future__ import annotations

from typing import Any, TypedDict


class PageMetadata(TypedDict, total=False):
    title: str
    meta_description: str
    language: str
    viewport: str
    canonical_url: str
    current_url: str


class NavigationLink(TypedDict, total=False):
    text: str
    href: str
    selector: str
    visible: bool
    external: bool
    section: str
    priority: int
    classification: str


class Heading(TypedDict, total=False):
    level: int
    text: str
    priority: int
    classification: str


class ButtonInfo(TypedDict, total=False):
    text: str
    selector: str
    disabled: bool
    visible: bool
    enabled: bool
    type: str
    section: str
    priority: int
    role: str
    classification: str
    class_name: str
    tag: str


class FormField(TypedDict, total=False):
    type: str
    name: str
    placeholder: str
    required: bool


class FormInfo(TypedDict, total=False):
    action: str
    method: str
    fields: list[FormField]
    required: int
    visible: bool
    section: str
    selector: str
    priority: int
    classification: str


class SectionInfo(TypedDict, total=False):
    tag: str
    role: str
    id: str
    class_name: str
    heading: str
    semantic_type: str
    buttons_count: int
    links_count: int
    forms_count: int
    priority: int


class FooterLink(TypedDict, total=False):
    text: str
    href: str
    selector: str
    visible: bool
    external: bool
    section: str
    priority: int
    classification: str


class AnchorLink(TypedDict, total=False):
    text: str
    href: str
    internal: bool
    selector: str
    visible: bool
    external: bool
    section: str
    priority: int
    classification: str


class WebsiteContext(TypedDict):
    metadata: PageMetadata
    navigation: list[NavigationLink]
    headings: list[Heading]
    buttons: list[ButtonInfo]
    forms: list[FormInfo]
    sections: list[SectionInfo]
    footer: list[FooterLink]
    links: list[AnchorLink]


def empty_context() -> WebsiteContext:
    """Return a Website Context object with all collections initialized."""
    return {
        "metadata": {},
        "navigation": [],
        "headings": [],
        "buttons": [],
        "forms": [],
        "sections": [],
        "footer": [],
        "links": [],
    }


def build(
    *,
    metadata: PageMetadata | None = None,
    navigation: list[NavigationLink] | None = None,
    headings: list[Heading] | None = None,
    buttons: list[ButtonInfo] | None = None,
    forms: list[FormInfo] | None = None,
    sections: list[SectionInfo] | None = None,
    footer: list[FooterLink] | None = None,
    links: list[AnchorLink] | None = None,
) -> WebsiteContext:
    """Combine parser outputs into the canonical Website Context structure."""
    context = empty_context()
    if metadata:
        context["metadata"] = metadata
    if navigation is not None:
        context["navigation"] = navigation
    if headings is not None:
        context["headings"] = headings
    if buttons is not None:
        context["buttons"] = buttons
    if forms is not None:
        context["forms"] = forms
    if sections is not None:
        context["sections"] = sections
    if footer is not None:
        context["footer"] = footer
    if links is not None:
        context["links"] = links
    return context


def merge_partial(context: WebsiteContext, key: str, value: Any) -> None:
    """Merge a single parser result into an existing context object."""
    if key == "metadata" and isinstance(value, dict):
        context["metadata"] = value
    elif key in context and isinstance(value, list):
        context[key] = value  # type: ignore[literal-required]
