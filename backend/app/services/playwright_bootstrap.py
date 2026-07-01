"""Ensure Playwright Chromium is installed and launchable in all environments."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import Browser, Playwright
from playwright.sync_api import Error as PlaywrightError

logger = logging.getLogger(__name__)

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
_BROWSERS_DIR = _BACKEND_ROOT / "storage" / "playwright-browsers"
_TMP_DIR = _BACKEND_ROOT / "storage" / "playwright-tmp"
_install_attempted = False


def _default_system_browser_dir() -> Path:
    local_app = os.environ.get("LOCALAPPDATA")
    if local_app:
        return Path(local_app) / "ms-playwright"
    return Path.home() / ".cache" / "ms-playwright"


def configure_playwright_env(*, use_project_browsers: bool = False) -> Path | None:
    """Optionally pin browser binaries to a stable project-local directory."""
    if use_project_browsers:
        _BROWSERS_DIR.mkdir(parents=True, exist_ok=True)
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(_BROWSERS_DIR)
        return _BROWSERS_DIR
    configured = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    return Path(configured) if configured else None


def _install_env() -> dict[str, str]:
    _TMP_DIR.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["TMP"] = str(_TMP_DIR)
    env["TEMP"] = str(_TMP_DIR)
    return env


def _run_browser_install(*, use_project_browsers: bool) -> bool:
    env = _install_env()
    if use_project_browsers:
        _BROWSERS_DIR.mkdir(parents=True, exist_ok=True)
        env["PLAYWRIGHT_BROWSERS_PATH"] = str(_BROWSERS_DIR)
    else:
        env.pop("PLAYWRIGHT_BROWSERS_PATH", None)

    logger.info(
        "[Playwright] Installing Chromium (project_path=%s)",
        env.get("PLAYWRIGHT_BROWSERS_PATH", "system default"),
    )
    try:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
            capture_output=True,
            text=True,
            timeout=900,
            env=env,
        )
        return True
    except subprocess.CalledProcessError as exc:
        logger.error("[Playwright] Browser install failed: %s", exc.stderr or exc)
        return False
    except Exception as exc:
        logger.error("[Playwright] Browser install error: %s", exc)
        return False


def _can_launch_chromium(*, use_project_browsers: bool = False) -> bool:
    if use_project_browsers:
        configure_playwright_env(use_project_browsers=True)
    else:
        configure_playwright_env(use_project_browsers=False)

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            browser.close()
        return True
    except Exception as exc:
        logger.debug("[Playwright] Chromium launch probe failed: %s", exc)
        return False


def ensure_playwright_browsers(*, force_install: bool = False) -> bool:
    """Install Chromium if missing; return True when launch succeeds."""
    global _install_attempted

    if not force_install and _can_launch_chromium(use_project_browsers=False):
        logger.info("[Playwright] Chromium available (system/default path)")
        return True

    if not force_install and _can_launch_chromium(use_project_browsers=True):
        logger.info("[Playwright] Chromium available at %s", _BROWSERS_DIR)
        return True

    if _install_attempted and not force_install:
        return _can_launch_chromium(use_project_browsers=False) or _can_launch_chromium(
            use_project_browsers=True
        )

    _install_attempted = True

    if _run_browser_install(use_project_browsers=False) and _can_launch_chromium(use_project_browsers=False):
        return True

    if _run_browser_install(use_project_browsers=True) and _can_launch_chromium(use_project_browsers=True):
        return True

    system_dir = _default_system_browser_dir()
    if system_dir.exists():
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(system_dir)
        return _can_launch_chromium(use_project_browsers=True)

    return False


def launch_chromium(playwright: Playwright, *, headless: bool = True) -> Browser:
    """Launch Chromium, installing browsers on demand when missing."""
    for use_project in (False, True):
        configure_playwright_env(use_project_browsers=use_project)
        try:
            return playwright.chromium.launch(headless=headless)
        except PlaywrightError as exc:
            message = str(exc)
            if "Executable doesn't exist" not in message and "doesn't exist at" not in message:
                raise
            logger.warning("[Playwright] Chromium missing for path strategy project=%s", use_project)

    if ensure_playwright_browsers(force_install=True):
        configure_playwright_env(use_project_browsers=False)
        try:
            return playwright.chromium.launch(headless=headless)
        except PlaywrightError:
            configure_playwright_env(use_project_browsers=True)
            return playwright.chromium.launch(headless=headless)

    raise PlaywrightError(
        "Chromium is not installed. Run: python -m playwright install chromium"
    )
