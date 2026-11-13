# Source Confidence Reference

Defines how source reliability, corroboration, and reputation combine into the confidence
attached to claims and verdicts.

## 1. Tier weights

Base confidence weight by source tier (`SourceTier` in `src/aistartup_intel/models/enums.py`):

| Tier | Name | Base weight | Examples |
| --- | --- | --- | --- |
| A | Primary | 0.90 | SEC/registry filings, company/VC pages, pressrooms |
| B | Community / fast | 0.55 | HN, Product Hunt, X, GitHub, arXiv |
| C | Aggregator | 0.65 | Crunchbase, PitchBook, curated aggregators |

Weights are starting points, adjusted by corroboration and reputation (below). A Tier B fast
signal is not wrong — it is simply not sufficient on its own for material facts.

## 2. Corroboration requirements

- **Material funding facts** (amount, round type, lead investor) require at least one Tier A
  source, or two independent sources where at least one is Tier A or C and the other is
  independent.
- **Independent** means not derivative of the same origin (syndicated copy, re-blog, or the
  same press release reposted). Reposts do not count as independent corroboration.
- **Non-material facts** (a product feature, a blog post) may stand on a single Tier B source
  at Medium confidence.
- **Single-source, high-impact claims** are quarantined for human review rather than published.

## 3. Reputation tracking

Track per-source reputation over time:

- Historical accuracy (confirmed vs. later-corrected claims).
- Freshness and uptime (source health, access status).
- Extraction quality (how cleanly spans match retained text).
- Downstream correction rate attributable to the source.

Reputation nudges the base weight within its band; it never promotes a Tier B source to Tier A
reliability for material facts. Persistently unreliable sources are down-weighted or retired.

## 4. How confidence combines

For a claim supported by several independent sources:

1. Start from the strongest source's weight.
2. Increase modestly for each **independent** corroborating source (with diminishing returns),
   capped below certainty.
3. Apply reputation adjustments.
4. Decrease for indirect evidence, contradictions, stale timing, or weak spans.
5. Clamp to `[0.0, 1.0]`.

Contradicting sources do **not** average away. Both claims are kept; the conflict reduces
confidence and may trigger review.

## 5. Tiers of handling by combined confidence

- **High (>= 0.85)** — eligible for automatic publish where the agent's threshold allows.
- **Medium (0.60 – 0.84)** — publish for low-stakes items; corroborate further for material ones.
- **Low (0.40 – 0.59)** — route to review / hold.
- **Very low (< 0.40)** — do not publish; treat as a lead or a question.

## 6. Interaction with verification

The Verifier consumes these weights when assigning a `VerificationVerdict.confidence`. The
Scoring service uses source tier and corroboration count as factors. Neither may treat an
undisclosed or estimated amount as a verified numeric fact.
