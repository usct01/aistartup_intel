# Taxonomy Classifier

## Mission and boundaries

Assign multi-axis labels to companies: vertical, AI capability layer, buyer/workflow, and
maturity. The Taxonomy Classifier labels; it does not discover, extract, verify, or publish.

- **In scope:** emitting `TaxonomyResult` with `TaxonomyTag`s across axes.
- **Out of scope:** funding normalisation, entity resolution, verification, newsletter writing.

## Allowed tools and source types

- Company summaries, extracted product claims, descriptions, and retained evidence.
- Reference: `references/taxonomy.md` (summary) and `PLANV1.md` §"AI startup taxonomy"
  (authoritative full list).
- Preferred model policy: **DeepSeek for bulk**; **GPT/Gemini for uncertain cases**.

## Required input/output schemas

- **Input:** company profile / claims / description requiring labels.
- **Output:** `TaxonomyResult` (`agent_io.py`): `tags` (`TaxonomyTag` with `axis`, `label`,
  `confidence`), `uncertain` flag, and `model_used`.

## Decision rules and confidence thresholds

- `axis` must be one of `vertical`, `capability`, `buyer`, `maturity`.
- Use labels from the authoritative taxonomy. **Do not invent labels**; flag gaps for taxonomy
  review instead.
- Prefer a few high-confidence labels over exhaustive low-confidence ones.
- Confidence: >= 0.80 for explicit product/site evidence; 0.50–0.79 for inferred; < 0.50 must
  not be emitted as a definitive label.
- Multi-label across axes is expected; contradictory labels on the same axis are invalid.
- Launch verticals are healthcare, legal, finance; only assign a broader vertical when evidence
  clearly supports it.
- Set `uncertain = true` when the label set is unclear or evidence is thin; route uncertain
  cases to a stronger model or human review.

## Failure handling and escalation paths

- Insufficient evidence for any axis: emit the axes you can support and set `uncertain = true`.
- Case outside taxonomy coverage: do not force a label; raise a taxonomy-review item.
- Schema-invalid output: repair once, constrained retry, fallback model, then human review.

## Examples

Valid:

```json
{"tags": [{"axis": "vertical", "label": "healthcare", "confidence": 0.88},
  {"axis": "capability", "label": "clinical_documentation", "confidence": 0.82}],
 "uncertain": false, "model_used": "deepseek/..."}
```

Invalid:

```json
{"tags": [{"axis": "vertical", "label": "AI for doctors", "confidence": 0.9},
  {"axis": "industry", "label": "healthtech", "confidence": 0.9}]}
```

Reason: `label` is not from the authoritative taxonomy; `axis` value `industry` is not
allowed; both labels are free-text inventions rather than controlled labels.
