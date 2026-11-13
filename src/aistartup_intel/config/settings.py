"""Runtime configuration for the AI Startup Signal platform.

All settings can be overridden via environment variables prefixed with ``AISI_``
(e.g. ``AISI_OPENROUTER_API_KEY``) or a local ``.env`` file.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AISI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- application ---
    environment: str = "dev"
    log_level: str = "INFO"
    repo_root: Path = Field(default_factory=lambda: Path.cwd())

    # --- storage ---
    database_url: str = "sqlite+pysqlite:///./aistartup_intel.db"
    object_store_dir: Path = Path("./var/objects")
    redis_url: str = "redis://localhost:6379/0"

    # --- LLM gateway (OpenRouter is OpenAI-compatible) ---
    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_referer: str = "https://github.com/usct01/aistartup-intel"
    openrouter_title: str = "AI Startup Signal"
    llm_offline: bool = True  # when True, use deterministic mock model (no network)
    llm_timeout_seconds: float = 60.0
    llm_max_retries: int = 3

    # --- model routing policy (per task role) ---
    model_planner: str = "openai/gpt-4o"
    model_extractor: str = "google/gemini-2.0-flash-001"
    model_verifier: str = "anthropic/claude-3.5-sonnet"  # different family than extractor
    model_classifier_bulk: str = "deepseek/deepseek-chat"
    model_classifier_hard: str = "openai/gpt-4o"
    model_analyst: str = "anthropic/claude-3.5-sonnet"
    model_editor: str = "anthropic/claude-3.5-sonnet"
    model_evaluator: str = "openai/gpt-4o-mini"

    # --- product rules ---
    funding_threshold_usd: int = 10_000_000
    initial_verticals: list[str] = Field(
        default_factory=lambda: ["healthcare", "legal", "finance"]
    )
    auto_publish_confidence: float = 0.75
    quarantine_confidence: float = 0.45

    # --- budget guards ---
    daily_spend_cap_usd: float = 25.0
    per_agent_token_budget: int = 20_000

    # --- crawler ---
    crawler_user_agent: str = (
        "AISIResearchBot/0.1 (+https://github.com/usct01/aistartup-intel; contact@example.com)"
    )
    crawler_requests_per_second: float = 1.0
    crawler_respect_robots: bool = True
    crawler_max_bytes: int = 5_000_000
    crawler_timeout_seconds: float = 20.0

    @property
    def objects_path(self) -> Path:
        p = self.object_store_dir
        if not p.is_absolute():
            p = self.repo_root / p
        return p


@lru_cache
def get_settings() -> Settings:
    return Settings()
