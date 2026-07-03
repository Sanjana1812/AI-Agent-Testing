"""Convert execution step outcomes into structured observations."""

from __future__ import annotations

from typing import Any

from playwright.sync_api import Page

from app.services.execution_intelligence.models import Observation


class ExecutionObserver:
    """
    Observes execution outcomes only.

    Does not make decisions, retry, recover, or dismiss overlays.
  Modal detection evaluates the page but does not interact with it.
    """

    @staticmethod
    def detect_modal(page: Page | None) -> bool:
        """Evaluate common modal/overlay patterns without dismissing them."""
        if page is None:
            return False
        try:
            modal_detected = page.evaluate(
                """() => {
                    const modalSelectors = [
                        '[role="dialog"]',
                        '[aria-modal="true"]',
                        '.modal',
                        '.overlay',
                        '.popup',
                        '[class*="cookie"]',
                        '[id*="cookie"]',
                        '[class*="consent"]',
                        '[id*="consent"]',
                    ];
                    return modalSelectors.some(selector => {
                        const el = document.querySelector(selector);
                        if (!el) return false;
                        const style = window.getComputedStyle(el);
                        return style.display !== 'none' &&
                               style.visibility !== 'hidden' &&
                               style.opacity !== '0';
                    });
                }"""
            )
            return bool(modal_detected)
        except Exception:
            return False

    def observe(self, payload: dict[str, Any]) -> Observation:
        page = payload.get("page")
        modal_detected = payload.get("modal_detected")
        if modal_detected is None and page is not None:
            modal_detected = self.detect_modal(page)
        elif modal_detected is None:
            modal_detected = False

        return Observation(
            step_index=int(payload.get("step_index", 0)),
            step_name=str(payload.get("step_name", "")),
            status=str(payload.get("status", "unknown")),
            current_url=str(payload.get("current_url", "")),
            page_title=str(payload.get("page_title", "")),
            selector=payload.get("selector"),
            selector_found=bool(payload.get("selector_found", False)),
            http_status=int(payload.get("http_status", 0) or 0),
            console_error_count=int(payload.get("console_error_count", 0) or 0),
            network_error_count=int(payload.get("network_error_count", 0) or 0),
            modal_detected=bool(modal_detected),
            execution_time_ms=int(payload.get("execution_time_ms", 0) or 0),
            step_action=str(payload.get("step_action", "")),
            error_message=payload.get("error_message"),
            total_steps=int(payload.get("total_steps", 0) or 0),
        )
