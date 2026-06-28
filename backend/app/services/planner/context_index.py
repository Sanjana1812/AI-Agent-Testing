"""Index of discoverable page elements from enriched Website Context."""

from __future__ import annotations

from app.services.website_context.json_builder import WebsiteContext


class ContextIndex:
    """Queryable view over enriched Website Context for planning and validation."""

    LOGO_CLASSIFICATIONS = frozenset({"Logo"})

    def __init__(self, context: WebsiteContext) -> None:
        self.context = context

    def summary(self) -> dict:
        """Compact summary for failure metadata and logging."""
        return {
            "navigation_count": len(self.context.get("navigation", [])),
            "heading_count": len(self.context.get("headings", [])),
            "button_count": len(self.usable_buttons()),
            "form_count": len(self.context.get("forms", [])),
            "section_count": len(self.context.get("sections", [])),
            "footer_link_count": len(self.context.get("footer", [])),
            "link_count": len(self.context.get("links", [])),
            "page_title": self.context.get("metadata", {}).get("title", ""),
            "top_cta": self.highest_priority_cta().get("text") if self.highest_priority_cta() else None,
        }

    @staticmethod
    def _by_priority(items: list[dict]) -> list[dict]:
        return sorted(items, key=lambda item: int(item.get("priority", 0)), reverse=True)

    def usable_buttons(self) -> list[dict]:
        return [
            btn
            for btn in self.context.get("buttons", [])
            if btn.get("visible") and btn.get("enabled", not btn.get("disabled"))
        ]

    def visible_buttons(self) -> list[dict]:
        return self.usable_buttons()

    def ranked_buttons(self, *, classification: str | None = None, button_type: str | None = None) -> list[dict]:
        buttons = self.usable_buttons()
        if classification:
            buttons = [btn for btn in buttons if btn.get("classification") == classification]
        if button_type:
            buttons = [btn for btn in buttons if btn.get("type") == button_type]
        return self._by_priority(buttons)

    def ranked_nav_links(self, *, exclude_logo: bool = True, section: str | None = None) -> list[dict]:
        links = list(self.context.get("navigation", []))
        if section:
            links = [link for link in links if link.get("section") == section]
        if exclude_logo:
            links = [link for link in links if link.get("classification") not in self.LOGO_CLASSIFICATIONS]
        links = [link for link in links if link.get("visible", True)]
        return self._by_priority(links)

    def ranked_footer_links(self, *, exclude_logo: bool = True) -> list[dict]:
        links = list(self.context.get("footer", []))
        if exclude_logo:
            links = [link for link in links if link.get("classification") not in self.LOGO_CLASSIFICATIONS]
        links = [link for link in links if link.get("visible", True)]
        return self._by_priority(links)

    def ranked_links(self, *, exclude_logo: bool = True, internal_only: bool = False) -> list[dict]:
        links = list(self.context.get("links", []))
        if internal_only:
            links = [link for link in links if link.get("internal")]
        if exclude_logo:
            links = [link for link in links if link.get("classification") not in self.LOGO_CLASSIFICATIONS]
        links = [link for link in links if link.get("visible", True)]
        return self._by_priority(links)

    def ranked_sections(self, *, semantic_type: str | None = None) -> list[dict]:
        sections = list(self.context.get("sections", []))
        if semantic_type:
            sections = [section for section in sections if section.get("semantic_type") == semantic_type]
        return self._by_priority(sections)

    def highest_priority_cta(self) -> dict | None:
        ctas = self.ranked_buttons(classification="CTA")
        if ctas:
            return ctas[0]
        primary = self.ranked_buttons(button_type="cta")
        if primary:
            return primary[0]
        ranked = self.ranked_buttons()
        non_logo = [btn for btn in ranked if btn.get("classification") not in self.LOGO_CLASSIFICATIONS]
        return non_logo[0] if non_logo else None

    def highest_priority_nav_link(self, *, exclude_logo: bool = True) -> dict | None:
        ranked = self.ranked_nav_links(exclude_logo=exclude_logo)
        return ranked[0] if ranked else None

    def highest_priority_footer_link(self, *, exclude_logo: bool = True) -> dict | None:
        ranked = self.ranked_footer_links(exclude_logo=exclude_logo)
        if ranked:
            return ranked[0]
        ranked_links = self.ranked_links(exclude_logo=exclude_logo)
        return ranked_links[0] if ranked_links else None

    def highest_priority_section(self, *, semantic_type: str | None = None) -> dict | None:
        ranked = self.ranked_sections(semantic_type=semantic_type)
        return ranked[0] if ranked else None

    def hero_section(self) -> dict | None:
        hero = self.highest_priority_section(semantic_type="hero")
        if hero:
            return hero
        return self.highest_priority_section()

    def hero_heading(self) -> dict | None:
        headings = self._by_priority(list(self.context.get("headings", [])))
        for heading in headings:
            if heading.get("level") == 1:
                return heading
        return headings[0] if headings else None

    def has_navigation(self) -> bool:
        return bool(self.ranked_nav_links(exclude_logo=False))

    def has_header(self) -> bool:
        if self.has_navigation():
            return True
        return any(section.get("tag") == "header" for section in self.context.get("sections", []))

    def has_footer(self) -> bool:
        if self.context.get("footer"):
            return True
        return any(section.get("semantic_type") == "footer" or section.get("tag") == "footer" for section in self.context.get("sections", []))

    def has_hero(self) -> bool:
        if self.hero_heading():
            return True
        return bool(self.ranked_sections(semantic_type="hero"))

    def has_sections(self) -> bool:
        return bool(self.context.get("sections"))

    def has_buttons(self) -> bool:
        return bool(self.usable_buttons())

    def has_forms(self) -> bool:
        return bool(self.context.get("forms"))

    def has_links(self) -> bool:
        return bool(self.context.get("links"))

    def has_email_field(self) -> bool:
        for form in self.context.get("forms", []):
            for field in form.get("fields", []):
                if field.get("type") == "email" or "email" in field.get("name", "").lower():
                    return True
        return False

    def has_password_field(self) -> bool:
        for form in self.context.get("forms", []):
            for field in form.get("fields", []):
                if field.get("type") == "password":
                    return True
        return False

    def has_input_field(self) -> bool:
        for form in self.context.get("forms", []):
            if form.get("fields"):
                return True
        return False

    def has_submit_control(self) -> bool:
        if self.ranked_buttons(classification="CTA"):
            return True
        if self.ranked_buttons(button_type="submit"):
            return True
        return self.has_forms()

    def has_image(self) -> bool:
        return any(link.get("href", "").endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")) for link in self.context.get("links", []))

    def supports_target(self, target: str) -> bool:
        checks = {
            "navigation": self.has_navigation,
            "menu": self.has_navigation,
            "header": self.has_header,
            "footer": self.has_footer,
            "hero": self.has_hero,
            "section": self.has_sections,
            "button": self.has_buttons,
            "submit": self.has_submit_control,
            "form": self.has_forms,
            "input": self.has_input_field,
            "email": self.has_email_field,
            "password": self.has_password_field,
            "link": self.has_links,
            "image": self.has_image,
        }
        checker = checks.get(target)
        return checker() if checker else False

    def supports_text(self, text: str) -> bool:
        needle = text.strip().lower()
        if not needle:
            return False
        for heading in self.context.get("headings", []):
            if needle in heading.get("text", "").lower():
                return True
        for btn in self.usable_buttons():
            if needle in btn.get("text", "").lower():
                return True
        for link in self.context.get("links", []):
            if needle in link.get("text", "").lower():
                return True
        return False

    def first_heading(self, level: int = 1) -> dict | None:
        return self.hero_heading() if level == 1 else None

    def first_visible_button(self) -> dict | None:
        return self.highest_priority_cta()

    def first_nav_link(self) -> dict | None:
        return self.highest_priority_nav_link()

    def first_footer_link(self) -> dict | None:
        return self.highest_priority_footer_link()

    def first_section(self) -> dict | None:
        return self.hero_section()

    def planner_snapshot(self) -> dict:
        """Trimmed enriched context payload for Ollama prompts."""
        return {
            "metadata": self.context.get("metadata", {}),
            "navigation": self.ranked_nav_links(exclude_logo=False)[:12],
            "headings": self._by_priority(list(self.context.get("headings", [])))[:12],
            "buttons": self.ranked_buttons()[:12],
            "forms": self._by_priority(list(self.context.get("forms", [])))[:5],
            "sections": self.ranked_sections()[:10],
            "footer": self.ranked_footer_links(exclude_logo=False)[:12],
            "links": self.ranked_links(exclude_logo=False)[:15],
        }
