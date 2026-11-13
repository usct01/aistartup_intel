"""A connector over in-memory Events. Used for tests, demos, and backfills."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterable

from ..crawler.policy import SourcePolicy
from ..models.events import Event, RawRecord
from .base import Connector, Cursor


class StaticConnector(Connector):
    def __init__(self, policy: SourcePolicy, events: Iterable[Event]) -> None:
        super().__init__(policy)
        self.source_id = policy.source_id
        self._events = list(events)

    async def fetch(self, cursor: Cursor | None = None) -> AsyncIterator[RawRecord]:
        return
        yield  # pragma: no cover - no raw records; events() is overridden

    def normalize(self, raw: RawRecord) -> Event:
        raise NotImplementedError

    async def events(self, cursor: Cursor | None = None) -> AsyncIterator[Event]:
        for event in self._events:
            yield event
