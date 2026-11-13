"""Compliant acquisition: policy, robots, rate limiting, caching, fetching."""

from .cache import CacheEntry, ContentCache
from .fetcher import CompliantFetcher, FetchResult, PausedDomains
from .policy import SourcePolicy, path_allowed
from .ratelimit import DomainRateLimiter
from .registry import SourceRegistry
from .robots import RobotsCache

__all__ = [
    "CacheEntry",
    "CompliantFetcher",
    "ContentCache",
    "DomainRateLimiter",
    "FetchResult",
    "PausedDomains",
    "RobotsCache",
    "SourcePolicy",
    "SourceRegistry",
    "path_allowed",
]
