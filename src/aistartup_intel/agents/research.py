"""Research Planner and Source Discovery agents."""

from __future__ import annotations

import hashlib

from ..models.agent_io import (
    CoverageRequest,
    DiscoveryResult,
    ResearchPlan,
    ResearchTask,
    SourceCandidate,
)
from ..models.enums import SourceTier
from .base import Agent, PipelineContext


def _task_id(vertical: str, query: str) -> str:
    return hashlib.sha1(f"{vertical}|{query}".encode()).hexdigest()[:12]


class ResearchPlanner(Agent[CoverageRequest, ResearchPlan]):
    name = "research-planner"
    model_role = "planner"
    description = "Turns coverage goals and gaps into concrete source/research tasks."

    async def handle(self, ctx: PipelineContext, payload: CoverageRequest) -> ResearchPlan:
        tasks: list[ResearchTask] = []
        for gap in payload.gaps:
            tasks.append(
                ResearchTask(
                    task_id=_task_id("gap", gap),
                    vertical="cross",
                    query=f"new AI startups addressing: {gap}",
                    rationale="Close a known coverage gap.",
                    priority=2,
                )
            )
        for vertical in payload.verticals:
            for category in payload.categories or ["foundation models", "vertical agents"]:
                query = f"recent funding for {vertical} AI {category} startups"
                tasks.append(
                    ResearchTask(
                        task_id=_task_id(vertical, query),
                        vertical=vertical,
                        category=category,
                        query=query,
                        rationale=f"Fresh coverage for {vertical}/{category}.",
                        priority=3,
                    )
                )
        tasks = tasks[: payload.max_tasks]
        return ResearchPlan(
            tasks=tasks,
            coverage_notes=f"{len(tasks)} tasks across {len({t.vertical for t in tasks})} verticals",
        )


# A small, curated seed set of high-signal discovery targets. In production the
# Source Discovery agent expands this via search APIs and portfolio pages.
_SEED_TARGETS: dict[str, list[str]] = {
    "healthcare": ["https://www.fiercehealthcare.com", "https://www.statnews.com"],
    "legal": ["https://www.law.com", "https://www.artificiallawyer.com"],
    "finance": ["https://www.finextra.com", "https://www.fintechfutures.com"],
}


class SourceDiscovery(Agent[ResearchTask, DiscoveryResult]):
    name = "source-discovery"
    model_role = "classifier_hard"
    description = "Finds official, press, registry, feed, and reputable reporting sources."

    async def handle(self, ctx: PipelineContext, payload: ResearchTask) -> DiscoveryResult:
        candidates: list[SourceCandidate] = []
        for url in _SEED_TARGETS.get(payload.vertical, []):
            candidates.append(
                SourceCandidate(
                    url=url,
                    source_type="news",
                    tier=SourceTier.AGGREGATOR.value,
                    title=url,
                    rationale=f"Reputable trade source for {payload.vertical}.",
                )
            )
        if ctx.registry:
            for policy in ctx.registry.enabled():
                if policy.base_url:
                    candidates.append(
                        SourceCandidate(
                            url=policy.base_url,
                            source_type=policy.source_type,
                            tier=policy.tier.value,
                            title=policy.name,
                            rationale="Registered source.",
                        )
                    )
        return DiscoveryResult(
            candidates=candidates,
            diagnostics=[f"discovered {len(candidates)} candidates"],
        )
