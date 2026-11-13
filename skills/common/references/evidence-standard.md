# Evidence Standard

Defines what counts as evidence, how provenance is recorded, how sources are tiered, and how
confidence is scored. This standard is normative for all agents.

## 1. Evidence spans

An **evidence span** is a verbatim passage from a retained source document that supports a
claim. It is represented by `EvidenceSpan` in `src/aistartup_intel/models/events.py`:

- `text` — the literal passage. Non-empty. Copied exactly from the source.
- `start` / `end` — optional character offsets within the document.
- `document_uri` — the retained document the span comes from.

Rules:

- The span must **literally match** text present in the retained source. The Verifier performs
  a literal match; spans that fail the literal match are **rejected**.
- Do not paraphrase, summarize, translate, normalize whitespace across sentence boundaries, or
  repair typos inside a span.
- A span should contain the sentence or clause that establishes the claim (for example, the
  sentence naming the amount and round type for a funding claim).
- Because spans are immutable (`frozen`), corrections create a new claim rather than mutating
  an old one.

## 2. The no-evidence rule

**Any claim without a verbatim evidence span is invalid and is rejected.** There is no
exception for "obvious" facts. A claim that cannot be anchored to a retained passage must be
dropped or routed to human review as a question, not published as a fact.

## 3. Provenance requirements

Every record carries `Provenance` (`src/aistartup_intel/models/events.py`):

- `url` — the source URL.
- `retrieved_at` — when it was fetched (UTC).
- `connector_id`, `connector_version` — which connector acquired it.
- `http_status`, `etag` — acquisition details for conditional fetch and cache reuse.
- `legal_note` — any licence, terms, or access notes.

Additional requirements:

- Store a `content_hash` (`sha256:...`) for every raw document so duplicates are detectable.
- Link every claim to its source event id(s) and, transitively, to the raw document URI.
- The **append-only provenance ledger** stores every claim with its evidence and confidence.
  Conflicting claims coexist; nothing is overwritten.

## 4. Source tiers

Sources are tiered by reliability and latency (`SourceTier` in `src/aistartup_intel/models/enums.py`):

- **Tier A — Primary.** Official filings and registries (for example SEC Form D), company and
  VC pages, pressrooms, and other first-party authoritative records.
- **Tier B — Community / fast.** Hacker News, Product Hunt, X, GitHub, arXiv, and similar fast
  signals. High velocity, lower per-item reliability.
- **Tier C — Aggregator.** Paid or curated aggregators such as Crunchbase and PitchBook.
  Useful for coverage and corroboration, but not authoritative on their own.

Tier influences confidence weighting; see `source-confidence.md`.

## 5. Confidence scoring bands

Confidence is a value in `[0.0, 1.0]`. Default reporting bands:

| Band | Range | Meaning |
| --- | --- | --- |
| High | 0.85 – 1.00 | Primary source, verbatim span, corroborated |
| Medium | 0.60 – 0.84 | Sound evidence, partial corroboration or single primary |
| Low | 0.40 – 0.59 | Weak/indirect evidence; review or quarantine |
| Very low | < 0.40 | Insufficient; do not publish, route to review |

Bands are guidance for routing, not a substitute for judgement. Thresholds per agent are
defined in each role `SKILL.md`.

## 6. Definition of sufficient evidence

A published claim normally requires: a verbatim span in a retained document, recorded
provenance, a confidence value, and — for material funding facts — corroboration as described
in `source-confidence.md`. Anything less is quarantined or sent to human review.
