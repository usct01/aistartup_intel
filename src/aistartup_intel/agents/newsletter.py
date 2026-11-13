"""Newsletter Editor agent: selects verified updates and drafts investor editions."""

from __future__ import annotations

from datetime import UTC, datetime

from ..models.agent_io import NewsletterDraft, NewsletterInput, NewsletterItem
from .base import Agent, PipelineContext

_MAX_ITEMS = 8


class NewsletterEditor(Agent[NewsletterInput, NewsletterDraft]):
    name = "newsletter-editor"
    model_role = "editor"
    description = "Selects verified updates per subscriber and drafts concise editions."

    async def handle(self, ctx: PipelineContext, payload: NewsletterInput) -> NewsletterDraft:
        eligible = [i for i in payload.items if i.confidence >= 0.5 and i.evidence_urls]
        ranked = sorted(
            eligible, key=lambda i: (i.score or 0.0, i.confidence), reverse=True
        )[:_MAX_ITEMS]

        items: list[NewsletterItem] = []
        for item in ranked:
            items.append(
                item.model_copy(
                    update={"body": _render(item)}
                )
            )

        verticals = payload.verticals or ["all"]
        pulse = {v: f"{len(items)} verified update(s)" for v in verticals}
        subject = f"AI Startup Signal — {', '.join(verticals)} — {len(items)} update(s)"
        return NewsletterDraft(
            subject=subject,
            vertical_pulse=pulse,
            items=items,
            generated_at=datetime.now(UTC),
        )


def _render(item: NewsletterItem) -> str:
    links = " ".join(f"[{i + 1}]" for i, _ in enumerate(item.evidence_urls))
    return f"{item.body} {links}".strip()
