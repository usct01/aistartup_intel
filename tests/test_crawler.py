from __future__ import annotations

import httpx

from aistartup_intel.config.settings import Settings
from aistartup_intel.crawler.cache import ContentCache
from aistartup_intel.crawler.fetcher import CompliantFetcher
from aistartup_intel.crawler.policy import SourcePolicy, path_allowed
from aistartup_intel.store.objects import ObjectStore


def _handler(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if "noindex.example" in url and url.endswith("/robots.txt"):
        return httpx.Response(200, text="User-agent: *\nDisallow: /")
    if url.endswith("/robots.txt"):
        return httpx.Response(200, text="User-agent: *\nAllow: /")
    if "blocked.example" in url:
        return httpx.Response(403, text="forbidden")
    if "example.com/page" in url:
        if request.headers.get("if-none-match") == "v1":
            return httpx.Response(304)
        return httpx.Response(
            200,
            text="<html><body>Hello</body></html>",
            headers={"etag": "v1", "content-type": "text/html"},
        )
    return httpx.Response(404)


def _fetcher(tmp_path, settings: Settings) -> CompliantFetcher:
    client = httpx.AsyncClient(transport=httpx.MockTransport(_handler))
    return CompliantFetcher(
        settings=settings,
        client=client,
        object_store=ObjectStore(root=tmp_path / "objects"),
        cache=ContentCache(index_path=tmp_path / "cache.json"),
    )


def _policy(source_id: str, base_url: str, **kw) -> SourcePolicy:
    return SourcePolicy(source_id=source_id, name=source_id, base_url=base_url, **kw)


def test_path_allowed_and_api_only():
    p = SourcePolicy(source_id="s", name="s", source_type="web", api_only=True)
    assert path_allowed(p, "/anything") is False
    p2 = SourcePolicy(source_id="s", name="s", source_type="api", api_only=True)
    assert path_allowed(p2, "/v1/search") is True
    p3 = SourcePolicy(source_id="s", name="s", disallowed_paths=["/private"])
    assert path_allowed(p3, "/private/x") is False
    assert path_allowed(p3, "/public") is True


async def test_fetch_then_conditional_cache(tmp_path):
    settings = Settings(crawler_requests_per_second=1000)
    fetcher = _fetcher(tmp_path, settings)
    policy = _policy("example", "https://example.com")
    first = await fetcher.fetch("https://example.com/page", policy)
    assert first.ok and not first.from_cache
    assert b"Hello" in first.content
    second = await fetcher.fetch("https://example.com/page", policy)
    assert second.ok and second.from_cache
    await fetcher.aclose()


async def test_forbidden_pauses_domain(tmp_path):
    settings = Settings(crawler_requests_per_second=1000)
    fetcher = _fetcher(tmp_path, settings)
    policy = _policy("blocked", "https://blocked.example")
    result = await fetcher.fetch("https://blocked.example/index", policy)
    assert result.paused
    assert fetcher.paused.is_paused("blocked.example")
    again = await fetcher.fetch("https://blocked.example/other", policy)
    assert again.paused
    await fetcher.aclose()


async def test_robots_disallow_causes_pause(tmp_path):
    settings = Settings(crawler_requests_per_second=1000, crawler_respect_robots=True)
    fetcher = _fetcher(tmp_path, settings)
    policy = _policy("noindex", "https://noindex.example")
    result = await fetcher.fetch("https://noindex.example/page", policy)
    assert result.paused
    assert "robots" in (result.diagnostic or "")
    await fetcher.aclose()
