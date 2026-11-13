"""Compliant fetcher.

Guarantees:
- Honors robots.txt and per-domain policy; blocked access causes a *pause*, never a bypass.
- Uses conditional requests (ETag/Last-Modified) and a content cache.
- Adaptive per-domain rate limiting with jitter and a max response size.

Never solves CAPTCHAs, authenticates, rotates IPs/proxies, or ignores rate limits.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx

from ..config.settings import Settings, get_settings
from ..store.objects import ObjectStore
from .cache import CacheEntry, ContentCache
from .policy import SourcePolicy, path_allowed
from .ratelimit import DomainRateLimiter
from .robots import RobotsCache


@dataclass
class FetchResult:
    url: str
    status: int
    content: bytes = b""
    content_type: str = "application/octet-stream"
    etag: str | None = None
    from_cache: bool = False
    paused: bool = False
    diagnostic: str | None = None
    content_uri: str | None = None
    content_hash: str | None = None

    @property
    def ok(self) -> bool:
        return self.status == 200 and not self.paused


@dataclass
class PausedDomains:
    _reasons: dict[str, str] = field(default_factory=dict)

    def pause(self, domain: str, reason: str) -> None:
        self._reasons.setdefault(domain, reason)

    def is_paused(self, domain: str) -> bool:
        return domain in self._reasons

    def reason(self, domain: str) -> str | None:
        return self._reasons.get(domain)

    def clear(self, domain: str) -> None:
        self._reasons.pop(domain, None)


class CompliantFetcher:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        client: httpx.AsyncClient | None = None,
        object_store: ObjectStore | None = None,
        cache: ContentCache | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.robots = RobotsCache(user_agent=self.settings.crawler_user_agent)
        self.limiter = DomainRateLimiter(self.settings.crawler_requests_per_second)
        self.paused = PausedDomains()
        self.object_store = object_store or ObjectStore()
        self.cache = cache or ContentCache()
        self._own_client = client is None
        self._client = client or httpx.AsyncClient(
            headers={"User-Agent": self.settings.crawler_user_agent},
            timeout=self.settings.crawler_timeout_seconds,
            follow_redirects=True,
        )

    async def __aenter__(self) -> CompliantFetcher:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._own_client:
            await self._client.aclose()

    async def fetch(self, url: str, policy: SourcePolicy) -> FetchResult:
        domain = urlparse(url).netloc
        path = urlparse(url).path or "/"

        if not policy.enabled:
            return FetchResult(url, 0, paused=True, diagnostic=f"source {policy.source_id} disabled")
        if self.paused.is_paused(domain):
            return FetchResult(
                url, 0, paused=True, diagnostic=f"domain paused: {self.paused.reason(domain)}"
            )
        if not path_allowed(policy, path):
            return FetchResult(url, 0, paused=True, diagnostic=f"path not allowed by policy: {path}")

        if policy.respect_robots and self.settings.crawler_respect_robots:
            allowed = await self.robots.can_fetch(self._client, url)
            if not allowed:
                # A robots directive is respected, not circumvented.
                return FetchResult(url, 0, paused=True, diagnostic="disallowed by robots.txt")

        await self.limiter.acquire(domain)

        cached = self.cache.get(url)
        headers: dict[str, str] = {}
        if cached and cached.etag:
            headers["If-None-Match"] = cached.etag
        if cached and cached.last_modified:
            headers["If-Modified-Since"] = cached.last_modified

        try:
            resp = await self._client.get(url, headers=headers)
        except httpx.TimeoutException:
            return FetchResult(url, 0, diagnostic="timeout")

        if resp.status_code == 304 and cached:
            try:
                content = self.object_store.get(cached.content_uri)
            except OSError:
                content = b""
            return FetchResult(
                url,
                200,
                content=content,
                content_type=cached.content_type,
                etag=cached.etag,
                from_cache=True,
                content_uri=cached.content_uri,
                content_hash=cached.content_hash,
            )

        if resp.status_code in {401, 403, 429}:
            reason = f"HTTP {resp.status_code} access control / rate limit"
            self.paused.pause(domain, reason)
            return FetchResult(url, resp.status_code, paused=True, diagnostic=reason)

        if resp.status_code >= 400:
            return FetchResult(
                url, resp.status_code, diagnostic=f"HTTP {resp.status_code} (not paused)"
            )

        content = resp.content
        if len(content) > self.settings.crawler_max_bytes:
            content = content[: self.settings.crawler_max_bytes]

        content_type = resp.headers.get("content-type", "application/octet-stream")
        uri, digest = self.object_store.put(content, suffix=".html")
        entry = CacheEntry(
            url=url,
            content_uri=uri,
            content_hash=digest,
            content_type=content_type,
            etag=resp.headers.get("etag"),
            last_modified=resp.headers.get("last-modified"),
        )
        self.cache.put(entry)
        return FetchResult(
            url,
            resp.status_code,
            content=content,
            content_type=content_type,
            etag=entry.etag,
            content_uri=uri,
            content_hash=digest,
        )

    def hash_bytes(self, content: bytes) -> str:
        return "sha256:" + hashlib.sha256(content).hexdigest()
