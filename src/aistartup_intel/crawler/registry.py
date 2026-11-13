"""Source registry: the curated, policy-bound list of acquirable sources."""

from __future__ import annotations

from pathlib import Path

import yaml

from .policy import SourcePolicy


class SourceRegistry:
    def __init__(self, policies: list[SourcePolicy] | None = None) -> None:
        self._by_id: dict[str, SourcePolicy] = {}
        for policy in policies or []:
            self._by_id[policy.source_id] = policy

    def add(self, policy: SourcePolicy) -> None:
        self._by_id[policy.source_id] = policy

    def get(self, source_id: str) -> SourcePolicy | None:
        return self._by_id.get(source_id)

    def all(self) -> list[SourcePolicy]:
        return list(self._by_id.values())

    def enabled(self) -> list[SourcePolicy]:
        return [p for p in self._by_id.values() if p.enabled]

    @classmethod
    def from_yaml(cls, path: Path) -> SourceRegistry:
        data = yaml.safe_load(path.read_text()) or {}
        policies = [SourcePolicy(**entry) for entry in data.get("sources", [])]
        return cls(policies)

    @classmethod
    def default(cls) -> SourceRegistry:
        path = Path(__file__).resolve().parent.parent / "config" / "sources.yaml"
        if path.exists():
            return cls.from_yaml(path)
        return cls()
