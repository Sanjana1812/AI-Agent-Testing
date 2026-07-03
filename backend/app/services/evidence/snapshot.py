"""Execution-time evidence snapshot buffer."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from playwright.sync_api import Page

from app.services.evidence.console import ConsoleLogCollector
from app.services.evidence.dom_capture import capture_dom_snapshot
from app.services.evidence.models import ExecutionContext
from app.services.evidence.network import NetworkLogCollector
from app.services.strategy.models import STRATEGY_VERSION

EVIDENCE_STORAGE = Path(__file__).resolve().parent.parent.parent / "storage" / "evidence"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ExecutionEvidenceBuffer:
    """Attach to a Playwright page and capture evidence during execution."""

    def __init__(
        self,
        run_id: str,
        *,
        browser: str | None = None,
        viewport: str | None = None,
        storage_dir: Path | None = None,
    ) -> None:
        self.run_id = run_id
        self.browser = browser
        self.viewport = viewport
        self.storage_dir = storage_dir or EVIDENCE_STORAGE
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.console = ConsoleLogCollector()
        self.network = NetworkLogCollector()
        self._failure_records: list[dict[str, Any]] = []
        self._page_errors: list[str] = []

    def attach(self, page: Page) -> None:
        self.console.attach(page)
        self.network.attach(page)
        page.on("pageerror", lambda error: self._page_errors.append(str(error)))

    def capture_failure(
        self,
        page: Page | None,
        *,
        step_number: int,
        step_name: str,
        action: dict | None,
        failure_type: str,
        exception: str,
        previous_steps: list[dict[str, Any]],
        elapsed_time_ms: int,
        planner_metadata: dict | None = None,
    ) -> dict[str, Any]:
        screenshot_rel = None
        dom_snapshot = None
        current_url = None
        page_title = None

        if page is not None:
            try:
                current_url = page.url
                page_title = page.title()
                dom_snapshot = capture_dom_snapshot(page)
            except Exception:
                pass
            try:
                filename = f"{self.run_id}-step{step_number}-{uuid.uuid4().hex[:8]}.png"
                path = self.storage_dir / filename
                page.screenshot(path=str(path), full_page=False)
                screenshot_rel = f"/storage/evidence/{filename}"
            except Exception:
                pass

        action_dict = action or {}
        record = {
            "step_number": step_number,
            "step_name": step_name,
            "action": action_dict.get("action"),
            "timestamp": _utc_now_iso(),
            "current_url": current_url,
            "page_title": page_title,
            "selector_attempted": action_dict.get("selector"),
            "selector_alternatives": list(action_dict.get("selector_alternatives") or []),
            "failure_type": failure_type,
            "exception": exception,
            "screenshot": screenshot_rel,
            "dom_snapshot": dom_snapshot,
            "console_errors": self.console.error_messages() + list(self._page_errors),
            "network_errors": self.network.error_messages(),
            "previous_successful_steps": [
                step for step in previous_steps if step.get("status") == "passed"
            ],
            "execution_context": ExecutionContext(
                browser=self.browser,
                viewport=self.viewport,
                planner_version=(planner_metadata or {}).get("planner_version"),
                strategy_version=STRATEGY_VERSION if planner_metadata else None,
                context_version=(planner_metadata or {}).get("context_version"),
                elapsed_time_ms=elapsed_time_ms,
                retry_count=0,
            ).to_dict(),
        }
        self._failure_records.append(record)
        return record

    def export(self) -> dict[str, Any]:
        return {
            "console_logs": self.console.export(),
            "network_logs": self.network.export(),
            "failure_records": list(self._failure_records),
            "page_errors": list(self._page_errors),
        }
