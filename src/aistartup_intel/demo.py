"""Deterministic sample data and an end-to-end demo pipeline run.

Runs entirely offline: no network, no API key. Demonstrates discovery ->
extraction -> funding normalization -> taxonomy -> verification -> scoring ->
newsletter, with provenance ledger and human-review routing.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from .agents.base import PipelineContext
from .agents.newsletter import NewsletterEditor
from .agents.orchestrator import EventOutcome, Orchestrator
from .config.settings import Settings, get_settings
from .connectors import SECFormDConnector
from .crawler import SourceRegistry
from .llm.gateway import LLMGateway
from .models.agent_io import NewsletterInput, NewsletterItem
from .store import db
from .store import repository as repo

SAMPLE_FILINGS: list[dict[str, Any]] = [
    {
        "company_name": "MediCore AI",
        "amount_usd": 25_000_000,
        "announced_on": "2026-09-15",
        "url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=medicore",
        "investors": ["Sequoia", "Andreessen Horowitz"],
        "lead_investor": "Sequoia",
        "text": "MediCore AI raised $25M Series A led by Sequoia to automate clinical "
        "documentation and patient triage for health systems.",
    },
    {
        "company_name": "LexPilot",
        "amount_usd": 12_000_000,
        "announced_on": "2026-09-18",
        "url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=lexpilot",
        "investors": ["Index Ventures"],
        "lead_investor": "Index Ventures",
        "text": "LexPilot raised $12M seed led by Index Ventures for AI legal research "
        "and contract lifecycle management.",
    },
    {
        "company_name": "LedgerMind",
        "amount_usd": 40_000_000,
        "announced_on": "2026-09-20",
        "url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=ledgermind",
        "investors": ["Ribbit Capital", "QED Investors"],
        "lead_investor": "Ribbit Capital",
        "text": "LedgerMind raised $40M Series B led by Ribbit Capital for AI underwriting "
        "and AML/KYC compliance in fintech.",
    },
    {
        "company_name": "TinyVision Labs",
        "amount_usd": 3_000_000,
        "announced_on": "2026-09-21",
        "url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=tinyvision",
        "investors": ["Angel Collective"],
        "lead_investor": "Angel Collective",
        "text": "TinyVision Labs raised $3M pre-seed for on-device computer vision in manufacturing.",
    },
    {
        "company_name": "MediCore AI",
        "amount_usd": 30_000_000,
        "announced_on": "2026-09-22",
        "url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=medicore2",
        "investors": ["Sequoia"],
        "lead_investor": "Sequoia",
        "text": "MediCore AI raised $30M Series A led by Sequoia, per an amended filing.",
    },
]


@dataclass
class DemoSummary:
    outcomes: list[dict[str, Any]] = field(default_factory=list)
    companies_over_threshold: list[dict[str, Any]] = field(default_factory=list)
    pending_reviews: int = 0
    newsletter: dict[str, Any] = field(default_factory=dict)
    run_manifests: int = 0


async def run_demo(settings: Settings | None = None) -> DemoSummary:
    settings = settings or get_settings()
    db.init_db(settings.database_url)
    llm = LLMGateway(settings=settings)
    registry = SourceRegistry.default()
    policy = registry.get("sec_form_d")
    assert policy is not None
    connector = SECFormDConnector(policy, SAMPLE_FILINGS)
    events = [event async for event in connector.events()]

    summary = DemoSummary()
    with db.session_scope(settings.database_url) as session:
        ctx = PipelineContext(
            settings=settings, llm=llm, run_id="demo", session=session, registry=registry
        )
        orchestrator = Orchestrator(ctx)
        outcomes: list[EventOutcome] = await orchestrator.process_events(events)
        summary.outcomes = [asdict(o) for o in outcomes]

        over_threshold = repo.list_companies(
            session, min_total_funding_usd=settings.funding_threshold_usd
        )
        for company, total in over_threshold:
            summary.companies_over_threshold.append(
                {"name": company.canonical_name, "total_disclosed_funding_usd": total}
            )
        summary.pending_reviews = len(repo.list_reviews(session, status="pending"))

        items: list[NewsletterItem] = []
        for company, total in repo.list_companies(session, limit=20):
            items.append(
                NewsletterItem(
                    company=company.canonical_name,
                    headline=f"{company.canonical_name} update",
                    body=f"Total disclosed funding ${total:,.0f}.",
                    confidence=company.confidence,
                    evidence_urls=[company.url] if company.url else [],
                    score=min(1.0, total / 100_000_000),
                )
            )
        draft = await NewsletterEditor(llm).handle(
            ctx,
            NewsletterInput(
                user_email="demo@example.com",
                verticals=["healthcare", "legal", "finance"],
                items=items,
                edition_date=datetime.now(UTC).date(),
            ),
        )
        summary.newsletter = draft.model_dump(mode="json")
        summary.run_manifests = len(outcomes)
    return summary
