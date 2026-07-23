"""Build per-model experience stores and audit them for leakage.

Each model retrieves from *its own* solved tasks — this is experience memory
in the self-improvement sense, not cross-model distillation, which would be a
different (and confounded) experiment.

The audit matters more than the build. Retrieval over a benchmark that also
supplies the evaluation tasks is only legitimate under leave-one-out; near
-duplicate tasks can still hand the model its answer. This script measures
that directly instead of assuming it away.
"""

from __future__ import annotations

import difflib
import json
import statistics
from pathlib import Path

from sia.bench import load_tasks
from sia.memory import Retriever, mine_from_runs

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "experiments" / "EXP-006"

BENCH = "mbpp+"
K_EXEMPLARS = 2

# Each model's own MBPP+ baseline run (EXP-003b).
BASELINES = {
    "qwen2.5-coder:1.5b-instruct": "7ce4c1224d11",
    "qwen2.5-coder:3b-instruct": "0b1aff369e5c",
    "qwen2.5-coder:7b": "f0f2559baf8d",
}


def main() -> None:
    tasks = load_tasks(BENCH)
    instructions = {t.task_id: t.instruction for t in tasks}
    gold = {t.task_id: t.canonical_solution for t in tasks}
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"{'model':<30} {'store':>7} {'covered':>8}")
    stores = {}
    for model, run_id in BASELINES.items():
        store = mine_from_runs(
            [run_id], bench_filter=BENCH, instructions=instructions, runs_dir=ROOT / "runs"
        )
        stores[model] = store
        path = OUT_DIR / f"memory-{model.replace(':', '_')}.jsonl"
        store.save(path)
        print(f"{model:<30} {len(store):>7} {len(store) / len(tasks):>7.0%}")

    print("\n" + "=" * 72)
    print("LEAKAGE AUDIT: does retrieval hand the model its own answer?")
    print("=" * 72)
    print("similarity between a retrieved exemplar's code and the query task's")
    print("gold solution. High values mean the exemplar *is* the answer.\n")
    print(f"{'model':<30} {'mean':>7} {'p95':>7} {'max':>7} {'>0.8':>7}")

    audit = {}
    for model, store in stores.items():
        retriever = Retriever(store)
        sims = []
        for task in tasks:
            got = retriever.retrieve(
                task.instruction, k=K_EXEMPLARS, exclude_task_ids={task.task_id}
            )
            for exemplar in got:
                sims.append(
                    difflib.SequenceMatcher(None, exemplar.code, gold[task.task_id]).ratio()
                )
        if not sims:
            continue
        sims.sort()
        p95 = sims[int(0.95 * len(sims))]
        high = sum(1 for s in sims if s > 0.8) / len(sims)
        audit[model] = {
            "mean": statistics.mean(sims),
            "p95": p95,
            "max": max(sims),
            "share_above_0.8": high,
            "pairs": len(sims),
        }
        print(
            f"{model:<30} {statistics.mean(sims):>7.3f} {p95:>7.3f} {max(sims):>7.3f} {high:>6.1%}"
        )

    (OUT_DIR / "leakage_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    worst = max((a["share_above_0.8"] for a in audit.values()), default=0.0)
    print(
        f"\nworst share of near-answer exemplars: {worst:.1%} -> "
        + ("OK" if worst < 0.05 else "LEAKAGE RISK, report explicitly")
    )


if __name__ == "__main__":
    main()
