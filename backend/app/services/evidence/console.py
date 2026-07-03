"""Console log collection during Playwright execution."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from playwright.sync_api import ConsoleMessage, Page


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ConsoleLogCollector:
    """Capture browser console output for evidence packages."""

    def __init__(self) -> None:
        self._logs: list[dict[str, Any]] = []

    def attach(self, page: Page) -> None:
        page.on("console", self._on_console)

    def _on_console(self, message: ConsoleMessage) -> None:
        entry = {
            "type": message.type,
            "text": message.text,
            "timestamp": _utc_now_iso(),
        }
        location = message.location
        if location:
            entry["location"] = {
                "url": location.get("url"),
                "line": location.get("lineNumber"),
                "column": location.get("columnNumber"),
            }
        self._logs.append(entry)

    def all_logs(self) -> list[dict[str, Any]]:
        return list(self._logs)

    def error_messages(self) -> list[str]:
        errors: list[str] = []
        for entry in self._logs:
            if entry.get("type") in {"error", "warning"}:
                text = str(entry.get("text", "")).strip()
                if text:
                    errors.append(text)
        return errors

    def export(self) -> list[dict[str, Any]]:
        return self.all_logs()
