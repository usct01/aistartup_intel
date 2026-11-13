# AI Startup Signal — Multi-Agent Intelligence Platform Design

Status: Draft v0.1
Scope: Detect, verify, enrich, and rank newly emerging AI startups and their funding
events, then produce analyst-grade briefs for investors, scouts, and operators.

---

## 1. Problem & Goals

**Problem.** Signals of a new AI startup — a launch, a seed round, a founder move, an
open-source release — are scattered across founder blogs, X/Twitter, Hacker News,
Product Hunt, SEC filings, VC portfolio pages, and paid databases. No single source is
fast, complete, and trustworthy at once. Investors learn about hot companies too late or
from too few eyeballs.

**Goals (in priority order).**

1. **Coverage** — discover startups *before* they appear in Crunchbase/PitchBook.
2. **Trust** — every claimed fact (funding amount, investors, founders, dates) carries
   provenance and a confidence score; low-confidence claims are quarantined, not published.
3. **Signal, not noise** — rank emerging companies by a defensible momentum score, not by
   media volume alone.
4. **Timeliness** — surface a fresh signal within minutes of its first public trace.
5. **Explainability** — each brief shows the evidence chain that produced it.

**Non-goals (v1).** Financial advice, cap-table data, private/derived PII, trading signals.

---

## 2. System Overview

```
                         ┌───────────────────────────────────────────┐
   SOURCES              │              INGESTION                    │
 ┌──────────────┐        │  Connectors → normalize → dedupe → land   │
 │ Crunchbase   │───────▶│                                           │
 │ SEC EDGAR    │        └───────────────────┬───────────────────────┘
 │ HN / PH / X  │                            │ raw events
 │ VC pages     │                            ▼
 │ Blogs / RSS  │        ┌───────────────────────────────────────────┐
 │ GitHub/arXiv │        │            EVENT BUS / QUEUE              │
 └──────────────┘        │   (Kafka/Redpanda or Redis Streams)       │
                         └───────────────────┬───────────────────────┘
                                             ▼
     ┌───────────────────────────────────────────────────────────────────┐
     │                     ORCHESTRATOR (supervisor agent)                │
     │   routes tasks, owns budgets/rate limits, retries, escalation     │
     └───┬───────────┬───────────┬───────────┬───────────┬───────────┬───┘
         ▼           ▼           ▼           ▼           ▼           ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
   │ SCOUT   │ │ FUNDING │ │ ENRICH  │ │ VERIFY  │ │ SCORING │ │ ANALYST │
   │ Agent   │ │ Agent   │ │ Agent   │ │ (Critic)│ │ Agent   │ │ Agent   │
   └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘
        └───────────┴───────────┴─────┬──────┴───────────┴───────────┘
                                      ▼
     ┌───────────────────────────────────────────────────────────────────┐
     │                        SHARED KNOWLEDGE LAYER                      │
     │  Company graph (Postgres) · Documents (S3) · Vectors (pgvector)   │
     │  Agent memory · Provenance ledger (append-only)                   │
     └───────────────────────────────────────────────────────────────────┘
                                      ▼
                       Briefs · Alerts · Ranked feed · API
```

The design separates a **deterministic skeleton** (ingestion, bus, storage, scheduling)
from a **probabilistic workforce** (LLM agents). Agents never talk to the raw internet
directly; they consume curated events and call tools that enforce rate limits and
provenance capture.

---

## 3. Data Sources & Connectors

Classified by reliability and latency so the scoring model can weight them.

| Tier | Source | Signal | Latency | Access |
|------|--------|--------|---------|--------|
| A (primary/official) | SEC EDGAR Form D, state registrations | funding filed, entity formation | days | API, free |
| A | Company/VC portfolio pages, press releases | launches, announced rounds | hours–days | scrape |
| B (community/fast) | Hacker News, Product Hunt, Reddit | launch, traction | minutes | API |
| B | X/Twitter, founder blogs, LinkedIn | founder moves, teasers | minutes–hours | API/scrape (ToS-bound) |
| B | GitHub orgs, npm/PyPI, arXiv | OSS release, research | minutes | API |
| C (aggregators) | Crunchbase, PitchBook, Dealroom, Tracxn | canonical funding/enrichment | days | paid API |

**Connector contract.** Each connector implements:

```python
class Connector(Protocol):
    source_id: str
    tier: str
    poll_interval: timedelta | None      # None => push/webhook
    async def fetch(self, cursor: Cursor | None) -> AsyncIterator[RawRecord]: ...
    def normalize(self, raw: RawRecord) -> Event: ...
```

- **Idempotency** — every raw record gets a content hash used as the dedupe key.
- **Cursor checkpoints** — stored per connector so restarts never reprocess or skip.
- **Backpressure** — connectors emit into the bus; slow consumers don't block fetch.
- **ToS/compliance** — connectors declare `legal_review_status`; unscraped or unlicensed
  sources are disabled in config, not hard-coded.

---

## 4. Data Model

A single **event** primitive flows through the bus; everything else is derived.

```jsonc
{
  "event_id": "uuid",
  "source_id": "hn",
  "source_tier": "B",
  "observed_at": "2026-10-16T09:12:00Z",   // when we saw it
  "occurred_at": "2026-10-16T08:50:00Z",   // when it happened (best effort)
  "kind": "launch | funding | founder_move | oss_release | hiring",
  "entity_mentions": [
    {"name": "Acme AI", "type": "company", "confidence": 0.7},
    {"name": "Jane Doe", "type": "person", "role": "founder", "confidence": 0.6}
  ],
  "claims": [
    {"predicate": "raised_amount_usd", "value": 4000000,
     "confidence": 0.55, "evidence_span": "raised $4M seed"}
  ],
  "raw_uri": "s3://.../hn/2026/10/16/abc.json",
  "content_hash": "sha256:...",
  "provenance": {"url": "...", "retrieved_at": "...", "connector_version": "1.3.0"}
}
```

**Canonical stores.**

- **Company graph (Postgres)** — `companies`, `people`, `investors`, `funding_rounds`,
  `products`, `relationships`. Soft-delete + `valid_from/valid_to` for temporal queries.
- **Document store (S3)** — immutable raw payloads, referenced by `raw_uri`.
- **Vector store (pgvector)** — embeddings of documents and entity descriptions for
  entity resolution and similar-company retrieval.
- **Provenance ledger (append-only)** — every claim links to its evidence; nothing is
  overwritten, conflicting claims coexist with confidence scores.

**Entity resolution.** Dedupe companies/people across sources via a blocking + scoring
pipeline: normalized name, domain, founder overlap, embedding similarity. Merge decisions
above a threshold are automatic; ambiguous ones go to a **human-in-the-loop** queue.

---

## 5. The Agent Workforce

Each agent is a bounded worker with a typed input/output contract, its own tools, a
system prompt, a model tier (cheap vs. strong), and a token/cost budget.

### 5.1 Orchestrator (Supervisor)

Stateful router built on a graph runtime (LangGraph recommended; CrewAI/AutoGen are
alternatives). Responsibilities:

- Consume events, classify them, and dispatch to the right agent(s).
- Manage DAGs (e.g. `scout → enrich → verify → score → analyst`).
- Enforce per-agent budgets, retry policies, and circuit breakers on failing tools.
- Own the **run manifest**: which agents touched an item, what they cost, what they decided.
- Escalate to human review when confidence is low or claims conflict irreconcilably.

Pattern: **supervisor + blackboard**. The orchestrator routes, while agents read/write a
shared blackboard (the knowledge layer) rather than calling each other directly. This
keeps agents independent, testable, and replayable.

### 5.2 Scout Agent — *discovery*

- **Job:** find companies not yet in the graph.
- **Input:** `launch`, `funding`, `founder_move`, `oss_release` events.
- **Tools:** search APIs, domain-whois, embedding search over the graph ("have we seen this
  company?"), entity-resolution tools.
- **Output:** candidate `CompanyCandidate` records with `is_new` flag and rationale.
- **Model tier:** cheap/fast (high volume).

### 5.3 Funding Agent — *event extraction*

- **Job:** turn prose into structured funding claims.
- **Input:** press releases, Form D filings, news, founder posts.
- **Tools:** LLM extraction with strict JSON schema, SEC parser, currency/round
  normalization, investor-name resolver.
- **Output:** `FundingClaim{amount, currency, round, date, lead, participants,
  valuation, evidence_span}`.
- **Guardrail:** must return an `evidence_span` that literally appears in the source;
  spans that don't match are rejected (anti-hallucination).
- **Model tier:** strong model; low volume, high value.

### 5.4 Enrichment Agent — *profile building*

- **Job:** build/refresh the company profile — sector, sub-sector, founders, HQ, tech
  stack, product, competitors.
- **Tools:** web fetch, GitHub API, embeddings, taxonomy classifier.
- **Output:** patch set applied to the company graph with per-field provenance.
- **Model tier:** mid.

### 5.5 Verify / Critic Agent — *the trust gate*

- **Job:** adversarially challenge every claim before publication.
- **Checks:**
  - **Corroboration** — is the claim supported by ≥1 independent Tier-A/B source?
  - **Provenance** — does the evidence span exist verbatim?
  - **Contradiction** — does it conflict with an existing ledger claim?
  - **Temporal sanity** — is `occurred_at` plausible?
  - **Source reputation** — is the source historically reliable?
- **Output:** `Verdict{publish | quarantine | reject}` + confidence + reasons.
- **Policy:** low-confidence items never auto-publish; they go to human review. The critic
  is deliberately a *different model/prompt* from the Extractor to reduce correlated error.
- **Model tier:** strong, reasoning.

### 5.6 Scoring Agent — *momentum ranking*

- **Job:** produce a transparent momentum score.
- **Inputs (weighted, configurable):**
  - Funding: round size, stage, lead-investor quality, valuation step-up.
  - Team: founder pedigree, prior exits, notable employers, team size growth.
  - Traction: HN/PH points, GitHub stars/velocity, product usage proxies, hiring velocity.
  - Timing: recency decay, novelty vs. crowded sectors.
  - Signal quality: source tier, number of independent corroborations.
- **Method:** starts as a linear/logistic model with hand-set weights (explainable), evolves
  to gradient-boosted trees once labels exist. **Every factor maps to evidence** so the
  brief can justify the rank.
- **Output:** `Score{value, percentile, factor_breakdown}`.
- **Model tier:** deterministic (code), not an LLM — rankings must be reproducible.

### 5.7 Analyst Agent — *brief generation*

- **Job:** write the human-facing brief: what happened, why it matters, who's involved,
  confidence, open questions, and the evidence chain.
- **Guardrail:** may only cite claims present in the ledger; every assertion carries inline
  citations. Refuses to speculate beyond evidence.
- **Output:** Markdown/JSON brief + alert payload.
- **Model tier:** strong.

### 5.8 Memory — not a separate agent, a shared service

- **Working memory:** the current run's blackboard.
- **Episodic memory:** past runs, decisions, and human corrections — used to calibrate
  confidence and avoid re-litigating resolved items.
- **Semantic memory:** vector index of all documents/entities.

---

## 6. Control Flow (end-to-end)

1. **Ingest.** Connectors land raw records and emit normalized events to the bus.
2. **Detect.** Orchestrator classifies events; dedupe against graph.
3. **Discover.** Scout identifies new entities → entity resolution.
4. **Extract.** Funding/Enrichment agents produce structured claims + profile patches.
5. **Verify.** Critic corroborates/contradicts; assigns verdict + confidence.
6. **Score.** Scoring agent computes momentum if the item is published.
7. **Publish.** Analyst writes the brief; alerts fire; API/feed updated.
8. **Learn.** Human corrections and downstream outcomes (did the company grow, re-raise?)
   feed back as labels for the scoring model and confidence calibration.

**Failure modes handled by design:** a failed connector degrades coverage but not
correctness; a failed strong-model call retries with a cheaper fallback and marks the item
`low_confidence`; conflicting claims are surfaced, never silently overwritten.

---

## 7. Technology Choices

| Concern | Choice | Rationale |
|---------|--------|-----------|
| Language | Python 3.13 | ecosystem for LLM + data tooling; matches existing project |
| Agent runtime | **LangGraph** (primary); CrewAI/AutoGen considered | explicit graph state, replay, human-in-the-loop, checkpointing |
| Event bus | Redis Streams (start) → Redpanda/Kafka (scale) | low ops burden early, durable + partitioned later |
| Relational/graph | PostgreSQL (+ Apache AGE or `edges` tables) | one engine for graph + temporal + JSONB |
| Vectors | pgvector | avoids a second datastore until scale demands it |
| Object store | S3-compatible (MinIO locally) | immutable raw evidence |
| Orchestration/schedule | Prefect or Temporal | retries, schedules, backfills, observability |
| API | FastAPI | typed, async, OpenAPI |
| LLM access | provider-agnostic gateway with caching + per-agent budgets | cost control + model swap without rewrites |
| Observability | OpenTelemetry + LangSmith/Langfuse traces | trace every agent step, token, and cost |
| Eval | golden-set regression + LLM-as-judge (guardrailed) | catch prompt/model regressions |
| Packaging | `uv` | already configured in this repo |

---

## 8. Reliability, Cost & Safety

- **Provenance by construction.** No claim exists without a `raw_uri` + evidence span.
- **Anti-hallucination.** Verbatim-span requirement, critic pass, ledger contradictions.
- **Human-in-the-loop.** Quarantine queue for low-confidence merges/claims; reviewer
  decisions are first-class data.
- **Cost controls.** Cheap models for high-volume discovery; strong models only for
  extraction/verification/briefs. Per-agent token budgets and daily spend caps; semantic
  cache for repeated fetches.
- **Rate limits & politeness.** Centralized per-source token buckets; `robots.txt`/ToS
  respected; retries with jittered backoff.
- **Privacy.** Only public/professional data; no private PII; configurable redaction.
- **Auditability.** Append-only ledger + run manifests let any brief be reconstructed
  exactly from its inputs (replayable).
- **Kill switch.** Any connector or agent can be disabled via config without a deploy.

---

## 9. Evaluation

- **Extraction quality:** precision/recall of funding-amount and investor extraction against
  a hand-labeled golden set.
- **Discovery lead time:** median hours between our first signal and Crunchbase appearance.
- **Trust:** % of published claims later contradicted; target < 2%.
- **Ranking usefulness:** precision@K of "companies investors care about" vs. curated list.
- **Cost per verified signal** and **cost per brief** tracked as first-class metrics.

---

## 10. Suggested Repository Layout

```
src/aistartup_intel/
  connectors/        # per-source fetch + normalize
  bus/               # event bus producers/consumers
  models/            # pydantic event & domain schemas
  store/             # postgres, vectors, object store, ledger
  agents/
    orchestrator.py
    scout.py
    funding.py
    enrich.py
    verify.py
    scoring.py
    analyst.py
  tools/             # rate-limited external tools + LLM gateway
  api/               # FastAPI app
  eval/              # golden sets + harness
  config/            # per-connector/agent config, budgets
docs/
  design.md          # this document
```

---

## 11. Phased Roadmap

- **Phase 0 — Foundations.** Event schema, bus, Postgres + ledger, one connector (SEC
  Form D), pydantic domain models, tracing.
- **Phase 1 — Core loop.** Scout + Funding + Verify + Analyst for funding events, with
  human review. No scoring yet.
- **Phase 2 — Enrichment & dedupe.** Entity resolution, enrichment agent, vector memory,
  more connectors (HN, PH, GitHub).
- **Phase 3 — Ranking.** Scoring agent with explainable factors; ranked feed + alerts.
- **Phase 4 — Scale & learn.** Kafka, more sources, feedback loop from outcomes, model
  fine-tuning on accumulated labels.

---

## 12. Open Questions

1. Which paid aggregators are licensed for our use (Crunchbase/PitchBook terms)?
2. What is the publish threshold — auto-publish above which confidence, and who reviews?
3. Do we optimize for **discovery lead time** (speed) or **precision** (trust) when they
   conflict? Proposed default: tiered publishing — fast low-confidence alerts, delayed
   verified briefs.
4. Sectors of focus within "AI" (infra, agents, verticals) to sharpen the scoring model.
5. Build vs. buy the entity-resolution layer.
