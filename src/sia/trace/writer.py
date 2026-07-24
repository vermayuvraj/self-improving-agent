from __future__ import annotations

import hashlib
import json
import subprocess
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Self

EVENT_TYPES = frozenset(
    {
        "task_start",
        "llm_call",
        "llm_response",
        "tool_call",
        "tool_result",
        "verdict",
        "error",
        "note",
    }
)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


def config_hash(config: dict[str, Any]) -> str:
    """Stable short hash of a config dict, independent of key order."""
    canonical = json.dumps(config, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()[:12]


def current_git_commit(cwd: Path | None = None) -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except OSError:
        return None
    return out.stdout.strip() if out.returncode == 0 else None


class TraceWriter:
    """Append-only JSONL event log for one run.

    Events carry a monotonically increasing ``seq`` so replays never depend
    on timestamp resolution. Unknown event types are rejected to keep the
    schema mineable by later modules.
    """

    def __init__(self, path: Path, run_id: str) -> None:
        self.path = path
        self.run_id = run_id
        self._seq = 0
        # Runs execute tasks concurrently (sia.parallel); without this lock,
        # interleaved writes would corrupt lines and duplicate seq numbers.
        self._lock = threading.Lock()
        path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = path.open("a", encoding="utf-8")

    def event(self, event_type: str, **data: Any) -> int:
        if event_type not in EVENT_TYPES:
            raise ValueError(f"unknown event type: {event_type!r}")
        with self._lock:
            record = {
                "run_id": self.run_id,
                "seq": self._seq,
                "ts": _now_iso(),
                "type": event_type,
                "data": data,
            }
            self._fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
            self._fh.flush()
            self._seq += 1
            return record["seq"]

    def close(self) -> None:
        self._fh.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL file written by ``TraceWriter`` / the run harness.

    Records are joined only by ``\\n`` (see ``TraceWriter.event``). Model
    output can contain exotic Unicode line separators (U+2028/U+2029/U+0085)
    that ``json.dumps`` does not escape; ``str.splitlines()`` *does* split on
    them, which shatters a valid record into unparseable fragments. Iterating
    the text-mode file handle splits on ``\\n`` (and ``\\r``) only, so it is
    the correct way to read these files — never ``.read_text().splitlines()``.
    """
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


# Backwards-compatible alias; ``read_trace`` predates the generalized name.
read_trace = read_jsonl


@dataclass
class RunManifest:
    """Everything needed to reproduce and account for a run."""

    run_id: str
    config: dict[str, Any]
    model: str
    seed: int | None
    created_at: str = field(default_factory=_now_iso)
    git_commit: str | None = field(default_factory=current_git_commit)
    config_hash: str = ""
    totals: dict[str, Any] = field(default_factory=dict)
    outcome: str = "running"

    def __post_init__(self) -> None:
        if not self.config_hash:
            self.config_hash = config_hash(self.config)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2, default=str), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> RunManifest:
        return cls(**json.loads(path.read_text(encoding="utf-8")))
