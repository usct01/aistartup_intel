from __future__ import annotations

from sqlalchemy import select

from aistartup_intel.demo import run_demo
from aistartup_intel.store import db
from aistartup_intel.store import repository as repo
from aistartup_intel.store.tables import CompanyRow, FundingRoundRow


async def test_demo_pipeline_end_to_end(settings):
    summary = await run_demo(settings)

    # Five filings processed; the amended conflicting filing is rejected.
    assert len(summary.outcomes) == 5
    verdicts = [o["verdict"] for o in summary.outcomes]
    assert verdicts.count("publish") == 4
    assert verdicts.count("reject") == 1

    names = {c["name"] for c in summary.companies_over_threshold}
    assert names == {"MediCore AI", "LedgerMind", "LexPilot"}  # TinyVision below $10M

    assert summary.pending_reviews >= 1
    assert "update" in summary.newsletter["subject"]

    with db.session_scope(settings.database_url) as session:
        medicore = session.scalar(
            select(CompanyRow).where(CompanyRow.canonical_name == "MediCore AI")
        )
        assert medicore is not None
        rounds = repo.list_funding_rounds(session, company_id=medicore.id)
        # The rejected conflicting filing must NOT add a second round.
        assert len(rounds) == 1
        assert repo.company_total_disclosed_funding(session, medicore.id) == 25_000_000

        # Total rounds across all companies equals the published count.
        total_rounds = session.scalars(select(FundingRoundRow)).all()
        assert len(total_rounds) == 4


async def test_events_are_marked_processed(settings):
    await run_demo(settings)
    with db.session_scope(settings.database_url) as session:
        events = repo.list_events(session)
        assert events
        assert all(e.processed for e in events)
