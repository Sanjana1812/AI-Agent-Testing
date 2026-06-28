"""Ollama AI planning provider."""

from __future__ import annotations

import logging
import time

import httpx

from app.config import settings
from app.services.ai.base import BaseAIProvider, PlanGenerationResult
from app.services.ai.providers.prompt_builder import build_planning_prompt
from app.services.ollama_health import is_ollama_available

logger = logging.getLogger(__name__)

OLLAMA_GENERATE_PATH = "/api/generate"


class OllamaProvider(BaseAIProvider):
    name = "ollama"

    async def is_available(self) -> bool:
        return await is_ollama_available()

    async def generate_plan(
        self,
        *,
        url: str,
        goal: str,
        intent: str,
        website_context: dict,
    ) -> PlanGenerationResult:
        endpoint = f"{settings.ollama_base_url.rstrip('/')}{OLLAMA_GENERATE_PATH}"
        prompt = build_planning_prompt(url, goal, intent, website_context)
        payload = {
            "model": settings.model_name,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }

        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=settings.ollama_timeout_seconds) as client:
                response = await client.post(endpoint, json=payload)
                response.raise_for_status()
                data = response.json()

            text = data.get("response", "")
            latency_ms = int((time.perf_counter() - start) * 1000)
            if not text:
                return PlanGenerationResult(
                    success=False,
                    error="Ollama returned an empty response",
                    provider=self.name,
                    latency_ms=latency_ms,
                )
            return PlanGenerationResult(
                success=True,
                text=text,
                provider=self.name,
                latency_ms=latency_ms,
            )
        except httpx.TimeoutException as exc:
            logger.error("[OllamaProvider] Request timed out: %s", exc)
            return PlanGenerationResult(
                success=False,
                error=f"Timeout: {exc}",
                provider=self.name,
                latency_ms=int((time.perf_counter() - start) * 1000),
            )
        except httpx.HTTPStatusError as exc:
            logger.error("[OllamaProvider] HTTP error: %s", exc)
            return PlanGenerationResult(
                success=False,
                error=f"HTTP error: {exc.response.status_code}",
                provider=self.name,
                latency_ms=int((time.perf_counter() - start) * 1000),
            )
        except Exception as exc:
            logger.error("[OllamaProvider] Request failed: %s", exc)
            return PlanGenerationResult(
                success=False,
                error=str(exc),
                provider=self.name,
                latency_ms=int((time.perf_counter() - start) * 1000),
            )
