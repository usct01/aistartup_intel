"""Agent roster and orchestration."""

from .base import Agent, AgentRecord, PipelineContext
from .crawl_coordinator import CrawlCoordinator
from .entity_resolution import EntityResolver
from .evaluator import QualityEvaluator
from .extraction import DocumentExtractor
from .funding import FundingAnalyst
from .newsletter import NewsletterEditor
from .orchestrator import EventOutcome, Orchestrator, compose_newsletter
from .research import ResearchPlanner, SourceDiscovery
from .review import HumanReviewQueue
from .signals import SignalAnalyst
from .taxonomy import TaxonomyClassifier
from .verifier import Verifier

__all__ = [
    "Agent",
    "AgentRecord",
    "CrawlCoordinator",
    "DocumentExtractor",
    "EntityResolver",
    "EventOutcome",
    "FundingAnalyst",
    "HumanReviewQueue",
    "NewsletterEditor",
    "Orchestrator",
    "PipelineContext",
    "QualityEvaluator",
    "ResearchPlanner",
    "SignalAnalyst",
    "SourceDiscovery",
    "TaxonomyClassifier",
    "Verifier",
    "compose_newsletter",
]
