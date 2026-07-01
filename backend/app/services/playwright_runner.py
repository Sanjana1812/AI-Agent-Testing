import logging
import time
import uuid
from datetime import datetime, timezone

from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from app.services.ai_planner import generate_test_plan
from app.services.assertions import AssertionContext, AssertionEngine
from app.services.self_healing import heal_locator
from app.services.playwright_bootstrap import ensure_playwright_browsers, launch_chromium
from app.services.semantic_targets import SEMANTIC_TARGET_SELECTORS
from app.services.wait_strategy import wait_before_action
from app.services.test_analyzer import TestAnalyzer

STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / "storage" / "screenshots"
TIMEOUT_MS = 30_000
TARGET_TIMEOUT_MS = 5_000
VIEWPORT = {"width": 1280, "height": 720}
BROWSER_LABEL = "Chromium (headless)"
_executor = ProcessPoolExecutor(max_workers=2)


def _reset_executor() -> None:
    """Recreate the process pool after a worker crash (common on Windows reload)."""
    global _executor
    try:
        _executor.shutdown(wait=False, cancel_futures=True)
    except Exception:
        pass
    _executor = ProcessPoolExecutor(max_workers=2)


class PlaywrightRunError(Exception):
    def __init__(self, message: str, error_type: str = "execution_error"):
        self.message = message
        self.error_type = error_type
        super().__init__(message)


class TargetNotFoundError(Exception):
    def __init__(self, target: str, selector: str, label: str | None = None):
        self.target = target
        self.selector = selector
        self.label = label
        super().__init__(f"Target '{target}' not found using selector '{selector}'")


def _step_name(action: dict) -> str:
    act = action["action"]
    if action.get("label"):
        return f"{act}:{action['label']}"
    if "target" in action:
        name = f"{act}:{action['target']}"
        if act == "fill" and "value" in action:
            return name
        return name
    if "text" in action:
        return f"{act}:{action['text']}"
    if act == "wait":
        return f"wait:{action.get('ms', 1000)}ms"
    return act


def _resolve_selector(target: str) -> str:
    selector = SEMANTIC_TARGET_SELECTORS.get(target)
    if not selector:
        raise TargetNotFoundError(target, "", target)
    return selector


def _locator(page: Page, action: dict):
    if action.get("selector"):
        selector = str(action["selector"])
        locator = page.locator(selector).first
        try:
            locator.wait_for(state="attached", timeout=500)
            return locator, selector
        except PlaywrightTimeoutError:
            healed, healed_selector = heal_locator(page, action, selector)
            if healed is not None:
                return healed, healed_selector or selector
        return locator, selector
    target = action["target"]
    selector = _resolve_selector(target)
    locator = page.locator(selector).first
    healed, healed_selector = heal_locator(page, action, selector)
    if healed is not None:
        return healed, healed_selector or selector
    return locator, selector


def _failure_metadata(action: dict, exc: Exception, context_summary: dict | None) -> dict:
    selector = getattr(exc, "selector", None) or action.get("selector")
    return {
        "expected_element": action.get("label") or action.get("target") or action.get("text"),
        "selector": selector,
        "available_context": context_summary,
    }


def _verify_target_visible(page: Page, action: dict) -> None:
    wait_before_action(page, action)
    locator, selector = _locator(page, action)
    try:
        locator.wait_for(state="visible", timeout=TARGET_TIMEOUT_MS)
    except PlaywrightTimeoutError as exc:
        raise TargetNotFoundError(action.get("target", ""), selector, action.get("label")) from exc


def _click_target(page: Page, action: dict) -> None:
    wait_before_action(page, action)
    locator, selector = _locator(page, action)
    try:
        locator.wait_for(state="visible", timeout=TARGET_TIMEOUT_MS)
        locator.click(timeout=TARGET_TIMEOUT_MS)
    except PlaywrightTimeoutError as exc:
        raise TargetNotFoundError(action.get("target", ""), selector, action.get("label")) from exc


def _fill_target(page: Page, action: dict, value: str) -> None:
    wait_before_action(page, action)
    locator, selector = _locator(page, action)
    try:
        locator.wait_for(state="visible", timeout=TARGET_TIMEOUT_MS)
        locator.fill(value, timeout=TARGET_TIMEOUT_MS)
    except PlaywrightTimeoutError as exc:
        raise TargetNotFoundError(action.get("target", ""), selector, action.get("label")) from exc


def _scroll_target(page: Page, action: dict) -> None:
    wait_before_action(page, action)
    locator, selector = _locator(page, action)
    try:
        locator.scroll_into_view_if_needed(timeout=TARGET_TIMEOUT_MS)
        page.wait_for_timeout(500)
    except PlaywrightTimeoutError as exc:
        if action.get("target") in {"section", "hero", "footer"}:
            for fallback in ("main", "body"):
                try:
                    page.locator(fallback).first.scroll_into_view_if_needed(timeout=TARGET_TIMEOUT_MS)
                    page.wait_for_timeout(500)
                    return
                except PlaywrightTimeoutError:
                    continue
        raise TargetNotFoundError(action.get("target", ""), selector, action.get("label")) from exc


def _verify_form(page: Page, action: dict) -> None:
    wait_before_action(page, action)
    locator, selector = _locator(page, action)
    try:
        locator.wait_for(state="visible", timeout=TARGET_TIMEOUT_MS)
        input_count = locator.locator("input, textarea, select").count()
        if input_count == 0:
            raise TargetNotFoundError(action.get("target", ""), selector, action.get("label"))
    except PlaywrightTimeoutError as exc:
        raise TargetNotFoundError(action.get("target", ""), selector, action.get("label")) from exc


def _execute_action(
    page: Page,
    action: dict,
    url: str,
    screenshot_path: Path,
) -> int | None:
    action_type = action["action"]
    http_status: int | None = None

    if action_type == "open_page":
        response = page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT_MS)
        http_status = response.status if response else 0
        wait_before_action(page, action)
    elif action_type == "wait":
        page.wait_for_timeout(int(action.get("ms", 1000)))
    elif action_type == "click":
        _click_target(page, action)
    elif action_type == "scroll":
        _scroll_target(page, action)
    elif action_type == "fill":
        _fill_target(page, action, action.get("value", ""))
    elif action_type == "verify_visible":
        _verify_target_visible(page, action)
    elif action_type == "verify_form":
        _verify_form(page, action)
    elif action_type == "verify_text":
        wait_before_action(page, action)
        page.get_by_text(action["text"]).wait_for(state="visible", timeout=TARGET_TIMEOUT_MS)
    elif action_type == "capture":
        page.screenshot(path=str(screenshot_path), full_page=False)

    return http_status


def _execute_sync(
    url: str,
    goal: str,
    plan: list[dict],
    ai_plan_source: str,
    context_summary: dict | None = None,
) -> dict:
    run_id = str(uuid.uuid4())
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    screenshot_filename = f"{run_id}.png"
    screenshot_path = STORAGE_DIR / screenshot_filename
    screenshot_rel = ""

    step_names = [_step_name(action) for action in plan]
    analyzer = TestAnalyzer(step_names)
    assertion_engine = AssertionEngine()
    start = time.perf_counter()

    title = ""
    final_url = url
    http_status = 0
    browser = None
    page = None
    js_errors: list[str] = []
    abort_execution = False
    screenshot_captured_at: str | None = None

    try:
        ensure_playwright_browsers()
        with sync_playwright() as playwright:
            browser = None
            try:
                browser = launch_chromium(playwright)
                page = browser.new_page(viewport=VIEWPORT)
                page.on("pageerror", lambda error: js_errors.append(str(error)))

                for index, action in enumerate(plan, start=1):
                    if abort_execution:
                        break

                    step_id = str(index)
                    step_label = step_names[index - 1]
                    analyzer.start_step(step_id, step_label)
                    step_start = time.perf_counter()
                    action_failed = False

                    try:
                        result_status = _execute_action(page, action, url, screenshot_path)
                        if result_status is not None:
                            http_status = result_status
                            final_url = page.url
                        if action["action"] == "capture" and screenshot_path.exists():
                            screenshot_rel = f"/storage/screenshots/{screenshot_filename}"
                            screenshot_captured_at = datetime.now(timezone.utc).isoformat()
                    except TargetNotFoundError as exc:
                        action_failed = True
                        analyzer.complete_step("failed")
                        analyzer.add_failure(
                            "element_not_found",
                            str(exc),
                            "medium",
                            **_failure_metadata(action, exc, context_summary),
                        )
                    except PlaywrightTimeoutError:
                        action_failed = True
                        if action["action"] == "open_page":
                            analyzer.complete_step("failed")
                            analyzer.add_failure(
                                "timeout",
                                f"Timed out while executing '{step_label}'.",
                                "high",
                            )
                            analyzer.skip_remaining_steps()
                            abort_execution = True
                        else:
                            analyzer.complete_step("failed")
                            analyzer.add_failure(
                                "timeout",
                                f"Timed out while executing '{step_label}'.",
                                "medium",
                            )
                    except PlaywrightError as exc:
                        action_failed = True
                        analyzer.complete_step("failed")
                        message = str(exc).splitlines()[0]
                        if action["action"] == "open_page" or "net::ERR" in str(exc) or "NS_ERROR" in str(exc):
                            analyzer.add_failure(
                                "navigation_error",
                                f"Could not complete '{step_label}': {message}",
                                "high",
                            )
                            analyzer.skip_remaining_steps()
                            abort_execution = True
                        else:
                            analyzer.add_failure(
                                "javascript_error",
                                f"Action '{step_label}' failed: {message}",
                                "medium",
                            )
                    except Exception as exc:
                        action_failed = True
                        analyzer.complete_step("failed")
                        analyzer.add_failure(
                            "javascript_error",
                            f"Action '{step_label}' failed: {exc}",
                            "medium",
                        )

                    if not action_failed:
                        action_duration_ms = int((time.perf_counter() - step_start) * 1000)
                        assertion_ctx = AssertionContext(
                            page=page,
                            action=action,
                            url=url,
                            http_status=http_status if action["action"] == "open_page" else None,
                            action_duration_ms=action_duration_ms,
                            screenshot_path=screenshot_path if action["action"] == "capture" else None,
                        )
                        assertion_results = assertion_engine.run_for_action(assertion_ctx)

                        if assertion_engine.all_passed(assertion_results):
                            analyzer.complete_step("passed", assertions=assertion_results)
                        else:
                            analyzer.complete_step("failed", assertions=assertion_results)
                            for reason in assertion_engine.failure_reasons(assertion_results):
                                analyzer.add_failure(
                                    "assertion_failure",
                                    reason,
                                    "medium",
                                    expected_element=action.get("label") or action.get("target"),
                                    selector=action.get("selector"),
                                    available_context=context_summary,
                                )

                if page and not abort_execution:
                    try:
                        title = page.title()
                        final_url = page.url
                    except PlaywrightError:
                        pass

                    capture_index = next(
                        (idx for idx, step in enumerate(plan) if step.get("action") == "capture"),
                        None,
                    )
                    if capture_index is not None:
                        final_ctx = AssertionContext(
                            page=page,
                            action=plan[capture_index],
                            url=url,
                            http_status=http_status,
                            screenshot_path=screenshot_path if screenshot_path.exists() else None,
                        )
                        final_assertions = assertion_engine.run_final_assertions(final_ctx)
                        capture_step_id = str(capture_index + 1)
                        for step in analyzer.steps:
                            if step["id"] != capture_step_id:
                                continue
                            existing = list(step.get("assertions") or [])
                            step["assertions"] = existing + final_assertions
                            if assertion_engine.all_passed(final_assertions):
                                if step["status"] != "failed":
                                    step["status"] = "passed"
                            else:
                                step["status"] = "failed"
                                for reason in assertion_engine.failure_reasons(final_assertions):
                                    analyzer.add_failure(
                                        "assertion_failure",
                                        reason,
                                        "medium",
                                        available_context=context_summary,
                                    )
                            break

                for js_error in js_errors:
                    analyzer.add_failure("javascript_error", js_error, "low")

                analyzer.check_http_status(http_status)
                if "capture" not in [step["action"] for step in plan]:
                    analyzer.check_screenshot(screenshot_rel)
            finally:
                if browser:
                    browser.close()

    except Exception as exc:
        if not analyzer.steps:
            analyzer.start_step("1", step_names[0] if step_names else "open_page")
            analyzer.complete_step("failed")
        analyzer.add_failure(
            "navigation_error",
            f"Browser crashed during execution: {exc}",
            "high",
        )
        analyzer.skip_remaining_steps()

    return analyzer.build_result(
        run_id=run_id,
        goal=goal,
        title=title,
        url=final_url,
        http_status=http_status,
        duration_ms=int((time.perf_counter() - start) * 1000),
        screenshot=screenshot_rel,
        ai_plan=plan,
        ai_plan_source=ai_plan_source,
        viewport=f"{VIEWPORT['width']}×{VIEWPORT['height']}",
        browser=BROWSER_LABEL,
        screenshot_captured_at=screenshot_captured_at,
    )


async def run_test(url: str, goal: str) -> dict:
    import asyncio
    import logging

    from app.services.planner.context_index import ContextIndex
    from app.services.website_context import ContextService
    from app.services.website_context.json_builder import empty_context

    logger = logging.getLogger(__name__)

    try:
        website_context = await ContextService().extract_async(url)
    except Exception as exc:
        logger.warning("[Runner] Website context extraction failed: %s", exc)
        website_context = empty_context()

    from app.services.website_analysis import analyze_website

    website_analysis = analyze_website(website_context, goal=goal)
    context_summary = ContextIndex(website_context).summary()
    plan_data = await generate_test_plan(url, goal, website_context, website_analysis=website_analysis)

    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(
            _executor,
            _execute_sync,
            url,
            goal,
            plan_data["plan"],
            plan_data["source"],
            context_summary,
        )
    except BrokenProcessPool as exc:
        logger.warning("[Runner] Process pool broken, resetting and retrying once: %s", exc)
        _reset_executor()
        result = await loop.run_in_executor(
            _executor,
            _execute_sync,
            url,
            goal,
            plan_data["plan"],
            plan_data["source"],
            context_summary,
        )
    if plan_data.get("metadata"):
        result["ai_plan_metadata"] = plan_data["metadata"]
    if plan_data.get("website_analysis"):
        result["_website_analysis"] = plan_data["website_analysis"]
    result["_website_context"] = website_context
    result["_source_url"] = url
    return result
