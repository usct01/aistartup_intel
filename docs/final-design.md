# AI Startup Signal — Final Design & Delivery Plan

Status: **For approval**
Supersedes: `PLANV1.md` (product/agent detail) and `docs/design.md` (systems/trust detail).
This document reconciles the two into one implementable specification.

---

## 0. Decisions at a glance (review these first)

| Topic | `PLANV1.md` | `docs/design.md` | **Final decision** |
| --- | --- | --- | --- |
| Orchestration | Google ADK | LangGraph supervisor | **Google ADK** (typed agents, workflow DAGs, HITL pauses) |
| LLM gateway | OpenRouter | provider-agnostic gateway | **OpenRouter**, per-task model policy |
| Event backbone | Redis (queues/cache/locks) | Redis Streams → Kafka | **Redis Streams** as backbone now; **Kafka/Redpanda** as documented scale path |
| Agent roster | 12 agents | 7 agents | **12 PLANV1 agents** + 1 deterministic **Scoring service** (not an LLM) |
| Ranking | Signal Analyst detects signals | Scoring agent ranks momentum | **Signal Analyst** produces signals; **Scoring service** computes explainable momentum/percentile |
| Trust model | Verifier + human review | Critic + quarantine + ledger | **Merged**: verifier + independent critic pass + append-only provenance ledger + human review |
| Knowledge stores | PostgreSQL, pgvector, object store, Redis | + provenance ledger, temporal graph | **Merged**: all of the above; ledger is first-class |
| Initial verticals | Healthcare, legal, finance | General AI | **Healthcare, legal, finance** first; broad taxonomy retained |
| Funding gate | > USD 10M disclosed | none | **PLANV1 rule** (total disclosed and per-round filters) |
| Skills layout | Full `SKILL.md` hierarchy | none | **PLANV1 `SKILL.md` layout adopted** |
| Compliance crawling | Detailed rules | brief | **PLANV1 rules adopted as normative** |
| Newsletter | Core product | brief | **PLANV1** |

**Open items needing your sign-off** are listed in §11.

---

## 1. Purpose

An investor-first AI startup intelligence platform. It discovers companies and funding
activity across public sources, verifies every material fact against retained evidence,
classifies them against a multi-label AI taxonomy, ranks momentum, and delivers a
personalized daily newsletter. Launch verticals: **healthcare, legal, finance**, with a
taxonomy that supports the full AI ecosystem.

**Non-negotiables**
1. **Verifiable** — no published fact without evidence span + provenance + confidence.
2. **Compliant** — no access-control bypass, CAPTCHA solving, or IP-rotation evasion.
3. **Explainable** — every score and every newsletter claim traces to evidence.
4. **Personalized** — daily edition filtered by each investor's sectors, thesis, watchlist.

**Non-goals (v1).** Financial advice, cap tables, private/derived PII, trading signals.

---

## 2. Product Definition

### 2.1 Investor experience
- Searchable company tracker: structured profiles, funding history, investors, positioning,
  competitors, evidence.
- Filters: vertical, AI category, geography, stage, investor, date, business model, customer
  type, and **total disclosed funding > USD 10M**.
- Market maps / landscape views per subscribed domain.
- Saved searches, watchlists, alerts, change timelines, comparable-company views.
- Daily personalized newsletter prioritizing verified developments in the investor's sectors.

### 2.2 Daily newsletter
New companies and newly discovered rounds; funding/investor activity including companies
crossing the USD 10M threshold; product launches, partnerships, customer wins, regulatory,
hiring, and research signals; watchlist and competitor movement; analyst interpretation with
evidence links; market pulse by vertical and AI category.

### 2.3 Taxonomy
Multi-label: a company may simultaneously hold a **regulated vertical**, an **AI capability
layer**, a **buyer/workflow category**, and a **maturity category**. The full taxonomy in
`PLANV1.md` §"AI startup taxonomy" is authoritative and lives in
`skills/common/references/taxonomy.md`.

### 2.4 Funding semantics (normative)
Separate filters for: **total publicly disclosed funding > USD 10M**, **individual round >
USD 10M**, stage, round type, date range, investor participation. Disclosed/undisclosed,
equity/debt/grant, announced vs. close date, and correction history are all stored.
Undisclosed/estimated values are labeled and **excluded** from numeric thresholds.

---

## 3. Architecture

### 3.1 Layered view

```text
Source registry + user watchlists
        |
        v
Discovery & crawl agents ─────▶ Raw-document store / crawl cache
        |                                |
        v                                v
Extraction agents ───────────▶ Structured claims + provenance + evidence spans
        |
        v
Verification (critic) + entity resolution
        |
        v
Taxonomy / funding / signal classification ──▶ Scoring service (deterministic)
        |
        v
PostgreSQL + pgvector knowledge base  (+ append-only provenance ledger)
        |
        +──▶ Search, filters, market maps, watchlists
        +──▶ Alerts + daily newsletter composer
        +──▶ Researcher / admin review console
```

### 3.2 Control backbone (the merge)
`PLANV1.md` gives the agent pipeline; `docs/design.md` gives the event-driven, replayable
backbone. The final system combines them:

- **Redis Streams** carries normalized `Event`s from ingestion to the ADK workflow; it also
  provides task queues, rate-limit buckets, and distributed locks (PLANV1's Redis uses).
- The **Google ADK workflow** is invoked per event/micro-batch and runs the typed agent DAG.
- Agents communicate via a **blackboard** (shared evidence + reference docs) and only
  validated workflows may write canonical records.
- Every run writes a **run manifest** (agents, models, versions, tokens, cost, decisions)
  enabling exact replay.

### 3.3 Orchestration pattern
Supervisor/planner + blackboard. ADK coordinates typed inputs/outputs, scheduled work,
retries, approvals, handoffs, and human-review pauses. The **Research Planner** sets goals;
the **Crawl Coordinator** enforces source policy deterministically and escalates exceptions
to an LLM only when needed.

---

## 4. Multi-Agent Team

Adopted from `PLANV1.md`, with the deterministic **Scoring service** added and the
`docs/design.md` trust machinery folded into the Verifier/Quality roles.

| Agent | Responsibility | Model policy |
| --- | --- | --- |
| Research Planner | Coverage goals, investor preferences, gaps → source/research tasks | GPT / Claude |
| Source Discovery | Official company, investor, press, registry, feed, reporting sources | Gemini / GPT |
| Crawl Coordinator | Source policy, caching, change detection, retries, diagnostics | **Deterministic Python**; LLM only for exceptions |
| Document Extractor | Facts, rounds, investors, dates, product claims, cited evidence spans | Gemini / GPT |
| Funding Analyst | Normalize round types, currency/date, totals, conflicts | GPT / Claude |
| Entity Resolver | Dedupe, aliases, rebrands, subsidiaries, investor names | Deterministic + GPT/Claude |
| Taxonomy Classifier | Vertical, AI layer, buyer, workflow, maturity labels | **DeepSeek** bulk; GPT/Gemini uncertain |
| Signal Analyst | Funding velocity, hiring, product, partnership, competitive, regulatory | GPT / Claude |
| Verifier | Validate against evidence, assign confidence, conflicts, review packets | GPT / Claude |
| Newsletter Editor | Select verified updates per subscriber; draft editions | Claude / GPT |
| Quality Evaluator | Sampled evals: hallucination, coverage, precision, remediation | GPT / Gemini |
| Human Review Queue | Route low-confidence/consequential updates + compact evidence packet | Deterministic + summaries |
| **Scoring service** (new) | Deterministic momentum score + percentile + factor breakdown | **Code, not LLM** — reproducible |

**Anti-correlation rule.** The Verifier uses a *different model family* from the Document
Extractor to reduce correlated error. Every claim must carry a **verbatim evidence span**
that exists in the retained source; spans that fail a literal match are rejected.

---

## 5. Data & Provenance Model

### 5.1 Event primitive (ingestion → agents)
```jsonc
{
  "event_id": "uuid", "source_id": "hn", "source_tier": "B",
  "observed_at": "...", "occurred_at": "...",
  "kind": "launch|funding|founder_move|oss_release|hiring|regulatory",
  "entity_mentions": [{"name": "Acme AI", "type": "company", "confidence": 0.7}],
  "claims": [{"predicate": "raised_amount_usd", "value": 4000000,
              "confidence": 0.55, "evidence_span": "raised $4M seed"}],
  "raw_uri": "s3://.../hn/2026/10/16/abc.json",
  "content_hash": "sha256:...",
  "provenance": {"url": "...", "retrieved_at": "...", "connector_version": "1.3.0"}
}
```

### 5.2 Canonical tables (from `PLANV1.md`, plus ledger)
- `companies`, `company_aliases`, `founders`, `investors`
- `funding_rounds`, `funding_participants`
- `documents`, `source_claims`, `evidence_spans`
- `taxonomy_tags`, `company_signals`
- `crawl_sources`, `crawl_runs`
- `users`, `subscriptions`, `watchlists`, `newsletter_editions`
- **`provenance_ledger`** — append-only; every claim links to evidence; conflicting claims
  coexist with confidence; nothing is overwritten.
- **`run_manifests`** — per-run agents/models/costs/decisions for replay.

### 5.3 Stores
PostgreSQL (canonical + temporal `valid_from/valid_to`), **pgvector** (hybrid semantic +
structured retrieval over approved passages and company summaries), object storage
(raw HTML/PDF/feed snapshots), Redis (Streams, queues, rate limits, cache, locks).

### 5.4 Entity resolution
Blocking + scoring on normalized name, domain, founder overlap, embedding similarity.
Above threshold → automatic merge; ambiguous → human review queue. Rebrands, aliases, and
subsidiaries handled explicitly.

---

## 6. Model Routing & Reliability (OpenRouter)

- Task-specific model policies, not one model for all work (see §4 table).
- **DeepSeek** for economical high-volume extraction/tagging/summarization.
- **GPT/Gemini/Claude** for complex extraction, reconciliation, nuanced classification,
  investor analysis, final editing.
- Enforce JSON schema on every agent output; **repair once → constrained retry → fallback
  model → human review**.
- Log model, version, cost, latency, success rate, confidence, downstream correction rate,
  and source quality per run.
- Minimize source text sent to models; redact secrets/unnecessary PII; retain only material
  research evidence.
- Per-agent token budgets and daily spend caps; semantic cache for repeated fetches.

---

## 7. Compliant Web Acquisition (normative)

- Curated **source registry**: company sites, pressrooms, investor portfolios, RSS, public
  registries, regulatory filings, research repositories, licensed providers.
- Prefer official APIs, RSS/Atom, sitemaps, structured data, ETag/Last-Modified conditional
  fetches, and cached snapshots before browser rendering.
- Per-domain policy: user agent, robots/terms, permitted paths, crawl budget, time windows,
  concurrency, contact info.
- Caching, request coalescing, adaptive rate limits, exponential backoff + jitter,
  per-domain queues, content-hash change detection.
- 403/429/anti-bot/auth-prompt/major-markup-change ⇒ **source pause + diagnostic**, never a
  bypass. For blocked high-value sources, prefer licensed data, publisher APIs, explicit
  authorization, customer-provided access, or alternate reputable sources.
- **Never** bypass CAPTCHAs, auth, robots, rate limits, or access controls; no IP rotation.
- Dedupe URLs/articles/claims/entities via hashes, canonical URLs, similarity, ER.
- Track source health, freshness, extraction quality, access status, legal notes.

---

## 8. Scoring & Ranking (added to PLANV1)

Deterministic, reproducible service consumed by the feed, alerts, and newsletter selection.

**Factors** (all map to evidence): round size/stage, lead-investor quality, valuation
step-up; founder pedigree/prior exits; traction (HN/PH, GitHub velocity, hiring velocity,
usage proxies); recency decay; novelty vs. crowded categories; signal quality (source tier,
independent corroborations).

**Method:** MVP = transparent weighted/logistic model with configurable weights → later GBT
once labels exist. Output `Score{value, percentile, factor_breakdown}`.

---

## 9. Delivery Plan

1. **Foundation** — PostgreSQL/pgvector schema, source registry, common skills + references,
   OpenRouter client, Google ADK workflow skeleton + Redis Streams backbone, provenance
   ledger, observability (OpenTelemetry + trace/cost logging), feature flags, analyst review
   queue. First connector: SEC Form D.
2. **Research MVP** — discovery, compliant crawling, extraction, entity resolution, funding
   normalization, verification, taxonomy for healthcare/legal/finance. Pipeline end-to-end
   with human review; no scoring yet.
3. **Investor product** — company profiles, hybrid search, market maps, saved filters,
   watchlists, the USD 10M funding filters, source/evidence views.
4. **Newsletter** — subscriber preferences, editorial selection, evidence-aware generation,
   email delivery, feedback capture, unsubscribe, delivery reporting.
5. **Scale & quality** — expand coverage, alerts, ecosystem maps, evaluation suites, model
   routing optimization, momentum Scoring service, broader verticals, Kafka path if needed.

---

## 10. Test Plan

- Extraction of companies, aliases, investor normalization, rounds, citations vs. real sources.
- USD 10M boundary; **total disclosed vs. single-round** distinction.
- Every newsletter claim links to retained evidence; unverified/conflicted claims excluded.
- Crawler honors robots/terms config, budgets, pauses; never circumvents blocked access.
- Malformed model output, fallback routing, duplicate docs, conflicting funding reports,
  low-confidence review routing.
- Subscriber personalization, watchlist alerts, unsubscribe, delivery failures, idempotent
  newsletter publication.
- Analyst corrections propagate to search, profiles, future newsletters.
- **Replay:** a run manifest reproduces a brief exactly from its inputs.
- **Ranking reproducibility:** identical inputs → identical score.

---

## 11. Decisions for Your Approval

1. **Backbone scope.** Adopt Redis Streams as the event backbone now (Kafka later), or start
   with plain Redis queues as in PLANV1 and skip the stream abstraction?
2. **Scoring service.** Confirm adding the deterministic Scoring service (not in PLANV1) as a
   Phase 5 deliverable, or fold ranking into Signal Analyst only?
3. **Verifier anti-correlation.** Confirm the rule that Verifier must use a *different* model
   family than Document Extractor (adds routing complexity, improves trust).
4. **Auto-publish threshold.** Default proposal: tiered publishing — fast low-confidence
   *alerts*, delayed verified *briefs/newsletter*. Agree?
5. **`docs/design.md` disposition.** Keep as internal systems reference, or delete once this
   document is approved?
6. **Repo layout.** Adopt the `src/aistartup_intel/` layout from `docs/design.md` (connectors,
   bus, models, store, agents, tools, api, eval, config) alongside PLANV1's `skills/` tree?

---

## 12. Assumptions & Defaults

- Launch verticals healthcare, legal, finance; taxonomy broader for later expansion.
- Funding totals use only publicly disclosed, source-verifiable amounts; estimates excluded
  from thresholds.
- OpenRouter is the LLM gateway; Google ADK is the orchestration framework.
- Platform is compliant research infrastructure; resilience ≠ access-control bypass.
- High-impact/conflicting claims require verification and often human approval before
  newsletter publication.
