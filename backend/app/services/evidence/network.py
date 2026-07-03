"""Network log collection during Playwright execution."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from playwright.sync_api import Page, Request, Response


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class NetworkLogCollector:
    """Capture failed and notable network activity for evidence packages."""

    def __init__(self) -> None:
        self._logs: list[dict[str, Any]] = []

    def attach(self, page: Page) -> None:
        page.on("requestfailed", self._on_request_failed)
        page.on("response", self._on_response)

    def _on_request_failed(self, request: Request) -> None:
        failure = request.failure
        self._logs.append(
            {
                "event": "request_failed",
                "url": request.url,
                "method": request.method,
                "resource_type": request.resource_type,
                "failure": failure,
                "timestamp": _utc_now_iso(),
            }
        )

    def _on_response(self, response: Response) -> None:
        status = response.status
        if status >= 400:
            self._logs.append(
                {
                    "event": "http_error",
                    "url": response.url,
                    "status": status,
                    "method": response.request.method,
                    "timestamp": _utc_now_iso(),
                }
            )

    def error_messages(self) -> list[str]:
        messages: list[str] = []
        for entry in self._logs:
            if entry.get("event") == "request_failed":
                messages.append(
                    f"{entry.get('method')} {entry.get('url')} failed: {entry.get('failure')}"
                )
            elif entry.get("event") == "http_error":
                messages.append(f"HTTP {entry.get('status')} for {entry.get('url')}")
        return messages

    def export(self) -> list[dict[str, Any]]:
        return list(self._logs)
