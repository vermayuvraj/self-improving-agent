"""EXP-005: is anchoring the mechanism behind EXP-004?

If conditioning on the failed attempt biases sampling toward minor edits of a
wrong approach, then feedback/placebo arms should show *lower* diversity
between consecutive attempts than blind resampling. Measured on traces
already collected — no new inference required.
"""

from __future__ import annotations

import difflib
import json
import statistics
from collections import defaultdict
from pathlib import Path

from sia.bench import extract_code

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
CELLS = json.loads((ROOT / "experiments" / "EXP-004" / "cells.json").read_text(encoding="utf-8"))

MODELS = ["qwen2.5-coder:1.5b-instruct", "qwen2.5-coder:3b-instruct", "qwen2.5-coder:7b"]
CONDITIONS = ["resample", "placebo", "feedback", "reflect"]


def similarity(a: str, b: str) -> float:
    """1.0 = identical attempts, 0.0 = nothing in common."""
    return difflib.SequenceMatcher(None, a, b).ratio()


def arm_diversity(run_id: str) -> tuple[float, float, int]:
    """Mean consecutive-attempt similarity, and share of near-identical retries."""
    by_task: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for line in (RUNS / run_id / "trace.jsonl").read_text(encoding="utf-8").splitlines():
        e = json.loads(line)
        if e["type"] != "llm_response":
            continue
        d = e["data"]
        by_task[d["task_id"]].append((d["iteration"], extract_code(d["content"])))

    sims = []
    for attempts in by_task.values():
        attempts.sort()
        for (_, prev), (_, cur) in zip(attempts, attempts[1:], strict=False):
            if prev.strip() and cur.strip():
                sims.append(similarity(prev, cur))
    if not sims:
        return 0.0, 0.0, 0
    near_identical = sum(1 for s in sims if s > 0.95) / len(sims)
    return statistics.mean(sims), near_identical, len(sims)


def main() -> None:
    print("=" * 76)
    print("EXP-005: inter-attempt code similarity (anchoring test)")
    print("higher similarity = model is editing its previous answer rather than")
    print("exploring a different approach")
    print("=" * 76)
    print(f"{'model':<30} {'condition':<10} {'mean sim':>9} {'>0.95':>8} {'pairs':>7}")
    results = {}
    for model in MODELS:
        for cond in CONDITIONS:
            run_id = CELLS[f"{model}|mbpp+|{cond}|k=8"]
            mean_sim, near, n = arm_diversity(run_id)
            results[(model, cond)] = mean_sim
            print(f"{model:<30} {cond:<10} {mean_sim:>9.3f} {near:>7.1%} {n:>7}")
        print()

    print("=" * 76)
    print("Anchoring effect (similarity relative to blind resampling)")
    print("=" * 76)
    for model in MODELS:
        base = results[(model, "resample")]
        deltas = " ".join(
            f"{c}={results[(model, c)] - base:+.3f}" for c in CONDITIONS if c != "resample"
        )
        print(f"{model:<30} resample={base:.3f}   {deltas}")


if __name__ == "__main__":
    main()
