from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Literal

Severity = Literal["low", "medium", "high"]
Health = Literal["PASS", "FAIL"]
StepStatus = Literal["passed", "failed", "skipped"]

STEP_LABELS = {
    "open_page": "Open Page",
    "wait": "Wait",
    "click": "Click",
    "fill": "Fill",
    "verify_visible": "Verify Visible",
    "verify_text": "Verify Text",
    "capture": "Capture Screenshot",
}


@dataclass
class StepTimer:
    step_id: str
    step: str
    started_at: float = field(default_factory=time.perf_counter)


class TestAnalyzer:
    def __init__(self, step_names: list[str] | None = None) -> None:
        self.step_names = step_names or []
        self.steps: list[dict] = []
        self.failures: list[dict] = []
        self._active: StepTimer | None = None

    def start_step(self, step_id: str, step: str) -> None:
        self._active = StepTimer(step_id=step_id, step=step)

    def complete_step(
        self,
        status: StepStatus = "passed",
        assertions: list[dict] | None = None,
    ) -> None:
        if not self._active:
            return

        duration_ms = int((time.perf_counter() - self._active.started_at) * 1000)
        step_data: dict = {
            "id": self._active.step_id,
            "step": self._active.step,
            "status": status,
            "duration_ms": duration_ms,
        }
        if assertions is not None:
            step_data["assertions"] = assertions
        self.steps.append(step_data)
        self._active = None

    def skip_remaining_steps(self) -> None:
        completed_ids = {step["id"] for step in self.steps}
        for index, step_name in enumerate(self.step_names, start=1):
            step_id = str(index)
            if step_id not in completed_ids:
                self.steps.append(
                    {
                        "id": step_id,
                        "step": step_name,
                        "status": "skipped",
                        "duration_ms": 0,
                        "assertions": [],
                    }
                )

    def add_failure(
        self,
        failure_type: str,
        message: str,
        severity: Severity,
        *,
        expected_element: str | None = None,
        selector: str | None = None,
        available_context: dict | None = None,
    ) -> None:
        failure: dict = {
            "type": failure_type,
            "message": message,
            "severity": severity,
        }
        if expected_element is not None:
            failure["expected_element"] = expected_element
        if selector is not None:
            failure["selector"] = selector
        if available_context is not None:
            failure["available_context"] = available_context
        self.failures.append(failure)

    def check_http_status(self, http_status: int) -> None:
        if http_status >= 400:
            self.add_failure(
                "http_error",
                f"HTTP response returned status {http_status}.",
                "medium",
            )

    def check_screenshot(self, screenshot_path: str | None) -> None:
        if not screenshot_path:
            self.add_failure(
                "screenshot_failure",
                "Screenshot was not captured.",
                "medium",
            )

    def build_summary(self) -> dict:
        passed_steps = sum(1 for step in self.steps if step["status"] == "passed")
        failed_steps = sum(1 for step in self.steps if step["status"] == "failed")
        total_steps = len(self.step_names) or len(self.steps)

        has_failures = bool(self.failures) or failed_steps > 0
        health: Health = "FAIL" if has_failures else "PASS"

        return {
            "total_steps": total_steps,
            "passed_steps": passed_steps,
            "failed_steps": failed_steps,
            "health": health,
        }

    def build_result(
        self,
        *,
        run_id: str,
        goal: str,
        title: str,
        url: str,
        http_status: int,
        duration_ms: int,
        screenshot: str,
        ai_plan: list[dict],
        ai_plan_source: str,
        viewport: str | None = None,
        browser: str | None = None,
        screenshot_captured_at: str | None = None,
    ) -> dict:
        summary = self.build_summary()
        status = "success" if summary["health"] == "PASS" else "failed"

        result = {
            "id": run_id,
            "goal": goal,
            "status": status,
            "title": title,
            "url": url,
            "http_status": http_status,
            "duration_ms": duration_ms,
            "screenshot": screenshot,
            "ai_plan": ai_plan,
            "ai_plan_source": ai_plan_source,
            "steps": self.steps,
            "failures": self.failures,
            "summary": summary,
        }
        if viewport:
            result["viewport"] = viewport
        if browser:
            result["browser"] = browser
        if screenshot_captured_at:
            result["screenshot_captured_at"] = screenshot_captured_at
        return result
