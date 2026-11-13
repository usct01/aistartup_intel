# Taxonomy Reference

Companies in AI Startup Signal are **multi-labelled**. A single company may simultaneously
hold a regulated **vertical**, an **AI capability layer**, a **buyer/workflow** category, and a
**maturity** category. Tags are represented by `TaxonomyTag` in
`src/aistartup_intel/models/domain.py`, where `axis` is one of `vertical`, `capability`,
`buyer`, or `maturity`.

This file summarises each axis and gives representative labels. **The full taxonomy in
`PLANV1.md` §"AI startup taxonomy" is authoritative**; when in doubt, defer to PLANV1 rather
than extending labels locally.

## Axis 1 — Vertical (regulated domain)

The regulated industry the company primarily serves. The launch verticals are
**healthcare, legal, and finance**, and the taxonomy is intentionally broader for later
expansion.

Representative labels:

- **Healthcare / life sciences** — clinical documentation and coding, care navigation, clinical
  decision support, drug discovery, diagnostics/imaging, genomics, clinical trials, payer tech.
- **Legal** — legal research, contract lifecycle management, e-discovery, litigation
  intelligence, drafting, compliance, investigations, IP, legal operations.
- **Finance** — fintech AI, wealth/asset management, trading and research, underwriting,
  lending, insurance, payments, fraud, AML/KYC, accounting, treasury, risk, regulatory tech.
- **Future expansions** — manufacturing, logistics, energy, climate, real estate, retail,
  agriculture, education, government, telecom, media, cybersecurity, defense, construction.

## Axis 2 — AI capability layer

Where the company sits in the AI stack (infrastructure through application).

Representative labels:

- **Foundation models and infrastructure** — general/domain/multimodal/small/open-source/
  sovereign models; hosting, inference, serving, routing, gateways, orchestration, caching,
  observability.
- **Agents and orchestration** — agent frameworks, runtimes, tool-use, memory, planning,
  workflow orchestration, agent evaluation.
- **Data and retrieval** — vector databases, RAG, knowledge graphs, enterprise search, data
  pipelines, labeling, synthetic data, marketplaces.
- **Model development** — fine-tuning, training platforms, RLHF/RLAIF, evaluation,
  benchmarking, prompt tooling, MLOps.
- **Compute and edge** — edge/on-device AI, chips, accelerators, networking, GPU cloud,
  data-center management, cooling, energy optimization, capacity marketplaces.
- **Trust, governance, and security** — governance, policy, model risk, audit, compliance,
  explainability, responsible AI, AI security, prompt-injection defense, red teaming, privacy,
  data-loss prevention, provenance/watermarking, deepfake detection, IP/copyright.

## Axis 3 — Buyer / workflow

Who buys it and what workflow it serves.

Representative labels:

- **Horizontal enterprise** — sales, marketing, support, HR, recruiting, procurement,
  operations, finance, analytics, IT, developer productivity, knowledge work.
- **Consumer / prosumer** — personal productivity, education, creativity, commerce, travel,
  media, gaming, communications.
- **Physical-world** — robotics, industrial automation, computer vision, digital twins,
  autonomous systems.

## Axis 4 — Maturity

The company's technical and commercial maturity (for example: research-stage, early, growth,
scaled). Maturity labels inform ranking and newsletter selection but never override evidence
quality.

## Labelling rules

- Assign labels with a `confidence` in `[0.0, 1.0]`; prefer a few high-confidence labels over
  exhaustive low-confidence ones.
- Multi-label is expected across axes, but avoid contradictory labels on the same axis.
- Uncertain label sets must set `uncertain = true` in `TaxonomyResult` and may be routed to a
  stronger model or human review.
- Do not invent labels. If the taxonomy does not cover a case, flag it for taxonomy review
  rather than creating a silent new label.
