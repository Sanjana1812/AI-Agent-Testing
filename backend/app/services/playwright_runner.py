import time
import uuid
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / "storage" / "screenshots"
TIMEOUT_MS = 30_000
_executor = ProcessPoolExecutor(max_workers=2)


class PlaywrightRunError(Exception):
    def __init__(self, message: str, error_type: str = "execution_error"):
        self.message = message
        self.error_type = error_type
        super().__init__(message)


def _execute_sync(url: str, goal: str) -> dict:
    run_id = str(uuid.uuid4())
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    screenshot_filename = f"{run_id}.png"
    screenshot_path = STORAGE_DIR / screenshot_filename

    start = time.perf_counter()
    last_error: PlaywrightRunError | None = None

    for attempt in range(2):
        browser = None
        try:
            with sync_playwright() as playwright:
                try:
                    browser = playwright.chromium.launch(headless=True)
                except Exception as exc:
                    raise PlaywrightRunError(
                        f"Failed to launch browser: {exc}",
                        "browser_launch_failure",
                    ) from exc

                try:
                    page = browser.new_page()
                    response = page.goto(url, wait_until="networkidle", timeout=TIMEOUT_MS)

                    title = page.title()
                    final_url = page.url
                    http_status = response.status if response else 0

                    page.screenshot(path=str(screenshot_path), full_page=False)
                except PlaywrightTimeoutError as exc:
                    raise PlaywrightRunError(
                        "Page load timed out after 30 seconds.",
                        "timeout",
                    ) from exc
                except PlaywrightError as exc:
                    message = str(exc)
                    if "net::ERR" in message or "NS_ERROR" in message:
                        raise PlaywrightRunError(
                            f"Could not reach URL ({message.splitlines()[0]}): {url}",
                            "invalid_url",
                        ) from exc
                    raise PlaywrightRunError(message, "execution_error") from exc
                finally:
                    if browser:
                        browser.close()

            duration_ms = int((time.perf_counter() - start) * 1000)

            return {
                "ok": True,
                "data": {
                    "id": run_id,
                    "status": "success",
                    "title": title,
                    "url": final_url,
                    "http_status": http_status,
                    "duration_ms": duration_ms,
                    "screenshot": f"/storage/screenshots/{screenshot_filename}",
                },
            }
        except PlaywrightRunError as exc:
            last_error = exc
            if exc.error_type != "invalid_url" or attempt == 1:
                return {
                    "ok": False,
                    "error_type": exc.error_type,
                    "message": exc.message,
                }
            time.sleep(1)

    return {
        "ok": False,
        "error_type": last_error.error_type if last_error else "execution_error",
        "message": last_error.message if last_error else "Test execution failed.",
    }


async def run_test(url: str, goal: str) -> dict:
    import asyncio

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(_executor, _execute_sync, url, goal)

    if not result["ok"]:
        raise PlaywrightRunError(result["message"], result["error_type"])

    return result["data"]
