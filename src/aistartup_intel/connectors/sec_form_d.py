"""SEC EDGAR Form D connector.

Parses Form D filings (structured JSON or a normalized record) into funding Events.
A live EDGAR client would populate ``records`` upstream; offline it accepts records
directly so the pipeline is testable without network access.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterable
from datetime import date
from typing import Any

from ..crawler.policy import SourcePolicy
from ..models.enums import EntityType, EventKind, SourceTier
from ..models.events import Claim, EntityMention, Event, EvidenceSpan, Provenance, RawRecord
from .base import Connector, Cursor


class SECFormDConnector(Connector):
    source_id = "sec_form_d"
    version = "0.1.0"

    def __init__(self, policy: SourcePolicy, records: Iterable[dict[str, Any]] | None = None) -> None:
        super().__init__(policy)
        self._records = list(records or [])

    async def fetch(self, cursor: Cursor | None = None) -> AsyncIterator[RawRecord]:
        for record in self._records:
            content = json.dumps(record).encode()
            yield RawRecord(
                source_id=self.source_id,
                content=content,
                content_type="application/json",
                provenance=Provenance(
                    url=record.get("url", "https://www.sec.gov/cgi-bin/browse-edgar"),
                    connector_id=self.source_id,
                    connector_version=self.version,
                    legal_note=self.policy.legal_note,
                ),
            )

    def normalize(self, raw: RawRecord) -> Event:
        record = json.loads(raw.content)
        company = record.get("company_name", "Unknown")
        amount = record.get("amount_usd")
        announced = record.get("announced_on")
        if isinstance(announced, str):
            announced = date.fromisoformat(announced)
        investors: list[str] = list(record.get("investors", []))
        lead = record.get("lead_investor")
        text = record.get("text") or (
            f"{company} filed Form D for ${amount:,.0f}" if amount else company
        )

        claims: list[Claim] = []
        if amount is not None:
            claims.append(
                Claim(
                    predicate="raised_amount_usd",
                    value=float(amount),
                    unit="USD",
                    confidence=0.85,
                    evidence=EvidenceSpan(text=_span(text, "raised", f"${amount:,.0f}")),
                    extracted_by=self.source_id,
                )
            )
        claims.append(
            Claim(
                predicate="company_name",
                value=company,
                confidence=0.9,
                evidence=EvidenceSpan(text=company),
                extracted_by=self.source_id,
            )
        )
        if announced:
            claims.append(
                Claim(
                    predicate="announced_on",
                    value=announced.isoformat(),
                    confidence=0.8,
                    evidence=EvidenceSpan(text=announced.isoformat()),
                    extracted_by=self.source_id,
                )
            )
        if lead:
            claims.append(
                Claim(
                    predicate="lead_investor",
                    value=lead,
                    confidence=0.75,
                    evidence=EvidenceSpan(text=_span(text, "led by", lead)),
                    extracted_by=self.source_id,
                )
            )

        mentions = [
            EntityMention(name=company, type=EntityType.COMPANY, role="subject", confidence=0.9)
        ]
        mentions += [
            EntityMention(
                name=inv,
                type=EntityType.INVESTOR,
                role="lead" if inv == lead else "participant",
                confidence=0.7,
            )
            for inv in investors
        ]

        return Event(
            source_id=self.source_id,
            source_tier=SourceTier.PRIMARY,
            kind=EventKind.FUNDING,
            occurred_at=None,
            title=text,
            entity_mentions=mentions,
            claims=claims,
            raw_uri=None,
            content_hash=raw.content_hash,
            provenance=raw.provenance,
        )


def _span(text: str, anchor: str, fallback: str) -> str:
    """Return a verbatim-ish evidence span, preferring a text window around anchor."""
    lowered = text.lower()
    idx = lowered.find(anchor.lower())
    if idx == -1:
        return fallback if fallback in text else text
    start = max(0, idx - 20)
    end = min(len(text), idx + len(anchor) + 40)
    return text[start:end].strip()
