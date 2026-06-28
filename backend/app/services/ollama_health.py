from __future__ import annotations

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

HEALTH_CHECK_TIMEOUT_SECONDS = 3.0


async def is_ollama_available() -> bool:
    url = f"{settings.ollama_base_url.rstrip('/')}/api/tags"

    try:
        async with httpx.AsyncClient(timeout=HEALTH_CHECK_TIMEOUT_SECONDS) as client:
            response = await client.get(url)
            if response.status_code == 200:
                return True
            logger.error(
                "[Planner] Ollama health check failed with status %s",
                response.status_code,
            )
            return False
    except Exception as exc:
        logger.error("[Planner] Ollama health check error: %s", exc)
        return False
