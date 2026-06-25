from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql://postgres:postgres@localhost:5432/ai_testing_platform"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    model_name: str = "llama3"
    ollama_base_url: str = "http://localhost:11434"
    ollama_timeout_seconds: int = 20


settings = Settings()
