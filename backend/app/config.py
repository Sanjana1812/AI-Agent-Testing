from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_SQLITE_PATH = _BACKEND_ROOT / "storage" / "ai_testing_platform.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = f"sqlite:///{_DEFAULT_SQLITE_PATH.as_posix()}"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    model_name: str = "llama3"
    ollama_base_url: str = "http://localhost:11434"
    ollama_timeout_seconds: int = 60


settings = Settings()
