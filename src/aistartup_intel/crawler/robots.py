"""robots.txt fetching, caching, and evaluation.

Failure handling: a missing robots.txt (404) is treated as allow; a server error
is treated conservatively as disallow for that host.
"""

from __future__ import annotations

import time
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx


class RobotsCache:
    def __init__(self, *, user_agent: str, ttl_seconds: float = 3600.0) -> None:
        self.user_agent = user_agent
        self.ttl = ttl_seconds
        self._cache: dict[str, tuple[float, RobotFileParser | None]] = {}

    async def _load(self, client: httpx.AsyncClient, scheme: str, host: str) -> RobotFileParser | None:
        url = f"{scheme}://{host}/robots.txt"
        try:
            resp = await client.get(url, follow_redirects=True)
        except httpx.HTTPError:
            return None  # unreachable -> conservative None handled by caller
        parser = RobotFileParser()
        if resp.status_code == 200:
            parser.parse(resp.text.splitlines())
            return parser
        if resp.status_code in {404, 410}:
            parser.allow_all = True  # type: ignore[attr-defined]
            return parser
        if resp.status_code >= 500:
            return None
        parser.allow_all = True  # type: ignore[attr-defined]
        return parser

    async def can_fetch(self, client: httpx.AsyncClient, url: str) -> bool:
        parsed = urlparse(url)
        host = parsed.netloc
        now = time.monotonic()
        cached = self._cache.get(host)
        if cached is None or now - cached[0] > self.ttl:
            parser = await self._load(client, parsed.scheme, host)
            self._cache[host] = (now, parser)
        else:
            parser = cached[1]
        if parser is None:
            return False  # server error / unreachable robots -> do not crawl
        if getattr(parser, "allow_all", False):
            return True
        return parser.can_fetch(self.user_agent, url)

    def robots_url(self, url: str) -> str:
        parsed = urlparse(url)
        return urljoin(f"{parsed.scheme}://{parsed.netloc}", "/robots.txt")
