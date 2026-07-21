"""Classify failed tasks in a run into a coarse failure taxonomy.

Reads a run's trace + results and buckets each failure by the signal in the
sandbox stderr. This is the M2 failure-taxonomy prototype: it exists now
because EXP-001 needs failure analysis, and it stays small until M2 gives it
a real home.

Usage: uv run python scripts/analyze_failures.py <run_id> [<run_id> ...]
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = ROOT / "runs"


def classify(stderr: str, timed_out: bool, *, budget_exhausted: bool = False) -> str:
    """Bucket a failure. ``budget_exhausted`` takes priority over every runtime
    signal: if the model never finished emitting code, the downstream error is
    an artifact of truncation, not evidence about the model's reasoning."""
    if budget_exhausted:
        return "budget_exhausted"
    if timed_out:
        return "timeout"
    if not stderr.strip():
        return "no_stderr"
    if "SyntaxError" in stderr or "IndentationError" in stderr:
        return "syntax_error"
    if "NameError" in stderr:
        return "name_error"
    if "ImportError" in stderr or "ModuleNotFoundError" in stderr:
        return "import_error"
    if "TypeError" in stderr:
        return "type_error"
    if "IndexError" in stderr or "KeyError" in stderr:
        return "lookup_error"
    if "RecursionError" in stderr:
        return "recursion_error"
    if "AssertionError" in stderr or "assert" in stderr:
        return "wrong_answer"
    return "other_runtime_error"


def analyze(run_id: str) -> dict[str, object]:
    run_dir = RUNS_DIR / run_id
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    max_tokens = manifest["config"].get("max_tokens", 0)

    verdicts: dict[tuple[str, int], dict] = {}
    responses: dict[tuple[str, int], dict] = {}
    for line in (run_dir / "trace.jsonl").read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        data = event["data"]
        key = (data.get("task_id"), data.get("sample"))
        if event["type"] == "verdict":
            verdicts[key] = data
        elif event["type"] == "llm_response":
            responses[key] = data

    def exhausted(key: tuple[str, int]) -> bool:
        """The model spent its whole budget without closing a code block."""
        r = responses.get(key)
        if not r or not max_tokens:
            return False
        return r["completion_tokens"] >= max_tokens - 8 or "```" not in r["content"]

    failures = [(k, v) for k, v in verdicts.items() if not v["passed"]]
    counts = Counter(
        classify(
            v.get("stderr_tail", ""), v.get("timed_out", False), budget_exhausted=exhausted(k)
        )
        for k, v in failures
    )
    n_exhausted = counts.get("budget_exhausted", 0)
    scored = len(verdicts) - n_exhausted
    passed = sum(1 for v in verdicts.values() if v["passed"])
    return {
        "run_id": run_id,
        "bench": manifest["config"]["bench"],
        "model": manifest["model"],
        "tasks": len(verdicts),
        "pass@1": manifest["totals"].get("pass@1") or passed / max(len(verdicts), 1),
        "conditional_pass": passed / scored if scored else None,
        "budget_exhausted": n_exhausted,
        "failures": len(failures),
        "taxonomy": dict(counts.most_common()),
    }


def main() -> None:
    run_ids = sys.argv[1:] or [p.name for p in sorted(RUNS_DIR.glob("*")) if p.is_dir()]
    for run_id in run_ids:
        report = analyze(run_id)
        print(f"\n=== {report['run_id']}  {report['bench']}  {report['model']} ===")
        print(
            f"tasks={report['tasks']}  pass@1={report['pass@1']:.3f}  "
            f"failures={report['failures']}"
        )
        if report["budget_exhausted"]:
            print(
                f"  ! {report['budget_exhausted']} responses exhausted the token budget "
                f"without emitting code — pass@1 understates capability."
            )
            print(f"  conditional pass rate (excluding those): {report['conditional_pass']:.3f}")
        for label, n in report["taxonomy"].items():
            share = n / report["failures"] * 100 if report["failures"] else 0
            print(f"  {label:<22} {n:>4}  ({share:.0f}% of failures)")


if __name__ == "__main__":
    main()
