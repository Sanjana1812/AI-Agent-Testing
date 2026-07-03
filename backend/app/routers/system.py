from fastapi import APIRouter

from app.config import settings
from app.services.ollama_health import is_ollama_available
from app.services.playwright_bootstrap import ensure_playwright_browsers

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/health")
async def system_health():
    ollama_connected = await is_ollama_available()
    playwright_ready = ensure_playwright_browsers()

    return {
        "backend": "ok",
        "ollama": "connected" if ollama_connected else "disconnected",
        "playwright": "ready" if playwright_ready else "missing",
        "model": settings.model_name,
        "planner": "active" if ollama_connected else "fallback",
    }
