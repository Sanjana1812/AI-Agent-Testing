NAVIGATION_LANDMARK_SELECTOR_CHAIN = (
    "[role='navigation'], nav, header nav, header:has(nav), nav a:visible"
)

SEMANTIC_TARGET_SELECTORS: dict[str, str] = {
    "navigation": NAVIGATION_LANDMARK_SELECTOR_CHAIN,
    "menu": "nav, [role='navigation'], .menu",
    "header": "header",
    "footer": "footer",
    "hero": "main, section:first-of-type, [role='banner']",
    "section": "section, main, main section, [role='main']",
    "button": "button, [role='button']",
    "submit": "button[type='submit'], input[type='submit']",
    "form": "form",
    "input": "input:visible",
    "email": "input[type='email'], input[name*='email' i], input[id*='email' i]",
    "password": "input[type='password']",
    "link": "nav a:visible, header a:visible, a:visible",
    "image": "img:visible",
    "text": "body",
    "page": "body",
}
