from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from aistartup_intel.api.app import app, get_session
from aistartup_intel.models.domain import Company, FundingRound
from aistartup_intel.models.enums import FundingType, RoundType
from aistartup_intel.store import repository as repo


def _override(session):
    def _dep():
        yield session

    return _dep


def test_health():
    client = TestClient(app)
    assert client.get("/health").json()["status"] == "ok"


def test_companies_endpoint_respects_threshold(session):
    company = Company(canonical_name="Acme AI", url="https://acme.ai")
    repo.upsert_company(session, company)
    repo.add_funding_round(
        session,
        FundingRound(
            company_id=company.id,
            round_type=RoundType.SERIES_A,
            funding_type=FundingType.EQUITY,
            amount=25_000_000,
            amount_usd=25_000_000,
            announced_on=date(2026, 9, 1),
        ),
    )
    small = Company(canonical_name="Small Co", url="https://small.ai")
    repo.upsert_company(session, small)
    repo.add_funding_round(
        session,
        FundingRound(
            company_id=small.id,
            round_type=RoundType.SEED,
            funding_type=FundingType.EQUITY,
            amount=2_000_000,
            amount_usd=2_000_000,
        ),
    )
    session.flush()

    app.dependency_overrides[get_session] = _override(session)
    try:
        client = TestClient(app)
        resp = client.get("/companies", params={"min_total_funding_usd": 10_000_000})
        assert resp.status_code == 200
        names = [c["name"] for c in resp.json()["companies"]]
        assert names == ["Acme AI"]
    finally:
        app.dependency_overrides.clear()
