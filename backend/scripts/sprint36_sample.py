import asyncio

from app.services.ai_planner import generate_test_plan

SAMPLE_CONTEXT = {
    "metadata": {"title": "Hospverse", "current_url": "https://sanjana.hospverse.com"},
    "navigation": [
        {
            "text": "About",
            "href": "/about",
            "internal": True,
            "priority": 80,
            "visible": True,
            "classification": "Primary Navigation",
            "selector": "a[href='/about']",
        },
        {
            "text": "Contact",
            "href": "/contact",
            "internal": True,
            "priority": 75,
            "visible": True,
            "classification": "Primary Navigation",
            "selector": "a[href='/contact']",
        },
    ],
    "headings": [{"level": 1, "text": "Welcome to Hospverse"}],
    "buttons": [
        {
            "text": "LET'S TALK",
            "selector": "a.cta-talk",
            "priority": 95,
            "classification": "CTA",
            "type": "cta",
            "visible": True,
            "enabled": True,
        }
    ],
    "sections": [{"heading": "Services", "semantic_type": "features", "priority": 70}],
    "footer": [{"text": "Privacy", "href": "/privacy", "internal": True, "priority": 40, "visible": True}],
    "links": [],
    "forms": [],
}


async def main() -> None:
    for goal in ("check the flow", "verify navigation"):
        plan_data = await generate_test_plan("https://sanjana.hospverse.com", goal, SAMPLE_CONTEXT)
        print("GOAL:", goal)
        print(" intent:", plan_data["intent"], "steps:", len(plan_data["plan"]))
        for step in plan_data["plan"]:
            print("  -", step.get("label") or step.get("action"))
        print()


if __name__ == "__main__":
    asyncio.run(main())
