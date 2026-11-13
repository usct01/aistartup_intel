"""RSS/Atom feed connector. Parses entries into launch/funding events."""

from __future__ import annotations

import re
from collections.abc import AsyncIterator, Iterable
from datetime import datetime

import feedparser

from ..crawler.policy import SourcePolicy
from ..models.enums import EntityType, EventKind
from ..models.events import Claim, EntityMention, Event, EvidenceSpan, Provenance, RawRecord
from .base import Connector, Cursor

_MONEY = re.compile(r"\$\s?([\d,.]+)\s?(million|billion|m|b|k)?", re.IGNORECASE)
_MULT = {"million": 1e6, "m": 1e6, "billion": 1e9, "b": 1e9, "k": 1e3, None: 1.0}


class RSSConnector(Connector):
    source_id = "rss"

    def __init__(self, policy: SourcePolicy, payloads: Iterable[bytes] | None = None) -> None:
        super().__init__(policy)
        self.source_id = policy.source_id
        self._payloads = list(payloads or [])

    async def fetch(self, cursor: Cursor | None = None) -> AsyncIterator[RawRecord]:
        for payload in self._payloads:
            yield RawRecord(
                source_id=self.source_id,
                content=payload,
                content_type="application/rss+xml",
                provenance=Provenance(
                    url=policy_url(self.policy),
                    connector_id=self.source_id,
                    legal_note=self.policy.legal_note,
                ),
            )

    def normalize(self, raw: RawRecord) -> Event:
        feed = feedparser.parse(raw.content)
        entries = feed.entries or []
        first = entries[0] if entries else {}
        title = first.get("title", "untitled")
        summary = first.get("summary", "")
        text = f"{title}. {summary}".strip()
        link = first.get("link") or policy_url(self.policy)
        occurred = None
        if first.get("published_parsed"):
            occurred = datetime(*first["published_parsed"][:6])

        claims: list[Claim] = [
            Claim(
                predicate="headline",
                value=title,
                confidence=0.6,
                evidence=EvidenceSpan(text=title),
                extracted_by=self.source_id,
            )
        ]
        amount = _parse_money(text)
        if amount:
            claims.append(
                Claim(
                    predicate="raised_amount_usd",
                    value=amount,
                    confidence=0.5,
                    evidence=EvidenceSpan(text=_money_span(text)),
                    extracted_by=self.source_id,
                )
            )
        kind = EventKind.FUNDING if amount else EventKind.LAUNCH
        return Event(
            source_id=self.source_id,
            source_tier=self.policy.tier,
            kind=kind,
            occurred_at=occurred,
            title=title,
            entity_mentions=[EntityMention(name=title[:120], type=EntityType.COMPANY, confidence=0.4)],
            claims=claims,
            content_hash=raw.content_hash,
            provenance=Provenance(url=link, connector_id=self.source_id),
        )


def policy_url(policy: SourcePolicy) -> str:
    return policy.base_url or f"https://{policy.source_id}"


def _parse_money(text: str) -> float | None:
    match = _MONEY.search(text)
    if not match:
        return None
    try:
        value = float(match.group(1).replace(",", ""))
    except ValueError:
        return None
    return value * _MULT.get((match.group(2) or "").lower(), 1.0)


def _money_span(text: str) -> str:
    match = _MONEY.search(text)
    if not match:
        return text[:80]
    return text[max(0, match.start() - 20) : match.end() + 20].strip()
