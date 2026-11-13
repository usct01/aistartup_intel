## Summary
<!-- Describe what this PR changes and why -->

## Type of Change
- [ ] Agent / Orchestrator logic (`src/aistartup_intel/agents/`)
- [ ] Crawler / Connectors (`crawler/`, `connectors/`)
- [ ] Storage / Ledger / Schema (`store/`, `models/`)
- [ ] API / Frontend (`api/`, `web/`)
- [ ] Docs / Skills / Config (`docs/`, `skills/`, `config/`)

## Architecture & Provenance Guarantees
- [ ] **Provenance by construction:** All extracted claims retain verbatim source spans.
- [ ] **Append-only ledger:** No existing facts are overwritten or mutated.
- [ ] **Compliant crawling:** Respects `robots.txt`, rate limits, and source policies.
- [ ] **Offline determinism:** Verified with `AISI_LLM_OFFLINE=true`.

## Verification
- [ ] `uv run ruff check src tests` passes
- [ ] `uv run mypy src` passes
- [ ] `uv run pytest` passes
- [ ] `uv run aistartup-intel demo` runs cleanly
