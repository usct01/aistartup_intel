# Crawl Coordinator

## Mission and boundaries

Acquire permitted web content compliantly and reliably. The Crawl Coordinator enforces source
policy, caches content, detects change, schedules retries, and emits diagnostics. It produces
retained documents and events; it does not interpret them.

- **In scope:** policy-driven fetching, caching, conditional requests, change detection,
  rate limiting, deduplication, and source-health diagnostics.
- **Out of scope:** extraction of meaning, classification, verification, and scoring.

## Deterministic-first policy

The Crawl Coordinator is **deterministic Python first**; an LLM is used **only for exception
handling** (for example, interpreting an unfamiliar markup change into a diagnostic), never to
decide policy dynamically. Given identical inputs and policies, it must behave identically.

## Allowed tools and source types

- HTTP fetchers with per-domain policies; RSS/Atom parsers; sitemap readers; conditional
  GET with `ETag`/`Last-Modified`; the crawl cache and raw-document store.
- Source types: company sites, pressrooms, investor portfolios, RSS/Atom, public registries,
  regulatory filings, research repositories, licensed providers.
- Preferred model policy: **Deterministic Python**, LLM only for exceptions.

## Hard compliance rules (never violate)

- **Never bypass CAPTCHAs, authentication, robots directives, rate limits, or any access
  control.**
- **Never use IP rotation or proxy rotation** to evade a site's blocking policy. There is no
  "resilience" exception that permits access-control bypass.
- On `403`, `429`, anti-bot challenge, auth prompt, or major markup change: **pause the source
  and emit a diagnostic** — do not retry around the block.
- Respect per-domain allowed paths, crawl budget, time windows, concurrency, and user agent.
- For blocked high-value sources, prefer licensed data, publisher APIs, explicit
  authorisation, customer-provided access, or alternate reputable sources.

## Required input/output schemas

- **Input:** `SourceCandidate` (from Source Discovery) and per-domain policy.
- **Output:** `CrawlResult` (`agent_io.py`) with `CrawlDocument` items (`uri`, `url`,
  `content_type`, `text`, `fetched_at`, `from_cache`, `http_status`), plus `paused_sources`
  and `diagnostics`.

## Decision rules and confidence thresholds

- Serve from cache when content hash is unchanged; set `from_cache = true`.
- Coalesce concurrent requests to the same URL; use exponential backoff with jitter on
  transient errors only.
- Deduplicate documents by canonical URL and `content_hash`.
- Track source health, freshness, extraction quality, access status, and legal notes.
- A paused source stays paused until a human or policy change clears it.

## Failure handling and escalation paths

- Transient network error: bounded retry with backoff; then diagnostic.
- Persistent `403`/`429`/anti-bot: pause + diagnostic + recommend authorised alternative.
- Major markup change: emit diagnostic; do not guess a new parser silently.
- Any request to bypass protections must be refused and escalated.

## Examples

Valid:

```json
{"documents": [{"uri": "s3://raw/acme/1.html", "url": "https://acme.ai/press",
  "content_type": "text/html", "text": "...", "fetched_at": "2026-10-16T00:00:00Z",
  "from_cache": false, "http_status": 200}], "paused_sources": [], "diagnostics": []}
```

Invalid:

```json
{"documents": [], "paused_sources": [], "diagnostics": ["rotated proxy to bypass 403"]}
```

Reason: IP-rotation bypass is prohibited; a 403 must pause the source and recommend an
authorised alternative instead.
