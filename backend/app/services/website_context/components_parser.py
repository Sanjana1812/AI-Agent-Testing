"""Extract rich UI components from production websites."""

from __future__ import annotations

import logging

from playwright.sync_api import Page

from app.services.website_context.json_builder import ComponentInfo

logger = logging.getLogger(__name__)

_COMPONENTS_SCRIPT = """
() => {
  const escape = (value) => value.replace(/([!"#$%&'()*+,./:;<=>?@[\\\\\\]^`{|}~])/g, '\\\\$1');
  const buildSelector = (el) => {
    if (el.getAttribute('data-testid')) return `[data-testid="${el.getAttribute('data-testid')}"]`;
    if (el.id) return `#${escape(el.id)}`;
    const tag = el.tagName.toLowerCase();
    const cls = (typeof el.className === 'string' ? el.className.trim().split(/\\s+/)[0] : '');
    if (cls) return `${tag}.${escape(cls)}`;
    return tag;
  };
  const isVisible = (el) => {
    const style = window.getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
  };
  const textOf = (el) => (el.innerText || el.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 120);
  const sectionOf = (el) => {
    if (el.closest('header, [role="banner"], .header, .topbar')) return 'header';
    if (el.closest('footer, [role="contentinfo"], .footer')) return 'footer';
    if (el.closest('aside, [role="complementary"], .sidebar')) return 'sidebar';
    if (el.closest('main, [role="main"], .main-content')) return 'main';
    return 'body';
  };

  const patterns = [
    { type: 'search_bar', selectors: 'input[type="search"], [role="search"] input, form[role="search"] input, .search input, #search' },
    { type: 'tab', selectors: '[role="tab"], .tab, .tabs button, .nav-tabs a, [data-testid*="tab"]' },
    { type: 'accordion', selectors: '[aria-expanded], .accordion, details, .collapse' },
    { type: 'dropdown', selectors: 'select, [role="listbox"], .dropdown, .select' },
    { type: 'modal', selectors: '[role="dialog"], .modal, .overlay, [aria-modal="true"]' },
    { type: 'drawer', selectors: '.drawer, .offcanvas, [data-testid*="drawer"]' },
    { type: 'breadcrumb', selectors: 'nav[aria-label*="breadcrumb" i], .breadcrumb, [role="navigation"].breadcrumb' },
    { type: 'pagination', selectors: '.pagination, nav[aria-label*="pagination" i], [data-testid*="pagination"]' },
    { type: 'carousel', selectors: '.carousel, .slider, [role="region"][aria-roledescription*="carousel" i], .swiper' },
    { type: 'product_grid', selectors: '.product-grid, .products, [data-testid*="product-list"], .grid .product' },
    { type: 'pricing_card', selectors: '.pricing, .price-card, [data-testid*="pricing"], .plan-card' },
    { type: 'feature_card', selectors: '.feature, .feature-card, .card.feature, [data-testid*="feature"]' },
    { type: 'card', selectors: '.card, article.card, [data-testid*="card"]' },
    { type: 'cta_group', selectors: '.cta-group, .hero-actions, .button-group, .actions' },
    { type: 'hero_banner', selectors: '.hero, .banner, [role="banner"], .jumbotron, .landing' },
    { type: 'sticky_header', selectors: 'header.sticky, .sticky-header, .fixed-top, .topbar.sticky' },
    { type: 'side_panel', selectors: '.side-panel, .panel, aside.panel, [data-testid*="sidebar"]' },
    { type: 'login_widget', selectors: 'form[action*="login" i], form:has(input[type="password"]), .login-form, #login' },
    { type: 'shopping_cart', selectors: '[data-testid*="cart"], .cart, .shopping-cart, a[href*="cart"]' },
    { type: 'filter', selectors: '.filter, .filters, [data-testid*="filter"], form.filters' },
    { type: 'mega_menu', selectors: '.mega-menu, .megamenu, .dropdown-menu.mega' },
  ];

  const seen = new Set();
  const components = [];

  for (const pattern of patterns) {
    document.querySelectorAll(pattern.selectors).forEach((el, index) => {
      const text = textOf(el);
      const selector = buildSelector(el);
      const key = pattern.type + '|' + selector + '|' + text;
      if (seen.has(key)) return;
      seen.add(key);
      components.push({
        type: pattern.type,
        text,
        selector,
        importance: Math.max(20, 100 - index * 3),
        page_section: sectionOf(el),
        visible: isVisible(el),
      });
    });
  }
  return components.slice(0, 80);
}
"""


def parse(page: Page) -> list[ComponentInfo]:
    logger.debug("[ContextEngine] Parsing rich UI components")
    raw = page.evaluate(_COMPONENTS_SCRIPT)
    return [
        ComponentInfo(
            type=str(item.get("type", "component")),
            text=str(item.get("text", "")),
            selector=str(item.get("selector", "")),
            importance=int(item.get("importance", 50)),
            page_section=str(item.get("page_section", "body")),
            visible=bool(item.get("visible", False)),
        )
        for item in raw
        if item.get("selector")
    ]
