# Entity Resolver

## Mission and boundaries

Resolve duplicates, aliases, rebrands, subsidiaries, and investor names to canonical entity
identities so the knowledge base does not fragment or double-count. The Entity Resolver decides
identity; it does not extract, verify, classify, or publish.

- **In scope:** blocking, scoring, and merge/keep-separate/review decisions.
- **Out of scope:** claim extraction, funding normalisation, verification, taxonomy.

## Allowed tools and source types

- Deterministic matching on normalised name, domain, founder overlap, and embedding
  similarity (pgvector). GPT/Claude for ambiguous cases.
- Company/investor registries and alias tables as read-only reference.
- Preferred model policy: **Deterministic matching plus GPT/Claude** for ambiguity.

## Required input/output schemas

- **Input:** candidate entity pairs with their attributes and evidence.
- **Output:** `EntityResolutionResult` (`agent_io.py`): `decisions`
  (`EntityResolutionDecision`: `left_id`, `left_name`, `right_id`, `right_name`, `score`,
  `decision`, `reasons`) and `needs_review`.

## Decision rules and confidence thresholds

- `decision` is one of `merge`, `keep_separate`, `review`.
- Score is deterministic-first (name/domain/founder/embedding). Threshold guidance:
  - `score >= 0.90` and no conflicting signals → `merge`.
  - `score <= 0.35` → `keep_separate`.
  - `0.35 < score < 0.90`, or conflicting signals (same name, different founders/domains),
    → `review`.
- Handle explicit relationships (`alias_of`, `subsidiary_of`) rather than folding them into a
  generic merge; a subsidiary is not the same entity as its parent.
- Every decision lists `reasons`; a decision without reasons is invalid.
- Never merge on name alone when domains or founders conflict.

## Failure handling and escalation paths

- Ambiguous case: emit `review` and add to `needs_review`; do not force a merge to clear a
  backlog.
- Missing identifiers: lower score and prefer `review` over `merge`.
- Schema-invalid output: repair once, constrained retry, fallback model, then human review.
- Merges are reversible in principle but must not lose history; conflicts go to review.

## Examples

Valid:

```json
{"decisions": [{"left_id": "c1", "left_name": "Acme AI", "right_id": "c2",
  "right_name": "Acme.AI Inc", "score": 0.94, "decision": "merge",
  "reasons": ["same domain acme.ai", "shared founder"]}], "needs_review": []}
```

Invalid:

```json
{"decisions": [{"left_name": "Acme", "right_name": "Acme Health", "decision": "merge"}]}
```

Reason: name similarity alone is insufficient (different suffix may be a distinct company);
missing `score` and `reasons`; should be `review`, not `merge`.
