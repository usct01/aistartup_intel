"""Agent framework: typed, bounded workers orchestrated as a DAG.

Each agent declares a model role and exposes a single typed ``handle`` method.
Agents read shared context and return structured output; only the orchestrator's
validated workflows write canonical records.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from ..config.settings import Settings
from ..crawler.fetcher import CompliantFetcher
from ..crawler.registry import SourceRegistry
from ..llm.gateway import LLMGateway


@dataclass
class PipelineContext:
    settings: Settings
    llm: LLMGateway
    run_id: str
    session: Session | None = None
    fetcher: CompliantFetcher | None = None
    registry: SourceRegistry | None = None
    decisions: dict[str, object] = field(default_factory=dict)


@dataclass
class AgentRecord:
    agent: str
    model: str | None = None
    ok: bool = True
    detail: str = ""
    cost_usd: float = 0.0
    tokens: int = 0


class Agent[In, Out](ABC):
    name: str = "agent"
    model_role: str = "extractor"
    description: str = ""

    def __init__(self, llm: LLMGateway) -> None:
        self.llm = llm

    @property
    def model(self) -> str:
        return self.llm.model_for(self.model_role)

    @abstractmethod
    async def handle(self, ctx: PipelineContext, payload: In) -> Out: ...
