from fastapi import APIRouter

from app.config import settings
from app.services.ollama_health import is_ollama_available

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/health")
async def system_health():
    ollama_connected = await is_ollama_available()

    return {
        "backend": "ok",
        "ollama": "connected" if ollama_connected else "disconnected",
        "model": settings.model_name,
        "planner": "active" if ollama_connected else "fallback",
    }
