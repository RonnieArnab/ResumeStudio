from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# .env lives at the repo root (docker-compose and the README both reference
# it there), not backend/ — resolve it relative to this file so it loads
# regardless of the process's cwd.
REPO_ROOT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT_ENV_FILE, extra="ignore")

    app_name: str = "resume-editor-agent"
    environment: str = "development"
    cors_origins: list[str] = ["http://localhost:5173"]

    openai_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
