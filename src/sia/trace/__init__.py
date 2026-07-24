"""Trace-first logging: append-only JSONL event logs plus run manifests (ADR-0003).

Every downstream module — evaluation, failure taxonomy, experience memory,
scaffold evolution — consumes traces. If it isn't in the trace, it didn't happen.
"""

from sia.trace.writer import (
    RunManifest,
    TraceWriter,
    config_hash,
    current_git_commit,
    read_jsonl,
    read_trace,
)

__all__ = [
    "RunManifest",
    "TraceWriter",
    "config_hash",
    "current_git_commit",
    "read_jsonl",
    "read_trace",
]
