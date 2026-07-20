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


def classify(stderr: str, timed_out: bool) -> str:
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
    verdicts = {}
    for line in (run_dir / "trace.jsonl").read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event["type"] == "verdict":
            data = event["data"]
            verdicts[(data["task_id"], data["sample"])] = data

    failures = [v for v in verdicts.values() if not v["passed"]]
    counts = Counter(
        classify(v.get("stderr_tail", ""), v.get("timed_out", False)) for v in failures
    )
    return {
        "run_id": run_id,
        "bench": manifest["config"]["bench"],
        "model": manifest["model"],
        "tasks": manifest["totals"]["tasks"],
        "pass@1": manifest["totals"]["pass@1"],
        "failures": len(failures),
        "taxonomy": dict(counts.most_common()),
        "examples": [
            {"task_id": v["task_id"], "stderr_tail": (v.get("stderr_tail") or "")[-300:]}
            for v in failures[:3]
        ],
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
        for label, n in report["taxonomy"].items():
            share = n / report["failures"] * 100 if report["failures"] else 0
            print(f"  {label:<22} {n:>4}  ({share:.0f}% of failures)")


if __name__ == "__main__":
    main()
