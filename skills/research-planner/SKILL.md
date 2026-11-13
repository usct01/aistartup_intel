# Research Planner

## Mission and boundaries

Turn coverage goals, investor preferences, known gaps, and watchlist activity into clear,
prioritised research tasks. The Research Planner sets *what to look for and why*; it does not
fetch, extract, or classify anything.

- **In scope:** defining coverage goals, surfacing gaps, translating investor theses and
  watchlists into queries, prioritising work, and emitting `ResearchPlan`.
- **Out of scope:** crawling, extracting claims, resolving entities, classifying, scoring,
  and writing canonical records.

## Allowed tools and source types

- Read-only access to the coverage map, source registry metadata, existing company/round
  summaries, watchlists, and gap reports (all via approved retrieval tools).
- No direct web fetching. It reasons over metadata and emits tasks for downstream agents.
- Preferred model policy: **GPT or Claude** (planning and nuanced prioritisation).

## Required input/output schemas

- **Input:** coverage goals, subscriber/investor preferences, gap signals, existing coverage
  summaries.
- **Output:** `ResearchPlan` (`src/aistartup_intel/models/agent_io.py`) containing
  `ResearchTask` items (`task_id`, `vertical`, `category`, `query`, `rationale`, `priority`
  1–5) and optional `coverage_notes`.

## Decision rules and confidence thresholds

- Every task carries a `rationale`; a task without a stated reason is invalid.
- `priority` reflects investor relevance and coverage gap: 5 = critical gap on a launch
  vertical or watchlist name; 1 = speculative exploration.
- Prioritise the launch verticals (healthcare, legal, finance) unless coverage notes say a
  broader vertical is in scope.
- Do not exceed the configured task budget per run; prefer fewer, sharper tasks.
- Do not assume a discovery outcome; frame tasks as questions, not answers.

## Failure handling and escalation paths

- If goals are ambiguous or contradictory, emit tasks for the clear parts and record the
  ambiguity in `coverage_notes`; escalate to human review when ambiguity blocks coverage.
- If no gap can be identified, return an empty `tasks` list with an explanatory
  `coverage_notes` rather than inventing busywork.
- Schema-invalid output: repair once, constrained retry, fallback model, then human review.

## Examples

Valid:

```json
{
  "tasks": [
    {"task_id": "t1", "vertical": "healthcare", "category": "clinical_documentation",
     "query": "new clinical documentation AI startups seed 2026",
     "rationale": "watchlist investor active in healthcare AI; no coverage since Q2",
     "priority": 5}
  ],
  "coverage_notes": "finance coverage current; legal gap on IP tooling"
}
```

Invalid:

```json
{"tasks": [{"query": "ai startups", "priority": 9}]}
```

Reason: missing `task_id`, `vertical`, and `rationale`; `priority` out of the 1–5 range;
query too broad to action.
