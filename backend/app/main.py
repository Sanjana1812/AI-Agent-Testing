from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import run

STORAGE_PATH = Path(__file__).resolve().parent.parent / "storage"
STORAGE_PATH.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="AI Testing Platform API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(run.router)


@app.get("/")
def root():
    return {
        "name": "AI Testing Platform API",
        "docs": "/docs",
        "health": "/health",
        "run": "POST /run",
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}


app.mount("/storage", StaticFiles(directory=str(STORAGE_PATH)), name="storage")