"""Command-line interface for the AI Startup Signal platform."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import typer

from .config.settings import get_settings
from .demo import run_demo
from .store import db
from .store import repository as repo

app = typer.Typer(help="AI Startup Signal — multi-agent startup & funding intelligence.")


@app.command("init-db")
def init_db() -> None:
    """Create the database schema (idempotent)."""
    db.init_db()
    typer.echo(f"initialized database at {get_settings().database_url}")


@app.command("demo")
def demo() -> None:
    """Run the offline end-to-end demo and print a summary."""
    summary = asyncio.run(run_demo())
    typer.echo("== outcomes ==")
    for outcome in summary.outcomes:
        typer.echo(
            f"  {outcome['verdict']:>9}  conf={outcome['confidence']:.2f}  "
            f"published={outcome['published']}  review={bool(outcome['review_id'])}  "
            f"{outcome.get('diagnostics') or ''}"
        )
    typer.echo("== companies over USD 10M disclosed ==")
    for company in summary.companies_over_threshold:
        typer.echo(f"  {company['name']}: ${company['total_disclosed_funding_usd']:,.0f}")
    typer.echo(f"== pending human reviews: {summary.pending_reviews} ==")
    typer.echo("== newsletter preview ==")
    typer.echo(f"  subject: {summary.newsletter.get('subject')}")
    for item in summary.newsletter.get("items", []):
        typer.echo(f"  - {item['company']}: {item['body']}")


@app.command("ingest")
def ingest(
    path: Path = typer.Argument(..., help="JSON file: list of Form D-like records"),
) -> None:
    """Ingest records from a JSON file through the agent pipeline."""
    records = json.loads(path.read_text())

    from .agents.base import PipelineContext
    from .agents.orchestrator import Orchestrator
    from .connectors import SECFormDConnector
    from .crawler import SourceRegistry
    from .llm.gateway import LLMGateway

    async def _run() -> list[dict[str, Any]]:
        settings = get_settings()
        db.init_db()
        registry = SourceRegistry.default()
        policy = registry.get("sec_form_d")
        assert policy is not None
        connector = SECFormDConnector(policy, records)
        events = [event async for event in connector.events()]
        with db.session_scope() as session:
            ctx = PipelineContext(
                settings=settings,
                llm=LLMGateway(settings=settings),
                run_id="ingest",
                session=session,
                registry=registry,
            )
            outcomes = await Orchestrator(ctx).process_events(events)
            return [
                {"event_id": o.event_id, "verdict": o.verdict.value if o.verdict else None,
                 "confidence": o.confidence, "published": o.published}
                for o in outcomes
            ]

    for result in asyncio.run(_run()):
        typer.echo(json.dumps(result))


@app.command("reviews")
def reviews(status: str = "pending") -> None:
    """List items in the human review queue."""
    with db.session_scope() as session:
        for row in repo.list_reviews(session, status=status):
            typer.echo(
                f"{row.id}  {row.summary}  conf={row.confidence:.2f}  status={row.status}"
            )


@app.command("serve")
def serve(host: str = "127.0.0.1", port: int = 8000, reload: bool = False) -> None:
    """Run the FastAPI server."""
    import uvicorn

    uvicorn.run("aistartup_intel.api.app:app", host=host, port=port, reload=reload)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
