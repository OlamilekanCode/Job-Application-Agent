from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Job Application Agent"
    environment: str = "local"
    host: str = "127.0.0.1"
    port: int = 8010
    database_url: str = "sqlite:///data/job_application_agent.db"
    log_level: str = "INFO"
    worker_poll_seconds: float = 2.0
    task_lease_seconds: int = 60
    playwright_profile_dir: Path = Path("data/browser-profile")
    codex_model: str | None = None
    codex_smoke_timeout_seconds: int = 120
    service_bind_lan: bool = False
    automation_mode: str = "prepare"
    final_submission_requires_approval: bool = True

    model_config = SettingsConfigDict(
        env_prefix="JAA_",
        env_file=".env",
        extra="ignore",
    )

    @field_validator("host")
    @classmethod
    def localhost_by_default(cls, value: str) -> str:
        if value not in {"127.0.0.1", "localhost"}:
            raise ValueError("Phase 1 service must bind to localhost unless explicitly redesigned.")
        return value

    @field_validator("automation_mode")
    @classmethod
    def phase_one_prepare_only(cls, value: str) -> str:
        allowed = {"observe", "prepare"}
        if value not in allowed:
            raise ValueError(f"Phase 1 automation mode must be one of {sorted(allowed)}.")
        return value

    @field_validator("final_submission_requires_approval")
    @classmethod
    def require_manual_submission_approval(cls, value: bool) -> bool:
        if not value:
            raise ValueError("Phase 1 requires manual approval for any future submission path.")
        return value

    @property
    def database_path(self) -> Path | None:
        prefix = "sqlite:///"
        if self.database_url.startswith(prefix):
            return Path(self.database_url.removeprefix(prefix))
        return None

    def ensure_local_paths(self) -> None:
        database_path = self.database_path
        if database_path is not None:
            database_path.parent.mkdir(parents=True, exist_ok=True)
        self.playwright_profile_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_local_paths()
    return settings

