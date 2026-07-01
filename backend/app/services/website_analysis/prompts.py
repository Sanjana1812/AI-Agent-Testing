"""Keyword and template prompts for website classification (Sprint 4.1)."""

from __future__ import annotations

WEBSITE_TYPE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Hospital": (
        "hospital",
        "clinic",
        "medical",
        "healthcare",
        "doctor",
        "patient",
        "appointment",
        "emergency",
        "physician",
        "nursing",
    ),
    "SaaS": (
        "saas",
        "software",
        "platform",
        "pricing",
        "features",
        "dashboard",
        "api",
        "subscription",
        "cloud",
        "trial",
        "demo",
    ),
    "Ecommerce": (
        "shop",
        "store",
        "cart",
        "checkout",
        "product",
        "buy",
        "ecommerce",
        "e-commerce",
        "catalog",
        "basket",
    ),
    "Portfolio": (
        "portfolio",
        "projects",
        "designer",
        "developer",
        "freelance",
        "case study",
        "work",
        "gallery",
    ),
    "Authentication Portal": (
        "login",
        "sign in",
        "signup",
        "register",
        "account",
        "authentication",
    ),
    "Documentation": (
        "docs",
        "documentation",
        "guide",
        "reference",
        "api reference",
        "developer docs",
    ),
    "Contact / Lead Generation": (
        "contact",
        "get in touch",
        "lead",
        "consultation",
        "request demo",
        "book a call",
    ),
}

DOMAIN_BY_TYPE: dict[str, str] = {
    "Hospital": "Healthcare",
    "SaaS": "Technology",
    "Ecommerce": "Retail",
    "Portfolio": "Creative Services",
    "Authentication Portal": "Technology",
    "Documentation": "Technology",
    "Contact / Lead Generation": "Marketing",
    "Marketing Website": "General Business",
    "Business Website": "General Business",
}

PURPOSE_BY_TYPE: dict[str, str] = {
    "Hospital": "Provide medical services and patient access",
    "SaaS": "Acquire and convert software customers",
    "Ecommerce": "Sell products online",
    "Portfolio": "Showcase work and attract clients",
    "Authentication Portal": "Authenticate users and gate access",
    "Documentation": "Help users understand and integrate a product",
    "Contact / Lead Generation": "Capture leads and inquiries",
    "Marketing Website": "Promote brand and drive engagement",
    "Business Website": "Present business information and services",
}

AUDIENCE_BY_TYPE: dict[str, str] = {
    "Hospital": "Patients and caregivers",
    "SaaS": "Business buyers and technical evaluators",
    "Ecommerce": "Online shoppers",
    "Portfolio": "Prospective clients and employers",
    "Authentication Portal": "Registered users",
    "Documentation": "Developers and technical users",
    "Contact / Lead Generation": "Prospective customers",
    "Marketing Website": "Prospective customers",
    "Business Website": "General visitors",
}

GOAL_BY_TYPE: dict[str, str] = {
    "Hospital": "Book appointments and find care",
    "SaaS": "Evaluate features and pricing",
    "Ecommerce": "Discover and purchase products",
    "Portfolio": "Review projects and contact the owner",
    "Authentication Portal": "Sign in or create an account",
    "Documentation": "Find technical guidance",
    "Contact / Lead Generation": "Submit an inquiry",
    "Marketing Website": "Learn about offerings",
    "Business Website": "Explore services and contact the business",
}

JOURNEY_TEMPLATES: dict[str, list[str]] = {
    "Hospital": ["Homepage", "Doctors", "Services", "Appointment", "Contact", "Screenshot"],
    "SaaS": ["Homepage", "Features", "Pricing", "Documentation", "Contact", "Screenshot"],
    "Ecommerce": ["Homepage", "Search", "Category", "Product", "Cart", "Checkout", "Screenshot"],
    "Portfolio": ["Homepage", "Projects", "About", "Contact", "Screenshot"],
    "Authentication Portal": ["Homepage", "Login", "Sign Up", "Dashboard", "Screenshot"],
    "Documentation": ["Homepage", "Documentation", "Search", "API Reference", "Screenshot"],
    "Contact / Lead Generation": ["Homepage", "Services", "Contact", "Form", "Screenshot"],
    "Marketing Website": ["Homepage", "About", "Services", "Contact", "Screenshot"],
    "Business Website": ["Homepage", "About", "Services", "Contact", "Screenshot"],
}

FLOW_ALIASES: dict[str, tuple[str, ...]] = {
    "doctors": ("doctor", "physician", "team", "staff"),
    "services": ("service", "treatment", "care", "departments"),
    "appointment": ("appointment", "book", "schedule"),
    "features": ("feature", "product", "solutions", "capabilities"),
    "pricing": ("pricing", "plans", "price"),
    "documentation": ("docs", "documentation", "guide", "resources"),
    "projects": ("project", "work", "portfolio", "case"),
    "about": ("about", "company", "who we are"),
    "contact": ("contact", "get in touch", "reach"),
    "search": ("search", "find"),
    "category": ("category", "categories", "collection", "shop"),
    "product": ("product", "item", "detail"),
    "cart": ("cart", "basket", "bag"),
    "checkout": ("checkout", "payment", "order"),
    "login": ("login", "sign in", "log in"),
    "sign up": ("sign up", "signup", "register", "create account"),
    "dashboard": ("dashboard", "account", "portal"),
    "form": ("form", "submit", "inquiry"),
}
