# Handoff 1 — AI Startup Signal (`aistartup_intel`)

> Session handoff for the next agent/engineer. Read this top-to-bottom before changing code.
> It captures architecture, exact current state, how to run/verify, gotchas, and the recommended
> next steps. Last updated: 2026-10-16.

---

## 1. What this project is

**AI Startup Signal** — an investor-first, multi-agent intelligence platform that:

1. Discovers AI startups and funding activity from public sources (SEC Form D, RSS, static pages).
2. Extracts and **verifies every material fact against retained evidence** (verbatim evidence spans).
3. Classifies companies against a multi-label AI taxonomy (topic / subtopic / buyer / maturity).
4. Ranks momentum deterministically.
5. Produces a **personalized daily newsletter**.
6. Exposes everything via a FastAPI backend + a **Next.js frontend** (topic/subtopic explorer,
   startup detail, newsletter briefing preview/editor).

Design docs (authoritative):
- `docs/final-design.md` — **approved spec, supersedes the others.** Read this first.
- `docs/design.md` — earlier design doc.
- `PLANV1.md` — most detailed product/taxonomy/agent spec (taxonomy lists, agent roster, rules).
- `README.md` — short overview + commands.
- `skills/` — per-agent role contracts (SKILL.md files) + `skills/common/`.

### Core product rules
- **Funding gate:** only total *disclosed* funding strictly `> USD 10,000,000` qualifies.
  Undisclosed/estimated amounts are excluded.
- **Provenance by construction:** no claim without a verbatim evidence span present in the source.
- **Append-only ledger:** facts are never overwritten; conflicting claims coexist.
- **Verifier anti-correlation:** the Verifier uses a *different* model family than the Extractor.
- **Compliant crawling:** robots/terms/rate limits honored; blocked access pauses a source, never
  bypasses it (no CAPTCHA solving, auth, or IP rotation).
- **Replayable:** every pipeline run writes a manifest (agents, models, cost, decisions).

---

## 2. Current status snapshot

- Backend: full **Phase 1 foundation** + a working **vertical slice of Phase 2**, running
  **offline and deterministically** (`AISI_LLM_OFFLINE=true`, no API key, no network).
- Frontend: **Next.js 16 + React 19 + TypeScript** app in `web/`, wired to the API.
- Verification is **green**:
  - `uv run pytest` → **39 tests pass**
  - `uv run ruff check src tests` → **All checks passed**
  - `uv run mypy src` → **Success: no issues found in 50 source files** (strict)
  - `web`: `npm run build` → compiles (`/`, `/briefing`)
- **Git: repo has NO commits yet** (`master`, all files untracked). Nothing has been committed.
  Do **not** commit unless the user explicitly asks.

### What was just added this session (frontend + supporting API)
- Backend API additions (in `src/aistartup_intel/api/app.py`):
  - `GET /taxonomy` — topics/subtopics/etc. with company counts, grouped by axis.
  - `GET /stats` — `{companies, pending_reviews, subscribers}`.
  - Extended `GET /companies` with `vertical`, `capability`, `buyer`, `q`, `min_total_funding_usd`
    filters (and `description` in the response).
  - `POST /newsletter/subscribe` (idempotent create/update) and `GET /newsletter/subscription?email=`.
  - CORS middleware (`allow_origins=["*"]`) so the separate Next.js dev/start origin can call it.
- Repository additions (`src/aistartup_intel/store/repository.py`):
  `list_taxonomy`, extended `list_companies` (capability/buyer/q), `get_user_by_email`, `create_user`,
  `add_subscription`, `get_subscription`, `list_subscribers`.
- Frontend (`web/`) — see §7.

---

## 3. How to run (local)

### Backend (Python 3.13, `uv`)
```bash
uv sync                              # install deps
uv run aistartup-intel demo          # offline end-to-end demo -> populates ./aistartup_intel.db
uv run aistartup-intel serve         # FastAPI at http://127.0.0.1:8000 (docs at /docs)
# or directly, explicit host/port:
uv run uvicorn aistartup_intel.api.app:app --host 127.0.0.1 --port 8000
```

### Frontend (`web/`)
```bash
cd web
npm install
npm run dev            # dev server http://localhost:3000
# or production:
npm run build && npm start
```
Config: `NEXT_PUBLIC_API_BASE` (defaults to `http://127.0.0.1:8000`). Put it in `web/.env.local` if
the API runs elsewhere.

### Sessions currently running (may not persist — verify before relying)
- API: `uvicorn` on `http://127.0.0.1:8000` (log: `/tmp/opencode/aisi-api.log`).
- Web: `next` on `http://127.0.0.1:3000` (log: `/tmp/opencode/aisi-web.log`).
- The demo DB `./aistartup_intel.db` contains 4 companies, 5 pending reviews, and 1 test subscriber
  (`jane@fund.com`) created during endpoint smoke tests.

---

## 4. Architecture

```
connectors/crawler -> Event (Redis-Streams-shaped) -> Orchestrator (agent DAG)
  extract -> resolve company -> funding -> taxonomy -> signals -> verify -> score
      -> publish (append-only ledger) | quarantine (human review)
  PostgreSQL/SQLite + object store + provenance ledger + run manifests
  FastAPI: companies, funding, events, review queue, newsletter preview/subscribe
  Next.js UI: explorer (topics/subtopics) + briefing (newsletter preview/editor)
```

Agent roster (`src/aistartup_intel/agents/`): Research Planner (`research.py`), Source Discovery,
Crawl Coordinator (`crawl_coordinator.py`), Document Extractor (`extraction.py`), Funding Analyst
(`funding.py`), Entity Resolver (`entity_resolution.py`), Taxonomy Classifier (`taxonomy.py`),
Signal Analyst (`signals.py`), Verifier (`verifier.py`), Newsletter Editor (`newsletter.py`),
Quality Evaluator (`evaluator.py`), Human Review Queue (`review.py`), Orchestrator
(`orchestrator.py`), plus a deterministic Scoring service (`scoring/service.py`).
Shared base + `PipelineContext` live in `agents/base.py`.

---

## 5. Repo layout

```
src/aistartup_intel/
  config/     settings.py (Settings, AISI_ prefix) + sources.yaml registry
  models/     events.py, domain.py, agent_io.py, scoring.py, enums.py
  store/      db.py, tables.py, repository.py, objects.py (object store)
  crawler/    policy.py, robots.py, ratelimit.py, cache.py, fetcher.py, registry.py
  connectors/ sec_form_d.py, rss.py, static.py, base.py
  agents/     roster + orchestrator.py
  scoring/    service.py (deterministic momentum)
  api/        app.py (FastAPI)
  llm/        base.py, gateway.py, mock.py (offline), openrouter.py, pricing.py
  tools/      text_extract.py (deterministic evidence extractors)
  demo.py     SAMPLE_FILINGS + run_demo()
  cli.py      Typer CLI (entrypoint: cli:main -> `aistartup-intel`)
skills/       per-agent role contracts + common/ references
docs/         design.md, final-design.md
PLANV1.md     full product/agent/taxonomy spec
web/          Next.js frontend (see §7)
tests/        12 files, 39 tests
```

### Key config (`src/aistartup_intel/config/settings.py`)
- `AISI_` env prefix (+ optional `.env`).
- `database_url` default `sqlite+pysqlite:///./aistartup_intel.db`; prod `postgresql+psycopg://...`.
- `llm_offline=True` default (deterministic mock; set `false` + `AISI_OPENROUTER_API_KEY` to go live).
- Per-role model routing: `model_planner/extractor/verifier/classifier_bulk/classifier_hard/analyst/editor/evaluator`.
- `funding_threshold_usd=10_000_000`, `initial_verticals=["healthcare","legal","finance"]`,
  `auto_publish_confidence=0.75`, `quarantine_confidence=0.45`.
- Budget guards: `daily_spend_cap_usd`, `per_agent_token_budget`.
- Crawler: `crawler_requests_per_second`, `crawler_respect_robots`, `crawler_max_bytes`, etc.

---

## 6. Backend reference

### CLI (`src/aistartup_intel/cli.py`, entrypoint `aistartup-intel`)
| Command | Purpose |
| --- | --- |
| `init-db` | Create schema (idempotent) |
| `demo` | Run sample filings through the full pipeline |
| `ingest <file.json>` | Ingest Form D-like records |
| `reviews` | List the human review queue |
| `serve` | Run the API (`uvicorn`, port 8000) |

### API routes (`src/aistartup_intel/api/app.py`, base `http://127.0.0.1:8000`)
| Method | Path | Notes |
| --- | --- | --- |
| GET | `/health` | `{status, environment}` |
| GET | `/taxonomy` | `?axis=` optional; `{axes: {vertical:[{label,count}], capability:[...], buyer:[...], maturity:[...]}}` |
| GET | `/stats` | `{companies, pending_reviews, subscribers}` |
| GET | `/companies` | filters: `min_total_funding_usd, vertical, capability, buyer, q, limit(<=200), offset` → `{count, companies:[{id,name,url,hq,description,total_disclosed_funding_usd,confidence,is_new}]}` |
| GET | `/companies/{id}` | detail: `funding_rounds`, `taxonomy:[{axis,label,confidence}]`, `ledger:[{action,type,at}]` |
| GET | `/funding` | `?min_amount_usd=&company_id=` |
| GET | `/events` | `?kind=&unprocessed_only=&limit=` |
| GET | `/review` | `?status=pending` |
| POST | `/review/{id}/resolve` | `?status=approved|rejected&resolver=&note=` |
| GET | `/runs/{run_id}` | run manifest (agents, cost, tokens, decisions, replayable) |
| POST | `/newsletter/preview` | query params `verticals` (repeatable) + `min_funding_usd` → `NewsletterDraft` |
| POST | `/newsletter/subscribe` | body `SubscribeRequest` (201, idempotent) |
| GET | `/newsletter/subscription` | `?email=` → subscription or 404 |

### Newsletter IO (`src/aistartup_intel/models/agent_io.py`)
- `NewsletterItem`: `company, headline, body, confidence, evidence_urls[], score?`
- `NewsletterInput`: `user_email, verticals[], categories[], min_funding_usd, items[], edition_date?`
- `NewsletterDraft`: `subject, vertical_pulse: dict[str,str], items: NewsletterItem[], generated_at?`
- `NewsletterEditor.handle` (async, `agents/newsletter.py`): keeps items with `confidence >= 0.5`
  **and** non-empty `evidence_urls`, sorts by `(score, confidence)` desc, caps at **8**.

### Storage (`src/aistartup_intel/store/`)
- `tables.py`: ORM incl. `CompanyRow`, `FundingRoundRow`, `TaxonomyTagRow`, `UserRow`,
  `SubscriptionRow`, `WatchlistRow`, plus ledger/run/event/review tables.
- `repository.py`: query + persistence layer used by API/CLI/agents.
- `objects.py`: content-addressed object store (`var/objects`) holding retained evidence.

---

## 7. Frontend reference (`web/`)

Stack: **Next.js 16.4.2 (App Router, Turbopack) + React 19 + TypeScript**. Plain CSS in
`app/globals.css` (dark theme, no Tailwind). Path alias `@/*` → `web/*`.

### Routes
- `web/app/layout.tsx` (root), `web/app/globals.css` (all styles), `web/app/page.tsx` (Explore),
  `web/app/briefing/page.tsx` (Briefing).

### Components (`web/components/`)
- `Header.tsx` — brand (links `/`), nav **Explore | Briefing**, optional search box, live stats,
  optional Subscribe button. Props: `stats, active?, query?, onQuery?, onSubscribe?`.
- `TopicSidebar.tsx` — topic/subtopic/buyer chips from taxonomy + `>$10M` gate + clear filters.
- `CompanyCard.tsx` — company card (funding, description, hq, confidence, "New" badge).
- `CompanyDrawer.tsx` — detail drawer (rounds, taxonomy, append-only ledger).
- `SubscribeModal.tsx` — email/name + topic/subtopic chips + min funding → `POST /newsletter/subscribe`.

### Lib (`web/lib/`)
- `api.ts` — typed client. `API_BASE` from `NEXT_PUBLIC_API_BASE` (default `http://127.0.0.1:8000`).
  Types: `Taxonomy, Company, CompanyDetail, FundingRound, Stats, NewsletterItem, NewsletterDraft`.
  Functions: `getTaxonomy, getStats, getCompanies, getCompany, getSubscription, subscribe,
  previewNewsletter`. Uses `fetch(..., {cache:"no-store"})`.
- `format.ts` — `formatUsd, titleCase, formatDate, relativeTime`.
- `newsletter.ts` — `itemHeadline, draftToText, draftToMarkdown`.

### Explore page behavior
Loads taxonomy+stats on mount; fetches `/companies` on filter/search change (250ms debounce on
query); topic/subtopic/buyer chips toggle filters; grid + drawer; subscribe modal (refreshes stats).

### Briefing page behavior
Select topics + funding gate → `previewNewsletter()` → toggle **Preview** (email-client rendering:
subject, market pulse, items w/ confidence + source links) / **Edit** (editable subject/headline/body)
→ export via **Copy Markdown**, **Copy text**, **Email** (`mailto:`).

### Frontend notes / gotchas
- Next upgraded off vulnerable `next@15.1.6` (CVE-2025-66478) to **`next@16.4.2`**. Do not downgrade.
- Next auto-modified `web/tsconfig.json` (`jsx: react-jsx`, added `.next/dev/types/**/*.ts` include).
- `web/next-env.d.ts` is committed (do not delete).
- `web/.gitignore` ignores `node_modules/ .next/ out/ .env*.local *.tsbuildinfo`.

---

## 8. Verification commands (run before finishing any backend change)

```bash
uv run pytest                 # 39 tests
uv run ruff check src tests   # line-length 110, select E,F,I,UP,B,C4,SIM; per-file B008 ignores
uv run mypy src               # strict, pydantic plugin, ignore_missing_imports
cd web && npm run build       # type-check + compile the frontend
```

Lint/type config lives in `pyproject.toml` (`[tool.ruff*]`, `[tool.mypy]`, `[tool.pytest.ini_options]`,
`asyncio_mode="auto"`).

---

## 9. Known issues, limitations & gotchas

1. **Deterministic taxonomy mislabels LedgerMind as `legal`** (the word "compliance" in fintech text).
   The LLM taxonomy path fixes this when `AISI_LLM_OFFLINE=false`. Do not "fix" by hardcoding.
2. **Newsletter `vertical_pulse` is cosmetic-wrong:** `agents/newsletter.py:33` sets the *same*
   `"{n} verified update(s)"` string for every selected vertical (n = total items, not per-vertical).
   Fix if per-vertical breakdowns are wanted.
3. **Demo company `description` is `null`** (demo filings lack descriptions) — the UI has fallbacks.
4. **Conflict case is intentional:** the demo's amended MediCore filing is *rejected* so MediCore
   stays at `$25M` (tests the append-only/anti-overwrite ledger). Don't "correct" it without reading
   `docs/final-design.md`.
5. **CORS is wide open** (`allow_origins=["*"]`) — fine for local dev, tighten for prod.
6. **Offline mock LLM** produces deterministic text, so generated headlines/bodies are templated,
   not "smart". Expected.
7. **No auth** anywhere yet (no login, no protected routes). Subscriptions are keyed by email only.
8. **No send/persist for a newsletter edition** — `/newsletter/preview` returns a draft but nothing
   is stored or emailed. Briefing "Email" is a `mailto:` client-side action.

### Operational pitfalls (learned this session)
- `pkill -f 'uvicorn aistartup_intel'` can **self-match** its own command line — prefer
  `pgrep -af ...` to find the PID, then `kill <pid>`.
- Backgrounding a server from the shell tool: use `setsid ... < /dev/null > log 2>&1 & disown` so it
  survives the tool's process-group cleanup. Redirect stdio or the tool waits on the pipe.
- `uv run` and `next` both spawn children; kill the whole group if needed.

---

## 10. Environment notes

- OS: linux. Python **3.13** via `uv` (`.python-version`, `uv.lock` present).
- Node **v26.7.0**, npm **11.19.0** (provided via `mise`).
- Backend deps: pydantic, pydantic-settings, SQLAlchemy, FastAPI, uvicorn, httpx, tenacity,
  beautifulsoup4, lxml, feedparser, python-dateutil, openai (OpenRouter is OpenAI-compatible),
  typer, pyyaml, redis. Optional extras: `adk` (google-adk), `postgres` (psycopg, pgvector).
- Repo is a git repo with **zero commits**; everything is untracked.

---

## 11. Conventions

- **No code comments** unless explicitly requested (ruff/quality style: self-documenting names).
- Backend is fully typed; `mypy --strict` must stay green. Line length 110.
- Agents are `Agent[Input, Output]` subclasses with `name`, `model_role`, `description`, and an
  async `handle(ctx, payload)`. Keep IO pydantic models in `models/agent_io.py`.
- Keep the deterministic/offline path working: never require network or an API key for tests/demo.
- Frontend: client components (`"use client"`), typed API client in `lib/api.ts`, styles in
  `globals.css`. Keep UI text investor-oriented.
- **Do not commit** unless the user explicitly asks.

---

## 12. Recommended next steps (rough priority)

Pick up with the user's direction; suggestions:

1. **Per-vertical pulse fix** in `agents/newsletter.py` (see §9.2) — compute counts per selected
   vertical (intersect item companies with taxonomy verticals).
2. **Persist + "send" a briefing:** store generated editions (new table), add
   `POST /newsletter/editions` and a "recent editions" list, and optionally email via a provider
   stub behind an interface (keep offline mode).
3. **Watchlists / saved views:** `WatchlistRow` already exists; expose endpoints + UI so a subscriber
   can pin topics/companies.
4. **Review-queue UI:** `/review` endpoints exist but have no frontend. Build an analyst page to
   approve/reject quarantined claims (`POST /review/{id}/resolve`).
5. **Auth + subscriber accounts** (email verification), then gate `/newsletter/subscription`.
6. **Go live with OpenRouter** behind a flag; add eval harness assertions (hallucination rate,
   precision) already sketched in `models/agent_io.py` (`EvaluationResult`).
7. **Postgres + pgvector path:** exercise `postgres` extra, add migrations.
8. **Deploy:** containerize backend + `web/`, set strict CORS, provide `.env.example`.
9. **First commit:** when the user asks, commit the initial tree (nothing is committed yet).

---

## 13. Quick file/line anchors

- Funding gate constant: `config/settings.py:54` (`funding_threshold_usd`).
- Newsletter pulse (known quirk): `agents/newsletter.py:33`.
- Newsletter item selection rule: `agents/newsletter.py:19-22`.
- API CORS: `api/app.py:46-52`. Subscribe endpoints: `api/app.py:290-349`. `/stats`: `api/app.py:352`.
- Frontend API base: `web/lib/api.ts` (`API_BASE`). Briefing page: `web/app/briefing/page.tsx`.
- Demo data: `demo.py` (`SAMPLE_FILINGS` at line 25; runner `run_demo`).

---

## 14. Suggested kickoff prompt for the next session

> Read `handoff1.md` and `docs/final-design.md`. Verify the current state with
> `uv run pytest && uv run ruff check src tests && uv run mypy src` and `cd web && npm run build`.
> Then [pick a task from §12]. Do not commit unless I ask.
