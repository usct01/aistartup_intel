"""Per-domain crawl policy. Compliance is configuration, not hard-coded behavior."""

from __future__ import annotations

from datetime import time
from typing import Literal

from pydantic import BaseModel, Field

from ..models.enums import SourceTier


class SourcePolicy(BaseModel):
    """Declarative rules for how one source may be acquired."""

    source_id: str
    name: str
    base_url: str | None = None
    source_type: Literal[
        "company_site",
        "pressroom",
        "investor_portfolio",
        "rss",
        "registry",
        "filing",
        "news",
        "api",
        "web",
    ] = "web"
    tier: SourceTier = SourceTier.COMMUNITY
    enabled: bool = True
    respect_robots: bool = True
    allowed_paths: list[str] = Field(default_factory=list)
    disallowed_paths: list[str] = Field(default_factory=list)
    requests_per_second: float = 1.0
    concurrency: int = 1
    crawl_window: tuple[time, time] | None = None
    user_agent: str | None = None
    contact: str | None = None
    legal_note: str | None = None
    # When True the source is only used through its official API/feed, never HTML scraping.
    api_only: bool = False


def path_allowed(policy: SourcePolicy, path: str) -> bool:
    if policy.api_only and policy.source_type not in {"api", "rss", "filing", "registry"}:
        return False
    if policy.allowed_paths and not any(path.startswith(p) for p in policy.allowed_paths):
        return False
    return not any(path.startswith(p) for p in policy.disallowed_paths)
