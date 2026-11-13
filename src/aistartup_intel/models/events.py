"""The normalized event primitive that flows from ingestion to the agent pipeline.

Every event is provenance-stamped and carries zero or more *claims*. A claim is an
atomic assertion (e.g. ``raised_amount_usd = 4_000_000``) that must reference a verbatim
``evidence_span`` present in the retained source document. Claims without evidence are
rejected downstream by the Verifier.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .enums import EntityType, EventKind, SourceTier


def _utcnow() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return uuid4().hex


class Provenance(BaseModel):
    """Where a record came from and how it was obtained."""

    model_config = ConfigDict(frozen=True)

    url: str
    retrieved_at: datetime = Field(default_factory=_utcnow)
    connector_id: str
    connector_version: str = "0.1.0"
    http_status: int | None = None
    etag: str | None = None
    legal_note: str | None = None


class EvidenceSpan(BaseModel):
    """A verbatim passage in a source document that supports a claim."""

    model_config = ConfigDict(frozen=True)

    text: str = Field(min_length=1)
    start: int | None = None
    end: int | None = None
    document_uri: str | None = None


class EntityMention(BaseModel):
    """A named entity referenced by an event, before resolution to a canonical id."""

    name: str = Field(min_length=1)
    type: EntityType
    role: str | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class Claim(BaseModel):
    """An atomic, evidence-backed assertion extracted from a source."""

    predicate: str = Field(min_length=1)
    value: str | int | float | bool | None = None
    unit: str | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence: EvidenceSpan
    extracted_by: str | None = None

    @field_validator("predicate")
    @classmethod
    def _normalize_predicate(cls, v: str) -> str:
        return v.strip().lower().replace(" ", "_")


class RawRecord(BaseModel):
    """A raw, un-normalized payload as fetched from a source."""

    model_config = ConfigDict(frozen=True)

    source_id: str
    content: bytes
    content_type: str = "application/octet-stream"
    provenance: Provenance

    @property
    def content_hash(self) -> str:
        return "sha256:" + hashlib.sha256(self.content).hexdigest()


class Event(BaseModel):
    """A normalized signal ready for the agent pipeline."""

    event_id: str = Field(default_factory=new_id)
    source_id: str
    source_tier: SourceTier
    kind: EventKind
    observed_at: datetime = Field(default_factory=_utcnow)
    occurred_at: datetime | None = None
    title: str | None = None
    entity_mentions: list[EntityMention] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    raw_uri: str | None = None
    content_hash: str | None = None
    provenance: Provenance

    @property
    def is_funding(self) -> bool:
        return self.kind is EventKind.FUNDING

    def claim_values(self, predicate: str) -> list[Claim]:
        return [c for c in self.claims if c.predicate == predicate]


class ExtractedClaim(Claim):
    """A claim produced by extraction, optionally attached to a resolved entity."""

    entity_ref: str | None = None
