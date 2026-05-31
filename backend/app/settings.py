from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_list(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    if value is None:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_format: str = os.getenv("LOG_FORMAT", "plain").strip().lower()
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./research_os.db")
    cors_allow_origins: list[str] = field(
        default_factory=lambda: _get_list(
            "CORS_ALLOW_ORIGINS",
            ["http://localhost:3000", "http://127.0.0.1:3000"],
        )
    )
    paper_discovery_provider: str = os.getenv("PAPER_DISCOVERY_PROVIDER", "mock").strip().lower()
    paper_discovery_allow_fallback: bool = _get_bool("PAPER_DISCOVERY_ALLOW_FALLBACK", True)
    paper_discovery_timeout_seconds: int = _get_int("PAPER_DISCOVERY_TIMEOUT_SECONDS", 20)
    paper_search_limit: int = _get_int("PAPER_SEARCH_LIMIT", 8)
    extraction_provider: str = os.getenv("EXTRACTION_PROVIDER", "mock").strip().lower()
    extraction_allow_fallback: bool = _get_bool("EXTRACTION_ALLOW_FALLBACK", True)
    scheduler_enabled: bool = _get_bool("SCHEDULER_ENABLED", True)
    scheduler_poll_seconds: int = _get_int("SCHEDULER_POLL_SECONDS", 60)
    digest_window_days: int = _get_int("DIGEST_WINDOW_DAYS", 7)
    database_migration_mode: str = os.getenv("DATABASE_MIGRATION_MODE", "hybrid").strip().lower()
    obsidian_export_dir: str = os.getenv("OBSIDIAN_EXPORT_DIR", "Research OS").strip()
    obsidian_export_root: str = os.getenv("OBSIDIAN_EXPORT_ROOT", "").strip()
    smtp_host: str = os.getenv("SMTP_HOST", "").strip()
    smtp_port: int = _get_int("SMTP_PORT", 587)
    smtp_username: str = os.getenv("SMTP_USERNAME", "").strip()
    smtp_password: str = os.getenv("SMTP_PASSWORD", "").strip()
    smtp_from_email: str = os.getenv("SMTP_FROM_EMAIL", "").strip()
    smtp_to_emails: list[str] = field(default_factory=lambda: _get_list("SMTP_TO_EMAILS", []))
    smtp_use_tls: bool = _get_bool("SMTP_USE_TLS", True)
    smtp_use_ssl: bool = _get_bool("SMTP_USE_SSL", False)
    digest_webhook_url: str = os.getenv("DIGEST_WEBHOOK_URL", "").strip()
    digest_webhook_timeout_seconds: int = _get_int("DIGEST_WEBHOOK_TIMEOUT_SECONDS", 15)
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "").strip()
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    openalex_email: str = os.getenv("OPENALEX_EMAIL", "").strip()

    def validate(self) -> None:
        if self.paper_discovery_provider not in {"mock", "openalex", "arxiv"}:
            raise ValueError("PAPER_DISCOVERY_PROVIDER must be one of: mock, openalex, arxiv")
        if self.extraction_provider not in {"mock", "llm"}:
            raise ValueError("EXTRACTION_PROVIDER must be one of: mock, llm")
        if self.database_migration_mode not in {"lightweight", "alembic", "hybrid"}:
            raise ValueError("DATABASE_MIGRATION_MODE must be one of: lightweight, alembic, hybrid")
        if self.extraction_provider == "llm" and not self.openai_api_key and not self.extraction_allow_fallback:
            raise ValueError("OPENAI_API_KEY is required when EXTRACTION_PROVIDER=llm and EXTRACTION_ALLOW_FALLBACK=false")
        if not self.database_url:
            raise ValueError("DATABASE_URL must not be empty")
        if self.scheduler_poll_seconds < 5:
            raise ValueError("SCHEDULER_POLL_SECONDS must be at least 5")
        if self.digest_window_days < 1 or self.digest_window_days > 30:
            raise ValueError("DIGEST_WINDOW_DAYS must be between 1 and 30")
        if self.smtp_use_ssl and self.smtp_use_tls:
            raise ValueError("SMTP_USE_TLS and SMTP_USE_SSL cannot both be true")
        if not self.obsidian_export_dir:
            raise ValueError("OBSIDIAN_EXPORT_DIR must not be empty")


settings = Settings()
