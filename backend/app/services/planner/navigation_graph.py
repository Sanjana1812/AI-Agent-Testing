"""Navigation graph built from Website Context."""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlparse

from app.services.planner.context_index import ContextIndex


@dataclass(frozen=True)
class GraphNode:
    node_id: str
    label: str
    href: str | None
    selector: str | None
    source: str
    classification: str
    priority: int
    is_internal: bool = True


@dataclass
class NavigationGraph:
    """Structured view of page sections and navigable destinations."""

    root: GraphNode
    navigation_nodes: list[GraphNode] = field(default_factory=list)
    footer_nodes: list[GraphNode] = field(default_factory=list)
    section_nodes: list[GraphNode] = field(default_factory=list)
    cta_node: GraphNode | None = None
    nodes_by_id: dict[str, GraphNode] = field(default_factory=dict)

    @classmethod
    def from_context(cls, index: ContextIndex) -> NavigationGraph:
        metadata = index.context.get("metadata", {})
        home_title = metadata.get("title") or "Home"
        home_url = metadata.get("current_url") or metadata.get("canonical_url") or ""
        root = GraphNode(
            node_id="home",
            label=home_title,
            href=home_url or None,
            selector=None,
            source="metadata",
            classification="Home",
            priority=100,
            is_internal=True,
        )

        graph = cls(root=root, nodes_by_id={root.node_id: root})

        for link in index.ranked_nav_links(exclude_logo=True):
            node = graph._link_node(link, source="navigation")
            if node:
                graph.navigation_nodes.append(node)
                graph.nodes_by_id[node.node_id] = node

        for link in index.ranked_footer_links(exclude_logo=True):
            node = graph._link_node(link, source="footer")
            if node:
                graph.footer_nodes.append(node)
                graph.nodes_by_id[node.node_id] = node

        for section in index.ranked_sections():
            node_id = f"section:{section.get('semantic_type', 'general')}:{section.get('heading', '')}"
            node = GraphNode(
                node_id=node_id,
                label=section.get("heading") or section.get("semantic_type", "section").title(),
                href=None,
                selector=None,
                source="section",
                classification=section.get("semantic_type", "section"),
                priority=int(section.get("priority", 0)),
                is_internal=True,
            )
            graph.section_nodes.append(node)
            graph.nodes_by_id[node_id] = node

        cta = index.highest_priority_cta()
        if cta:
            graph.cta_node = graph._button_node(cta)

        return graph

    @staticmethod
    def _link_node(link: dict, *, source: str) -> GraphNode | None:
        text = (link.get("text") or "").strip()
        href = link.get("href")
        if not text and not href:
            return None
        label = text or href or "link"
        node_id = f"{source}:{href or label}".lower()
        selector = link.get("selector") or (f"a[href='{href}']" if href else None)
        parsed = urlparse(href or "")
        is_internal = bool(link.get("internal", parsed.scheme in {"", "http", "https"}))
        return GraphNode(
            node_id=node_id,
            label=label,
            href=href,
            selector=selector,
            source=source,
            classification=link.get("classification", "Link"),
            priority=int(link.get("priority", 0)),
            is_internal=is_internal,
        )

    @staticmethod
    def _button_node(button: dict) -> GraphNode:
        text = (button.get("text") or "button").strip()
        selector = button.get("selector")
        return GraphNode(
            node_id=f"cta:{selector or text}".lower(),
            label=text,
            href=None,
            selector=selector,
            source="button",
            classification=button.get("classification", "CTA"),
            priority=int(button.get("priority", 0)),
            is_internal=True,
        )

    def primary_nav_destinations(self, limit: int = 3) -> list[GraphNode]:
        """Return diverse internal navigation targets for multi-page journeys."""
        seen_labels: set[str] = set()
        destinations: list[GraphNode] = []
        for node in self.navigation_nodes:
            key = node.label.lower()
            if key in seen_labels:
                continue
            if node.classification in ContextIndex.LOGO_CLASSIFICATIONS:
                continue
            if not node.is_internal and node.source == "navigation":
                continue
            seen_labels.add(key)
            destinations.append(node)
            if len(destinations) >= limit:
                break
        return destinations

    def footer_destinations(self, limit: int = 2) -> list[GraphNode]:
        seen: set[str] = set()
        destinations: list[GraphNode] = []
        for node in self.footer_nodes:
            key = node.label.lower()
            if key in seen:
                continue
            seen.add(key)
            destinations.append(node)
            if len(destinations) >= limit:
                break
        return destinations

    def content_sections(self, *, exclude: set[str] | None = None) -> list[GraphNode]:
        blocked = {value.lower() for value in (exclude or set())}
        return [node for node in self.section_nodes if node.label.lower() not in blocked]

    def tree_summary(self) -> dict:
        """Human-readable graph summary for logging."""
        return {
            "home": self.root.label,
            "navigation": [node.label for node in self.navigation_nodes[:8]],
            "footer": [node.label for node in self.footer_nodes[:6]],
            "sections": [node.label for node in self.section_nodes[:6]],
            "primary_cta": self.cta_node.label if self.cta_node else None,
        }
