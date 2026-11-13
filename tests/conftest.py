from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session

from aistartup_intel.config.settings import Settings
from aistartup_intel.store import db


@pytest.fixture
def db_url(tmp_path) -> str:
    return f"sqlite+pysqlite:///{tmp_path / 'test.db'}"


@pytest.fixture
def settings(db_url, tmp_path) -> Settings:
    return Settings(
        database_url=db_url,
        llm_offline=True,
        object_store_dir=tmp_path / "objects",
        funding_threshold_usd=10_000_000,
    )


@pytest.fixture
def session(db_url) -> Iterator[Session]:
    db.init_db(db_url)
    with db.session_scope(db_url) as s:
        yield s
