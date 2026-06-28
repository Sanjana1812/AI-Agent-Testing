import time
import uuid
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from app.services.ai_planner import generate_test_plan
from app.services.assertions import AssertionContext, AssertionEngine
from app.services.semantic_targets import SEMANTIC_TARGET_SELECTORS
from app.services.test_analyzer import TestAnalyzer

STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / "storage" / "screenshots"
TIMEOUT_MS = 30_000
TARGET_TIMEOUT_MS = 5_000
_executor = ProcessPoolExecutor(max_workers=2)


class PlaywrightRunError(Exception):
    def __init__(self, message: str, error_type: str = "execution_error"):
        self.message = message
        self.error_type = error_type
        super().__init__(message)


class TargetNotFoundError(Exception):
    def __init__(self, target: str, selector: str):
        self.target = target
        self.selector = selector
        super().__init__(f"Target '{target}' not found using selector '{selector}'")


def _step_name(action: dict) -> str:
    act = action["action"]
    if "target" in action:
        name = f"{act}:{action['target']}"
        if act == "fill" and "value" in action:
            return f"{name}"
        return name
    if "text" in action:
        return f"{act}:{action['text']}"
    if act == "wait":
        return f"wait:{action.get('ms', 1000)}ms"
    return act


def _resolve_selector(target: str) -> str:
    selector = SEMANTIC_TARGET_SELECTORS.get(target)
    if not selector:
        raise TargetNotFoundError(target, "")
    return selector


def _locator(page: Page, target: str):
    selector = _resolve_selector(target)
    return page.locator(selector).first, selector


def _verify_target_visible(page: Page, target: str) -> None:
    locator, selector = _locator(page, target)
    try:
        locator.wait_for(state="visible", timeout=TARGET_TIMEOUT_MS)
    except PlaywrightTimeoutError as exc:
        raise TargetNotFoundError(target, selector) from exc


def _click_target(page: Page, target: str) -> None:
    locator, selector = _locator(page, target)
    try:
        locator.wait_for(state="visible", timeout=TARGET_TIMEOUT_MS)
        locator.click(timeout=TARGET_TIMEOUT_MS)
    except PlaywrightTimeoutError as exc:
        raise TargetNotFoundError(target, selector) from exc


def _fill_target(page: Page, target: str, value: str) -> None:
    locator, selector = _locator(page, target)
    try:
        locator.wait_for(state="visible", timeout=TARGET_TIMEOUT_MS)
        locator.fill(value, timeout=TARGET_TIMEOUT_MS)
    except PlaywrightTimeoutError as exc:
        raise TargetNotFoundError(target, selector) from exc


def _scroll_target(page: Page, target: str) -> None:
    locator, selector = _locator(page, target)
    try:
        locator.scroll_into_view_if_needed(timeout=TARGET_TIMEOUT_MS)
        page.wait_for_timeout(500)
    except PlaywrightTimeoutError as exc:
        raise TargetNotFoundError(target, selector) from exc


def _verify_form(page: Page, target: str) -> None:
    locator, selector = _locator(page, target)
    try:
        locator.wait_for(state="visible", timeout=TARGET_TIMEOUT_MS)
        input_count = locator.locator("input, textarea, select").count()
        if input_count == 0:
            raise TargetNotFoundError(target, selector)
    except PlaywrightTimeoutError as exc:
        raise TargetNotFoundError(target, selector) from exc


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
    elif action_type == "wait":
        page.wait_for_timeout(int(action.get("ms", 1000)))
    elif action_type == "click":
        _click_target(page, action["target"])
    elif action_type == "scroll":
        _scroll_target(page, action["target"])
    elif action_type == "fill":
        _fill_target(page, action["target"], action.get("value", ""))
    elif action_type == "verify_visible":
        _verify_target_visible(page, action["target"])
    elif action_type == "verify_form":
        _verify_form(page, action["target"])
    elif action_type == "verify_text":
        page.get_by_text(action["text"]).wait_for(state="visible", timeout=TARGET_TIMEOUT_MS)
    elif action_type == "capture":
        page.screenshot(path=str(screenshot_path), full_page=False)

    return http_status


def _execute_sync(url: str, goal: str, plan: list[dict], ai_plan_source: str) -> dict:
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

    try:
        with sync_playwright() as playwright:
            browser = None
            try:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page()
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
                    except TargetNotFoundError as exc:
                        action_failed = True
                        analyzer.complete_step("failed")
                        analyzer.add_failure(
                            "javascript_error",
                            str(exc),
                            "medium",
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
                                analyzer.add_failure("assertion_failure", reason, "medium")

                if page and not abort_execution:
                    try:
                        title = page.title()
                        final_url = page.url
                    except PlaywrightError:
                        pass

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
    )


async def run_test(url: str, goal: str) -> dict:
    import asyncio
    import logging

    from app.services.website_context import ContextService
    from app.services.website_context.json_builder import empty_context

    logger = logging.getLogger(__name__)

    plan_data = await generate_test_plan(url, goal)

    try:
        website_context = await ContextService().extract_async(url)
    except Exception as exc:
        logger.warning("[Runner] Website context extraction failed: %s", exc)
        website_context = empty_context()

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        _executor,
        _execute_sync,
        url,
        goal,
        plan_data["plan"],
        plan_data["source"],
    )
    result["_website_context"] = website_context
    result["_source_url"] = url
    return result
