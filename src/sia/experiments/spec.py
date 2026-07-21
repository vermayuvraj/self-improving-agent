from __future__ import annotations

import itertools
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sia.bench import BENCHMARKS

# Axes are ordered so grid expansion is deterministic; a spec must always
# produce the same cell sequence for the same file.
AXES = ("model", "bench", "condition", "repair_k")


@dataclass(frozen=True)
class GridCell:
    """One (model, bench, condition, repair_k) combination — a single run."""

    model: str
    bench: str
    condition: str = "none"
    repair_k: int = 0

    def label(self) -> str:
        return f"{self.model}|{self.bench}|{self.condition}|k={self.repair_k}"


@dataclass
class ExperimentSpec:
    """A declarative experiment: axes, shared run settings, and metadata."""

    id: str
    title: str
    hypothesis: str = ""
    models: list[str] = field(default_factory=list)
    benches: list[str] = field(default_factory=list)
    conditions: list[str] = field(default_factory=lambda: ["none"])
    repair_ks: list[int] = field(default_factory=lambda: [0])
    seed: int = 7
    samples: int = 1
    temperature: float = 0.0
    max_tokens: int = 2048
    exec_timeout_s: float = 60.0
    limit: int | None = None

    def __post_init__(self) -> None:
        if not self.models:
            raise ValueError(f"{self.id}: at least one model required")
        if not self.benches:
            raise ValueError(f"{self.id}: at least one benchmark required")
        unknown = set(self.benches) - set(BENCHMARKS)
        if unknown:
            raise ValueError(f"{self.id}: unknown benchmark(s): {sorted(unknown)}")
        if any(k < 0 for k in self.repair_ks):
            raise ValueError(f"{self.id}: repair_k values must be non-negative")

    def grid(self) -> list[GridCell]:
        return [
            GridCell(model=m, bench=b, condition=c, repair_k=k)
            for m, b, c, k in itertools.product(
                self.models, self.benches, self.conditions, self.repair_ks
            )
        ]

    def run_kwargs(self) -> dict[str, Any]:
        """Settings shared by every cell — the controlled part of the design."""
        return {
            "seed": self.seed,
            "samples": self.samples,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "exec_timeout_s": self.exec_timeout_s,
            "limit": self.limit,
        }


def load_spec(path: Path) -> ExperimentSpec:
    """Load a TOML experiment spec (stdlib tomllib — no YAML dependency)."""
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    known = set(ExperimentSpec.__dataclass_fields__)
    unknown = set(data) - known
    if unknown:
        raise ValueError(f"unknown spec field(s): {sorted(unknown)}")
    return ExperimentSpec(**data)
