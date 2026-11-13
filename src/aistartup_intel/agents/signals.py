"""Signal Analyst agent: detects funding, hiring, product, and market signals."""

from __future__ import annotations

from typing import Any

from ..models.agent_io import SignalInput, SignalResult
from .base import Agent, PipelineContext

_KIND_TO_SIGNAL = {
    "funding": ("funding", 0.8),
    "hiring": ("hiring", 0.5),
    "product": ("product", 0.6),
    "launch": ("product", 0.6),
    "partnership": ("partnership", 0.6),
    "customer_win": ("commercial", 0.7),
    "regulatory": ("regulatory", 0.5),
    "oss_release": ("product", 0.5),
    "research": ("research", 0.4),
    "founder_move": ("team", 0.5),
}


class SignalAnalyst(Agent[SignalInput, SignalResult]):
    name = "signal-analyst"
    model_role = "analyst"
    description = "Detects funding velocity, hiring, product, competitive, regulatory signals."

    async def handle(self, ctx: PipelineContext, payload: SignalInput) -> SignalResult:
        signals: list[dict[str, Any]] = []
        counts: dict[str, int] = {}
        for kind in payload.event_kinds:
            mapped = _KIND_TO_SIGNAL.get(kind)
            if mapped is None:
                continue
            name, strength = mapped
            counts[name] = counts.get(name, 0) + 1
            signals.append(
                {
                    "kind": name,
                    "summary": f"{kind} signal for {payload.company_name}",
                    "strength": strength,
                }
            )

        # Funding velocity: multiple rounds in the window.
        if len(payload.funding_rounds) >= 2:
            signals.append(
                {
                    "kind": "funding_velocity",
                    "summary": f"{payload.company_name} raised {len(payload.funding_rounds)} rounds",
                    "strength": min(0.95, 0.5 + 0.15 * len(payload.funding_rounds)),
                }
            )
        return SignalResult(signals=signals)
