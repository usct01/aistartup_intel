"""Async per-domain token-bucket rate limiter with jittered spacing."""

from __future__ import annotations

import asyncio
import random
import time


class DomainRateLimiter:
    def __init__(self, default_rps: float = 1.0) -> None:
        self._default_rps = default_rps
        self._locks: dict[str, asyncio.Lock] = {}
        self._next_allowed: dict[str, float] = {}
        self._rps: dict[str, float] = {}

    def configure(self, domain: str, rps: float) -> None:
        self._rps[domain] = max(rps, 0.01)

    def _lock(self, domain: str) -> asyncio.Lock:
        return self._locks.setdefault(domain, asyncio.Lock())

    async def acquire(self, domain: str) -> float:
        """Block until a request to ``domain`` is permitted. Returns waited seconds."""
        async with self._lock(domain):
            rps = self._rps.get(domain, self._default_rps)
            interval = 1.0 / rps
            now = time.monotonic()
            next_at = self._next_allowed.get(domain, now)
            wait = max(0.0, next_at - now)
            # Add small jitter to avoid synchronized bursts.
            wait += random.uniform(0, interval * 0.1)
            if wait > 0:
                await asyncio.sleep(wait)
            self._next_allowed[domain] = time.monotonic() + interval
            return wait
