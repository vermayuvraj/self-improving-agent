from __future__ import annotations

import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

TRUNCATION_MARKER = "\n...[output truncated]"


@dataclass
class ExecResult:
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool
    duration_ms: float

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + TRUNCATION_MARKER


def run_python(
    code: str,
    *,
    timeout_s: float = 10.0,
    max_output_chars: int = 20_000,
    python: str | None = None,
) -> ExecResult:
    """Run a Python program in an isolated temp directory.

    Uses ``-I`` (isolated mode: no user site, no env-var influence) and a
    fresh cwd per run. Known limits, accepted for M1: no memory/network caps,
    and on Windows grandchild processes may survive a timeout kill.
    """
    interpreter = python or sys.executable
    with tempfile.TemporaryDirectory(prefix="sia-exec-", ignore_cleanup_errors=True) as td:
        program = Path(td) / "main.py"
        program.write_text(code, encoding="utf-8")
        start = time.perf_counter()
        try:
            proc = subprocess.run(
                [interpreter, "-I", str(program)],
                cwd=td,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_s,
                check=False,
            )
            duration_ms = (time.perf_counter() - start) * 1000
            return ExecResult(
                exit_code=proc.returncode,
                stdout=_truncate(proc.stdout or "", max_output_chars),
                stderr=_truncate(proc.stderr or "", max_output_chars),
                timed_out=False,
                duration_ms=duration_ms,
            )
        except subprocess.TimeoutExpired as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            return ExecResult(
                exit_code=None,
                stdout=_truncate(_as_text(exc.stdout), max_output_chars),
                stderr=_truncate(_as_text(exc.stderr), max_output_chars),
                timed_out=True,
                duration_ms=duration_ms,
            )


def _as_text(data: str | bytes | None) -> str:
    if data is None:
        return ""
    if isinstance(data, bytes):
        return data.decode("utf-8", errors="replace")
    return data
