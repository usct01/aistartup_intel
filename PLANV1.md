# AI Startup Signal — Multi-Agent Intelligence Platform Design

## Summary

Build an investor-first AI startup intelligence platform that tracks companies, funding, product activity, and market signals, then produces a personalized daily newsletter. The initial launch covers healthcare, legal, and finance, while the taxonomy supports the full AI ecosystem.

The system uses Python and Google ADK to orchestrate specialized research agents. OpenRouter provides model access and routing across GPT, Gemini, Claude, and DeepSeek. PostgreSQL is the system of record; pgvector powers semantic search and similarity. Every material fact is source-backed, confidence-scored, and reviewable.

The funding threshold is **more than USD 10 million in verified, publicly disclosed total funding**, with separate filters for individual round size and funding type.

## Product Concept

### Investor experience

- Searchable company tracker with structured profiles, funding history, investors, product positioning, competitors, and source evidence.
- Filters for vertical, AI category, geography, stage, investor, date, business model, customer type, and total disclosed funding above USD 10 million.
- Market maps and landscape views for subscribed domains, such as healthcare AI agents or legal AI governance.
- Saved searches, watchlists, alerts, change timelines, and comparable-company views.
- A daily personalized email newsletter that prioritizes verified developments relevant to each investor's sectors, theses, watchlists, and funding preferences.

### Daily newsletter

Each edition includes:

- New companies and newly discovered funding rounds.
- Funding and investor activity, including companies crossing the USD 10 million total-disclosed threshold.
- Product launches, partnerships, customer wins, regulatory events, hiring, and research signals.
- Watchlist changes and competitor movement.
- Short analyst-style interpretation with links to underlying evidence.
- A concise market pulse by subscribed vertical and AI category.

### AI startup taxonomy

Companies are multi-labelled: a company may belong to a regulated vertical, an AI capability layer, a buyer/workflow category, and a technical maturity category simultaneously.

**Foundation models and infrastructure**

- General-purpose, domain-specific, multimodal, small, open-source, and sovereign foundation models.
- Model hosting, inference, serving, routing, gateways, orchestration, caching, and observability.
- AI agent frameworks, runtimes, tool-use platforms, memory, planning, workflow orchestration, and agent evaluation.
- Vector databases, RAG systems, knowledge graphs, enterprise search, data pipelines, data quality, data labeling, synthetic data, and data marketplaces.
- Fine-tuning, training platforms, RLHF/RLAIF, evaluation, benchmarking, prompt tooling, model development, and MLOps.
- Edge AI, on-device AI, AI chips, accelerators, networking, cloud GPU, data-center management, cooling, energy optimization, and capacity marketplaces.

**Trust, governance, and security**

- AI governance, policy management, model risk management, audit, compliance, explainability, and responsible AI.
- AI security, prompt-injection defense, model supply-chain security, red teaming, adversarial testing, fraud prevention, identity, privacy, and data-loss prevention.
- Content authenticity, provenance, watermarking, deepfake detection, IP/copyright management, and safety tooling.

**Agentic and application layer**

- Horizontal enterprise agents: sales, marketing, support, HR, recruiting, procurement, operations, finance, analytics, IT, developer productivity, and knowledge work.
- Consumer and prosumer agents: personal productivity, education, creativity, commerce, travel, media, gaming, and communications.
- Robotics, industrial automation, computer vision, digital twins, autonomous systems, and physical-world AI.

**Healthcare and life sciences**

- Clinical documentation, coding, revenue cycle, patient engagement, care navigation, triage, clinical decision support, and administrative automation.
- Drug discovery, protein design, diagnostics, imaging, genomics, clinical trials, medical devices, provider operations, and payer technology.

**Legal**

- Legal research, contract lifecycle management, e-discovery, litigation intelligence, drafting, compliance, investigations, IP, and legal operations.

**Finance**

- Fintech AI, wealth and asset management, trading and research, underwriting, lending, insurance, payments, fraud, AML/KYC, accounting, treasury, risk, and regulatory technology.

**Future vertical expansion**

- Manufacturing, logistics, energy, climate, real estate, retail, agriculture, education, government, telecom, media, cybersecurity, defense, and construction.

## System Architecture

```text
Source registry + user watchlists
          |
          v
Discovery and crawling agents ----> Raw-document store / crawl cache
          |                                      |
          v                                      v
Extraction agents ----------------> Structured claims + provenance
          |
          v
Verification and entity-resolution agents
          |
          v
Classification, funding, and market-signal agents
          |
          v
PostgreSQL + pgvector knowledge base
          |
          +--> Search, filters, market maps, watchlists
          +--> Alerts and daily-newsletter composer
          +--> Researcher/admin review console
```

- **Application layer:** Python 3.13, FastAPI APIs, asynchronous workers, and a React/Next.js web client when the investor UI is added.
- **Orchestration:** Google ADK coordinates typed agent inputs and outputs, scheduled work, retries, approvals, handoffs, and human-review pauses.
- **LLM gateway:** An OpenRouter client provides a single provider interface, model routing policy, JSON-schema validation, retries, fallbacks, cost tracking, and model/version logging.
- **Data stores:** PostgreSQL for canonical data, pgvector for semantic retrieval and deduplication, object storage for raw HTML/PDF/feed/rendered snapshots, and Redis for task queues, rate limits, caches, and locks.
- **Operations:** Daily newsletter cutoff, source polling schedules, priority crawl queues, retry policies, source-health checks, taxonomy review, and recurring model evaluation.

## Multi-Agent Team

| Agent | Responsibility | Preferred model policy |
| --- | --- | --- |
| Research Planner | Turns coverage goals, investor preferences, and gaps into source and research tasks. | GPT or Claude |
| Source Discovery | Finds official company, investor, press, registry, feed, and reputable reporting sources. | Gemini or GPT |
| Crawl Coordinator | Enforces source policies, caches content, detects changes, schedules retries, and emits diagnostics. | Deterministic Python first; LLM only for exceptions |
| Document Extractor | Extracts company facts, funding rounds, investors, dates, product claims, and cited evidence spans. | Gemini or GPT |
| Funding Analyst | Normalizes round types, resolves currency/date distinctions, calculates totals, and identifies conflicts. | GPT or Claude |
| Entity Resolver | Resolves duplicates, aliases, rebrands, subsidiaries, investor names, and related entities. | Deterministic matching plus GPT/Claude |
| Taxonomy Classifier | Assigns vertical, AI layer, buyer, workflow, and maturity labels. | DeepSeek for bulk; GPT/Gemini for uncertain cases |
| Signal Analyst | Detects funding velocity, hiring, product, partnership, competitive, and regulatory signals. | GPT or Claude |
| Verifier | Validates claims against evidence, assigns confidence, identifies conflicts, and creates review packets. | GPT or Claude |
| Newsletter Editor | Selects verified updates per subscriber and drafts concise investor-oriented editions. | Claude or GPT |
| Quality Evaluator | Runs sampled evaluations for hallucinations, coverage, precision, and remediation recommendations. | GPT or Gemini |
| Human Review Queue | Routes low-confidence or consequential updates to an analyst with a compact evidence packet. | Deterministic workflow plus summaries |

Agents may read shared evidence and reference documents, but only validated workflows can write canonical records. Every handoff uses typed structured data and preserves document, extraction, model, timestamp, and confidence provenance.

## `SKILL.md` and Role Reference Layout

```text
skills/
  common/
    SKILL.md
    references/
      evidence-standard.md
      taxonomy.md
      funding-normalization.md
      source-confidence.md
      editorial-style.md
  research-planner/SKILL.md
  source-discovery/SKILL.md
  crawl-coordinator/SKILL.md
  document-extractor/SKILL.md
  funding-analyst/SKILL.md
  entity-resolver/SKILL.md
  taxonomy-classifier/SKILL.md
  verifier/SKILL.md
  signal-analyst/SKILL.md
  newsletter-editor/SKILL.md
  quality-evaluator/SKILL.md
```

The common skill establishes non-negotiable behavior: cite evidence, never invent facts, emit structured output, record uncertainty, preserve privacy, and escalate conflicts. The shared references define source hierarchy, taxonomy, funding normalization, source-confidence scoring, and newsletter tone.

Each role-specific `SKILL.md` defines:

- Mission and boundaries.
- Allowed tools and source types.
- Required input/output schemas.
- Decision rules and confidence thresholds.
- Failure handling and escalation paths.
- Examples of valid and invalid outputs.

## Data Model and Interfaces

Core tables:

- `companies`, `company_aliases`, `founders`, `investors`
- `funding_rounds`, `funding_participants`
- `documents`, `source_claims`, `evidence_spans`
- `taxonomy_tags`, `company_signals`
- `crawl_sources`, `crawl_runs`
- `users`, `subscriptions`, `watchlists`, `newsletter_editions`

Key company fields include canonical name, aliases, URL, headquarters, description, vertical tags, AI capability tags, target buyers, maturity, employee/hiring signals, funding total, latest round, investors, evidence links, confidence, and last verified time.

Funding records store announced date, close date where known, currency and USD-normalized amount, round type, disclosed/undisclosed status, equity/debt/grant distinction, participating investors, sources, confidence, and correction history. The product exposes distinct filters for:

- Total publicly disclosed funding greater than USD 10 million.
- Individual round amount greater than USD 10 million.
- Funding stage, round type, date range, and investor participation.

Semantic search uses pgvector over approved source passages and company summaries, combined with structured PostgreSQL filtering for hybrid retrieval.

## Model Routing and Reliability

- Use OpenRouter as the unified provider gateway, with task-specific model policies rather than a single model for all work.
- Use DeepSeek for economical high-volume preliminary extraction, tagging, and summarization.
- Use GPT, Gemini, or Claude for complex extraction, reconciliation, nuanced classification, investor analysis, and final newsletter editing.
- Enforce JSON schemas on every agent output; repair once, retry with a constrained prompt, then fall back to another model or human review.
- Log model, version, cost, latency, success rate, confidence, downstream correction rate, and source quality for every run.
- Minimize source text sent to models, redact secrets and unnecessary personal data, and retain only material research evidence.

## High-Quality, Compliant Web Acquisition

The crawler must be resilient without evading access controls.

- Maintain a curated source registry for company sites, pressrooms, investor portfolios, RSS feeds, public registries, regulatory filings, research repositories, and licensed news/data providers.
- Prefer official APIs, RSS/Atom, sitemaps, structured data, ETag/Last-Modified conditional fetches, and cached snapshots before browser rendering.
- Store domain-specific policies: user agent, robots.txt and terms restrictions, permitted paths, crawl budget, time windows, concurrency, and contact information.
- Use caching, request coalescing, adaptive rate limits, exponential backoff, jitter, per-domain queues, and content-hash change detection to reduce load and avoid unnecessary requests.
- Treat 403, 429, anti-bot challenges, authentication prompts, and substantial markup changes as a source pause plus diagnostic event—not a signal to bypass protections.
- For blocked high-value sources, prioritize licensed data, publisher APIs, explicit authorization or partnerships, customer-provided authorized access, alternative reputable sources, or analyst research.
- Never bypass CAPTCHAs, authentication, robots directives, rate limits, or technical access controls; do not use IP rotation/proxies to evade a website's blocking policy.
- Deduplicate URLs, articles, extracted claims, and company entities through hashes, canonical URLs, similarity search, and entity resolution.
- Track source health, freshness, extraction quality, access status, and legal/compliance notes.

## Delivery Plan

1. **Foundation:** Create the PostgreSQL/pgvector schema, source registry, common skills and references, OpenRouter client, Google ADK workflow skeleton, observability, and analyst review queue.
2. **Research MVP:** Implement discovery, compliant crawling, extraction, entity resolution, funding normalization, verification, and taxonomy workflows for the three initial verticals.
3. **Investor product:** Add company profiles, hybrid search, market maps, saved filters, watchlists, the verified USD 10 million funding filter, and source/evidence views.
4. **Newsletter:** Add subscriber preferences, editorial selection, evidence-aware newsletter generation, email delivery, feedback capture, unsubscribe support, and delivery reporting.
5. **Scale and quality:** Expand source coverage, add alerts and ecosystem maps, run evaluation suites, optimize model routing, and broaden vertical support.

## Test Plan

- Verify company extraction, aliases, investor normalization, funding rounds, and citations against representative public sources.
- Test the USD 10 million boundary and distinguish total disclosed funding from single-round size.
- Confirm every newsletter claim links to retained evidence and excludes unverified or conflicted claims.
- Confirm crawler policies honor robots/terms configuration, rate budgets, pauses, and never attempt to circumvent blocked access.
- Test malformed model output, fallback routing, duplicate documents, conflicting funding reports, and low-confidence review routing.
- Test subscriber personalization, watchlist alerts, unsubscribe handling, email delivery failures, and idempotent newsletter publication.
- Test analyst corrections and confirm changed canonical data propagates to search, profiles, and future newsletters.

## Assumptions and Defaults

- Initial launch is healthcare, legal, and finance; the taxonomy is intentionally broader for later expansion.
- Funding totals use only publicly disclosed, source-verifiable amounts. Estimates and undisclosed values are labeled but excluded from the numeric threshold.
- OpenRouter is the LLM provider gateway, while Google ADK is the orchestration framework.
- The platform operates as compliant research infrastructure. Resilience means efficient, permitted acquisition and alternate authorized sources—not IP-block avoidance or access-control bypassing.
- High-impact or conflicting claims require verification and, when needed, human analyst approval before newsletter publication.
