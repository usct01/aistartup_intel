# AI Startup Signal

[![CI](https://github.com)](https://github.com)


Multi-agent intelligence platform that discovers AI startups and funding activity,
verifies every material fact against retained evidence, classifies companies against a
multi-label AI taxonomy, ranks momentum, and produces a personalized daily newsletter.

Design and plan: [`docs/final-design.md`](docs/final-design.md).

## Status

Implementable foundation (Phase 1) plus a working vertical slice of Phase 2. The full
pipeline runs **offline and deterministically** with no API key; OpenRouter and Google ADK
are wired behind clean interfaces and activate when configured.

## Architecture

```
connectors/crawler -> Event (Redis-Streams-shaped) -> Orchestrator (agent DAG)
  extract -> resolve company -> funding -> taxonomy -> signals -> verify -> score
      -> publish (append-only ledger) | quarantine (human review)
  PostgreSQL/SQLite + object store + provenance ledger + run manifests
  FastAPI: companies, funding, events, review queue, newsletter preview
```

Agents: Research Planner, Source Discovery, Crawl Coordinator, Document Extractor,
Funding Analyst, Entity Resolver, Taxonomy Classifier, Signal Analyst, Verifier,
Newsletter Editor, Quality Evaluator, Human Review Queue, plus a deterministic Scoring
service. Role contracts live in [`skills/`](skills/).

## Quick start

```bash
uv sync                       # install (Python 3.13)
uv run aistartup-intel demo   # offline end-to-end demo (no network, no API key)
uv run aistartup-intel serve  # FastAPI at http://127.0.0.1:8000 (docs at /docs)
```

## Commands

| Command | Purpose |
| --- | --- |
| `aistartup-intel init-db` | Create the schema (idempotent) |
| `aistartup-intel demo` | Run sample filings through the full pipeline |
| `aistartup-intel ingest <file.json>` | Ingest Form D-like records |
| `aistartup-intel reviews` | List the human review queue |
| `aistartup-intel serve` | Run the API |

## Configuration

All settings use the `AISI_` env prefix (or a `.env` file). Key ones:

- `AISI_DATABASE_URL` (default SQLite; use `postgresql+psycopg://...` in prod)
- `AISI_LLM_OFFLINE` (default `true`; set `false` + `AISI_OPENROUTER_API_KEY` to go live)
- `AISI_OPENROUTER_API_KEY`, `AISI_MODEL_*` (per-role model routing)
- `AISI_FUNDING_THRESHOLD_USD` (default 10,000,000)
- `AISI_CRAWLER_RESPECT_ROBOTS`, `AISI_CRAWLER_REQUESTS_PER_SECOND`

## Guarantees

- **Provenance by construction** — every claim carries a verbatim evidence span; spans not
  present in the source are rejected.
- **Append-only ledger** — no fact is overwritten; conflicting claims coexist.
- **Verifier anti-correlation** — the Verifier uses a different model family than the
  Extractor.
- **Compliant crawling** — robots/terms/rate limits are honored; blocked access pauses a
  source, never bypasses it (no CAPTCHA solving, auth, or IP rotation).
- **Replayable** — every run writes a manifest (agents, models, cost, decisions).

## Development

```bash
uv run pytest          # 39 tests
uv run ruff check src tests
uv run mypy src
```

## Layout

```
src/aistartup_intel/
  config/   settings + source registry (sources.yaml)
  models/   events, domain, agent IO, scoring
  store/    SQLAlchemy tables, repository, ledger, object store
  crawler/  policy, robots, rate limiting, cache, compliant fetcher
  connectors/  sec_form_d, rss, static
  agents/   the agent roster + orchestrator
  scoring/  deterministic momentum service
  api/      FastAPI app
  llm/      OpenRouter gateway + offline mock
  tools/    deterministic evidence extractors
  eval/     (evaluation harness; see tests)
skills/     role contracts + shared references
```
