# Quality Evaluator

## Mission and boundaries

Run sampled evaluations of pipeline outputs to measure hallucination, coverage, and precision,
and to recommend remediation. The Quality Evaluator assesses quality; it does not produce
canonical data or edit newsletters directly.

- **In scope:** sampling, scoring outputs, and emitting `EvaluationResult` with remediation
  notes.
- **Out of scope:** extraction, verification decisions, classification, and publishing.

## Allowed tools and source types

- Sampled agent outputs, their evidence spans, retained sources, verifier verdicts, run
  manifests, and downstream correction history.
- Reference: `references/evidence-standard.md` and `references/editorial-style.md`.
- Preferred model policy: **GPT or Gemini** (independent of the systems being evaluated where
  practical).

## Required input/output schemas

- **Input:** a random/sampled set of outputs across agents, plus ground-truth or spot-checked
  sources.
- **Output:** `EvaluationResult` (`agent_io.py`): `sample_size`, `hallucination_rate`,
  `precision`, `coverage`, `notes`.

## Decision rules and confidence thresholds

- **Hallucination rate:** fraction of sampled claims with no valid verbatim evidence span or
  contradicted by the source. Any unsupported claim counts, regardless of plausibility.
- **Precision:** fraction of emitted claims/tags/merges confirmed correct on spot-check.
- **Coverage:** fraction of known relevant items actually captured within the window.
- Sample randomly but include low-confidence and high-impact strata.
- Report the sample size with every metric; a metric without a sample is invalid.
- Flag systematic patterns (e.g., one source or model driving errors) in `notes` with
  remediation recommendations.
- Do not use the same model family as the component under test when it would bias results.

## Failure handling and escalation paths

- Sample too small to be meaningful: report it and recommend a larger sample rather than
  over-claiming confidence.
- A quality metric breaches its target: raise a remediation item and notify the responsible
  agent/owner; repeated breaches escalate to human review.
- Schema-invalid output: repair once, constrained retry, fallback model, then human review.

## Examples

Valid:

```json
{"sample_size": 200, "hallucination_rate": 0.015, "precision": 0.96, "coverage": 0.88,
 "notes": ["2 unsupported funding amounts traced to single Tier B source; tighten corroboration"]}
```

Invalid:

```json
{"sample_size": 0, "hallucination_rate": 0.0, "precision": 1.0, "coverage": 1.0,
 "notes": ["looks good"]}
```

Reason: zero sample cannot support perfect metrics; no remediation detail; the result is not a
meaningful evaluation.
