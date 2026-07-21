"""Print the failure taxonomy for one or more runs.

Thin CLI over ``sia.analysis`` (the logic moved into the package in M2).

Usage: uv run python scripts/analyze_failures.py [<run_id> ...]
"""

from __future__ import annotations

import sys
from pathlib import Path

from sia.analysis import analyze_run

RUNS_DIR = Path(__file__).resolve().parent.parent / "runs"


def main() -> None:
    run_ids = sys.argv[1:] or [p.name for p in sorted(RUNS_DIR.glob("*")) if p.is_dir()]
    for run_id in run_ids:
        try:
            report = analyze_run(run_id, runs_dir=RUNS_DIR)
        except (FileNotFoundError, KeyError) as exc:
            print(f"\n=== {run_id} === skipped ({type(exc).__name__})")
            continue
        failures = report.tasks - report.passed
        print(f"\n=== {report.run_id}  {report.bench}  {report.model} ===")
        print(f"tasks={report.tasks}  pass@1={report.pass_rate:.3f}  failures={failures}")
        if report.conditional_pass is not None:
            print(
                f"  ! {report.budget_exhausted} responses exhausted the token budget "
                f"without emitting code — pass@1 understates capability."
            )
            print(f"  conditional pass rate: {report.conditional_pass:.3f}")
        for label, n in report.taxonomy.items():
            share = n / failures * 100 if failures else 0
            print(f"  {label:<22} {n:>4}  ({share:.0f}% of failures)")


if __name__ == "__main__":
    main()
