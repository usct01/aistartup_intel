"""Connector contract: raw acquisition -> normalized Event."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass

from ..crawler.fetcher import CompliantFetcher
from ..crawler.policy import SourcePolicy
from ..models.events import Event, RawRecord


@dataclass
class Cursor:
    value: str | None = None


class Connector(ABC):
    source_id: str
    version: str = "0.1.0"

    def __init__(self, policy: SourcePolicy, fetcher: CompliantFetcher | None = None) -> None:
        self.policy = policy
        self.fetcher = fetcher

    @abstractmethod
    def fetch(self, cursor: Cursor | None = None) -> AsyncIterator[RawRecord]:
        """Yield raw records from the source, honoring the source policy."""

    @abstractmethod
    def normalize(self, raw: RawRecord) -> Event:
        """Convert a raw record into a normalized, provenance-stamped Event."""

    async def events(self, cursor: Cursor | None = None) -> AsyncIterator[Event]:
        async for raw in self.fetch(cursor):
            yield self.normalize(raw)
