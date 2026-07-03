import logging
import time
import uuid
from datetime import datetime, timezone

from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from pathlib import Path

from typing import Any

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from app.services.ai_planner import generate_test_plan
from app.services.assertions import AssertionContext, AssertionEngine
from app.services.self_healing import heal_locator
from app.services.playwright_bootstrap import ensure_playwright_browsers, launch_chromium
from app.services.semantic_targets import NAVIGATION_LANDMARK_SELECTOR_CHAIN, SEMANTIC_TARGET_SELECTORS
from app.services.wait_strategy import wait_before_action
from app.services.test_analyzer import TestAnalyzer
from app.services.evidence.snapshot import ExecutionEvidenceBuffer
from app.services.execution_intelligence import ExecutionIntelligenceOrchestrator
from app.services.execution_intelligence.models import DecisionType
from app.services.execution_intelligence.recovery import dismiss_modal_overlay
from app.services.execution_intelligence.summary import build_summary_from_export
from app.services.replanning import ReplanningEngine

STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / "storage" / "screenshots"
EVIDENCE_DIR = Path(__file__).resolve().parent.parent.parent / "storage" / "evidence"
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


def _is_misleading_navigation_selector(selector: str | None) -> bool:
    if not selector:
        return False
    lowered = str(selector).lower()
    return (
        "has-text" in lowered
        and ("navigation" in lowered or "nav bar" in lowered or lowered.endswith('"nav")'))
    ) or (lowered.startswith("button") and "navigation" in lowered)


def _locator_for_navigation_verify(page: Page, action: dict) -> tuple[Any, str]:
    selectors: list[str] = []
    step_selector = action.get("selector")
    if step_selector and not _is_misleading_navigation_selector(str(step_selector)):
        selectors.append(str(step_selector))
    selectors.extend(NAVIGATION_LANDMARK_SELECTOR_CHAIN.split(", "))
    seen: set[str] = set()
    for selector in selectors:
        normalized = selector.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        locator = page.locator(normalized).first
        try:
            if locator.count() > 0:
                locator.wait_for(state="attached", timeout=500)
                return locator, normalized
        except PlaywrightTimeoutError:
            continue
    raise TargetNotFoundError(
        action.get("target", "navigation"),
        step_selector or NAVIGATION_LANDMARK_SELECTOR_CHAIN,
        action.get("label"),
    )


def _locator(page: Page, action: dict):
    if action.get("action") == "verify_visible" and action.get("target") == "navigation":
        return _locator_for_navigation_verify(page, action)
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


def _step_error_message(analyzer: TestAnalyzer) -> str | None:
    if analyzer.steps and analyzer.steps[-1].get("status") == "failed" and analyzer.failures:
        return str(analyzer.failures[-1].get("message", ""))
    return None


def _intelligence_step_payload(
    *,
    index: int,
    step_label: str,
    action: dict,
    analyzer: TestAnalyzer,
    page: Page | None,
    title: str,
    http_status: int,
    js_errors: list[str],
    action_failed: bool,
    step_start: float,
    total_steps: int,
) -> dict:
    last_step = analyzer.steps[-1] if analyzer.steps else None
    status = last_step["status"] if last_step else ("failed" if action_failed else "passed")
    duration_ms = (
        last_step["duration_ms"]
        if last_step
        else int((time.perf_counter() - step_start) * 1000)
    )
    current_url = ""
    page_title = title
    if page:
        try:
            current_url = page.url
            page_title = page.title()
        except PlaywrightError:
            current_url = ""

    return {
        "step_index": index,
        "step_name": step_label,
        "status": status,
        "current_url": current_url,
        "page_title": page_title,
        "selector": action.get("selector"),
        "selector_found": status == "passed" and not action_failed,
        "http_status": http_status,
        "console_error_count": len(js_errors),
        "network_error_count": 0,
        "modal_detected": None,
        "execution_time_ms": duration_ms,
        "step_action": str(action.get("action", "")),
        "error_message": _step_error_message(analyzer),
        "total_steps": total_steps,
        "page": page,
    }


def _apply_adaptive_actions(
    *,
    intelligence_orchestrator: ExecutionIntelligenceOrchestrator,
    analyzer: TestAnalyzer,
    page: Page | None,
    index: int,
    step_label: str,
    action: dict,
    title: str,
    http_status: int,
    js_errors: list[str],
    action_failed: bool,
    step_start: float,
    total_steps: int,
    rerun_step,
    plan: list[dict],
    step_names: list[str],
) -> str:
    """Apply adaptive intelligence actions.

    Returns:
        ``continue`` — proceed to the next step
        ``abort`` — stop execution
        ``replay_step`` — retry the current step (after replan or recovery)
    """
    payload = _intelligence_step_payload(
        index=index,
        step_label=step_label,
        action=action,
        analyzer=analyzer,
        page=page,
        title=title,
        http_status=http_status,
        js_errors=js_errors,
        action_failed=action_failed,
        step_start=step_start,
        total_steps=total_steps,
    )

    for _ in range(4):
        outcome = intelligence_orchestrator.process_step(payload)

        if outcome.requires_skip:
            analyzer.convert_last_step_to_skipped(outcome.decision.reason)
            analyzer.remove_last_failure()
            return "continue"

        if outcome.requires_abort:
            analyzer.skip_remaining_steps()
            return "abort"

        if outcome.requires_replan:
            context = intelligence_orchestrator.context
            if context is None:
                return "continue"
            remaining_plan = [dict(step) for step in plan[index - 1 :]]
            replan_result = ReplanningEngine().replan(
                observation=outcome.observation,
                context=context,
                remaining_plan=remaining_plan,
                decision=outcome.decision,
                website_context=context.website_context,
            )
            if replan_result.success and replan_result.history:
                completed_prefix = [dict(step) for step in plan[: index - 1]]
                new_tail = [dict(step) for step in replan_result.modified_remaining_plan]
                plan[:] = completed_prefix + new_tail
                step_names[:] = [_step_name(step) for step in plan]
                context.total_steps = len(plan)
                intelligence_orchestrator.record_replan_history(replan_result.history.to_dict())
                analyzer.remove_last_failure()
                analyzer.replace_last_step()
                if rerun_step():
                    return "continue"
                return "replay_step"
            return "continue"

        if outcome.requires_recover:
            selectors = outcome.decision.metadata.get("dismiss_selectors") or []
            if dismiss_modal_overlay(page, selectors) and rerun_step():
                return "continue"
            payload = _intelligence_step_payload(
                index=index,
                step_label=step_label,
                action=action,
                analyzer=analyzer,
                page=page,
                title=title,
                http_status=http_status,
                js_errors=js_errors,
                action_failed=True,
                step_start=step_start,
                total_steps=total_steps,
            )
            continue

        if outcome.requires_retry:
            alternative = outcome.decision.metadata.get("alternative_selector")
            if rerun_step(selector_override=alternative):
                return "continue"
            payload = _intelligence_step_payload(
                index=index,
                step_label=step_label,
                action=action,
                analyzer=analyzer,
                page=page,
                title=title,
                http_status=http_status,
                js_errors=js_errors,
                action_failed=True,
                step_start=step_start,
                total_steps=total_steps,
            )
            continue

        return "continue"

    return "continue"


def _execute_sync(
    url: str,
    goal: str,
    plan: list[dict],
    ai_plan_source: str,
    context_summary: dict | None = None,
    intelligence_input: dict | None = None,
) -> dict:
    ensure_playwright_browsers()
    run_id = str(uuid.uuid4())
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    screenshot_filename = f"{run_id}.png"
    screenshot_path = STORAGE_DIR / screenshot_filename
    screenshot_rel = ""

    step_names = [_step_name(action) for action in plan]
    plan = list(plan)
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
    evidence_buffer = ExecutionEvidenceBuffer(
        run_id,
        browser=BROWSER_LABEL,
        viewport=f"{VIEWPORT['width']}×{VIEWPORT['height']}",
        storage_dir=EVIDENCE_DIR,
    )
    intelligence_orchestrator: ExecutionIntelligenceOrchestrator | None = None
    if intelligence_input:
        intelligence_orchestrator = ExecutionIntelligenceOrchestrator()
        intelligence_orchestrator.start(
            goal=str(intelligence_input.get("goal") or goal),
            website_analysis=intelligence_input.get("website_analysis"),
            strategy=intelligence_input.get("strategy"),
            planner_metadata=intelligence_input.get("planner_metadata"),
            website_context=intelligence_input.get("website_context"),
            total_steps=len(plan),
        )

    def _record_failure_evidence(
        step_id: str,
        step_label: str,
        action: dict,
        failure_type: str,
        exception: str,
    ) -> None:
        if not page:
            return
        evidence_buffer.capture_failure(
            page,
            step_number=int(step_id),
            step_name=step_label,
            action=action,
            failure_type=failure_type,
            exception=exception,
            previous_steps=list(analyzer.steps),
            elapsed_time_ms=int((time.perf_counter() - start) * 1000),
        )

    try:
        ensure_playwright_browsers()
        with sync_playwright() as playwright:
            browser = None
            try:
                browser = launch_chromium(playwright)
                page = browser.new_page(viewport=VIEWPORT)
                page.on("pageerror", lambda error: js_errors.append(str(error)))
                evidence_buffer.attach(page)

                index = 1
                while index <= len(plan):
                    if abort_execution:
                        break

                    action = plan[index - 1]
                    step_id = str(index)
                    step_label = step_names[index - 1]

                    def run_step_attempt(selector_override: str | None = None) -> bool:
                        nonlocal http_status, final_url, screenshot_rel, screenshot_captured_at, abort_execution
                        current_action = plan[index - 1]
                        current_label = step_names[index - 1]
                        attempt_action = dict(current_action)
                        if selector_override:
                            attempt_action["selector"] = selector_override
                        analyzer.start_step(step_id, current_label)
                        attempt_start = time.perf_counter()
                        attempt_failed = False
                        try:
                            result_status = _execute_action(page, attempt_action, url, screenshot_path)
                            if result_status is not None:
                                http_status = result_status
                                final_url = page.url
                            if attempt_action["action"] == "capture" and screenshot_path.exists():
                                screenshot_rel = f"/storage/screenshots/{screenshot_filename}"
                                screenshot_captured_at = datetime.now(timezone.utc).isoformat()
                        except TargetNotFoundError as exc:
                            attempt_failed = True
                            analyzer.complete_step("failed")
                            analyzer.add_failure(
                                "element_not_found",
                                str(exc),
                                "medium",
                                **_failure_metadata(attempt_action, exc, context_summary),
                            )
                            _record_failure_evidence(
                                step_id, current_label, attempt_action, "element_not_found", str(exc)
                            )
                        except PlaywrightTimeoutError:
                            attempt_failed = True
                            if attempt_action["action"] == "open_page":
                                analyzer.complete_step("failed")
                                analyzer.add_failure(
                                    "timeout",
                                    f"Timed out while executing '{step_label}'.",
                                    "high",
                                )
                                _record_failure_evidence(
                                    step_id,
                                    step_label,
                                    attempt_action,
                                    "timeout",
                                    f"Timed out while executing '{step_label}'.",
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
                                _record_failure_evidence(
                                    step_id,
                                    step_label,
                                    attempt_action,
                                    "timeout",
                                    f"Timed out while executing '{step_label}'.",
                                )
                        except PlaywrightError as exc:
                            attempt_failed = True
                            analyzer.complete_step("failed")
                            message = str(exc).splitlines()[0]
                            if (
                                attempt_action["action"] == "open_page"
                                or "net::ERR" in str(exc)
                                or "NS_ERROR" in str(exc)
                            ):
                                analyzer.add_failure(
                                    "navigation_error",
                                    f"Could not complete '{step_label}': {message}",
                                    "high",
                                )
                                _record_failure_evidence(
                                    step_id, step_label, attempt_action, "navigation_error", message
                                )
                                analyzer.skip_remaining_steps()
                                abort_execution = True
                            else:
                                analyzer.add_failure(
                                    "javascript_error",
                                    f"Action '{step_label}' failed: {message}",
                                    "medium",
                                )
                                _record_failure_evidence(
                                    step_id, step_label, attempt_action, "javascript_error", message
                                )
                        except Exception as exc:
                            attempt_failed = True
                            analyzer.complete_step("failed")
                            analyzer.add_failure(
                                "javascript_error",
                                f"Action '{step_label}' failed: {exc}",
                                "medium",
                            )
                            _record_failure_evidence(
                                step_id, step_label, attempt_action, "javascript_error", str(exc)
                            )

                        if not attempt_failed:
                            action_duration_ms = int((time.perf_counter() - attempt_start) * 1000)
                            assertion_ctx = AssertionContext(
                                page=page,
                                action=attempt_action,
                                url=url,
                                http_status=http_status if attempt_action["action"] == "open_page" else None,
                                action_duration_ms=action_duration_ms,
                                screenshot_path=screenshot_path if attempt_action["action"] == "capture" else None,
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
                                        expected_element=attempt_action.get("label")
                                        or attempt_action.get("target"),
                                        selector=attempt_action.get("selector"),
                                        available_context=context_summary,
                                    )
                                _record_failure_evidence(
                                    step_id,
                                    step_label,
                                    attempt_action,
                                    "assertion_failure",
                                    "; ".join(assertion_engine.failure_reasons(assertion_results)),
                                )
                        return bool(analyzer.steps) and analyzer.steps[-1]["status"] == "passed"

                    def rerun_step(selector_override: str | None = None) -> bool:
                        analyzer.replace_last_step()
                        analyzer.remove_last_failure()
                        return run_step_attempt(selector_override)

                    step_start = time.perf_counter()
                    action_failed = not run_step_attempt()

                    if (
                        intelligence_orchestrator is not None
                        and page
                        and not abort_execution
                        and action["action"] != "open_page"
                    ):
                        adaptive_result = _apply_adaptive_actions(
                            intelligence_orchestrator=intelligence_orchestrator,
                            analyzer=analyzer,
                            page=page,
                            index=index,
                            step_label=step_label,
                            action=action,
                            title=title,
                            http_status=http_status,
                            js_errors=js_errors,
                            action_failed=action_failed,
                            step_start=step_start,
                            total_steps=len(plan),
                            rerun_step=rerun_step,
                            plan=plan,
                            step_names=step_names,
                        )
                        if adaptive_result == "abort":
                            abort_execution = True
                        elif adaptive_result == "replay_step":
                            continue
                    elif intelligence_orchestrator is not None:
                        intelligence_orchestrator.after_step(
                            _intelligence_step_payload(
                                index=index,
                                step_label=step_label,
                                action=action,
                                analyzer=analyzer,
                                page=page,
                                title=title,
                                http_status=http_status,
                                js_errors=js_errors,
                                action_failed=action_failed,
                                step_start=step_start,
                                total_steps=len(plan),
                            )
                        )

                    index += 1

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
                                    _record_failure_evidence(
                                        capture_step_id,
                                        step_names[capture_index],
                                        plan[capture_index],
                                        "assertion_failure",
                                        reason,
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

    result = analyzer.build_result(
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
    result["_execution_evidence"] = evidence_buffer.export()
    if intelligence_orchestrator is not None:
        export = intelligence_orchestrator.export()
        result["_execution_intelligence"] = export
        if intelligence_orchestrator.context is not None:
            result["execution_intelligence_log"] = list(
                intelligence_orchestrator.context.execution_intelligence_log
            )
        result["execution_intelligence"] = build_summary_from_export(export)
    return result


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
        website_context["metadata"] = {
            "current_url": url,
            "extraction_error": str(exc),
        }

    from app.services.website_analysis import analyze_website

    website_analysis = analyze_website(website_context, goal=goal)
    context_summary = ContextIndex(website_context).summary()
    plan_data = await generate_test_plan(url, goal, website_context, website_analysis=website_analysis)

    intelligence_input = {
        "goal": goal,
        "website_analysis": plan_data.get("website_analysis"),
        "strategy": plan_data.get("testing_strategy"),
        "planner_metadata": plan_data.get("metadata"),
        "website_context": website_context,
    }

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
            intelligence_input,
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
            intelligence_input,
        )
    if plan_data.get("metadata"):
        result["ai_plan_metadata"] = plan_data["metadata"]
    if plan_data.get("website_analysis"):
        result["_website_analysis"] = plan_data["website_analysis"]
    if plan_data.get("testing_strategy"):
        result["_testing_strategy"] = plan_data["testing_strategy"]
    result["_website_context"] = website_context
    result["_source_url"] = url
    return result
