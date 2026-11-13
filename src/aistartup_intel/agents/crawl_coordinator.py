"""Crawl Coordinator agent.

Deterministic-first: it enforces source policy, respects robots, uses the
rate-limited fetcher, and records diagnostics. It never bypasses access controls.
LLMs are used only for exceptions (not implemented here).
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from urllib.parse import urlparse

from ..crawler.policy import SourcePolicy
from ..crawler.registry import SourceRegistry
from ..models.agent_io import CrawlDocument, CrawlResult, DiscoveryResult, SourceCandidate
from .base import Agent, PipelineContext

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def html_to_text(html: str) -> str:
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(" ")
    except Exception:  # noqa: BLE001 - fall back to regex stripping
        text = _TAG.sub(" ", html)
    return _WS.sub(" ", text).strip()


class CrawlCoordinator(Agent[DiscoveryResult, CrawlResult]):
    name = "crawl-coordinator"
    model_role = "extractor"  # only used for exceptions; logic is deterministic
    description = "Applies source policy, fetches with caching, and emits diagnostics."

    async def handle(self, ctx: PipelineContext, payload: DiscoveryResult) -> CrawlResult:
        documents: list[CrawlDocument] = []
        paused: list[str] = []
        diagnostics: list[str] = list(payload.diagnostics)
        fetcher = ctx.fetcher
        registry = ctx.registry
        if fetcher is None or registry is None:
            return CrawlResult(diagnostics=["crawl coordinator missing fetcher/registry"])

        for candidate in payload.candidates:
            policy = _resolve_policy(candidate, registry)
            if policy is None:
                diagnostics.append(f"unregistered source skipped: {candidate.url}")
                continue
            if not policy.enabled:
                diagnostics.append(f"disabled source skipped: {policy.source_id}")
                continue
            result = await fetcher.fetch(candidate.url, policy)
            if result.paused or not result.ok:
                paused.append(policy.source_id)
                diagnostics.append(f"{policy.source_id}: {result.diagnostic}")
                continue
            text = result.content.decode("utf-8", errors="replace")
            if "html" in result.content_type:
                text = html_to_text(text)
            documents.append(
                CrawlDocument(
                    uri=result.content_uri or candidate.url,
                    url=candidate.url,
                    content_type=result.content_type,
                    text=text,
                    fetched_at=_now(),
                    from_cache=result.from_cache,
                    http_status=result.status,
                )
            )
        return CrawlResult(documents=documents, paused_sources=paused, diagnostics=diagnostics)


def _resolve_policy(candidate: SourceCandidate, registry: SourceRegistry) -> SourcePolicy | None:
    host = urlparse(candidate.url).netloc
    for policy in registry.all():
        if not policy.base_url:
            continue
        if urlparse(policy.base_url).netloc == host:
            return policy
    return None


def _now() -> datetime:
    return datetime.now(UTC)
