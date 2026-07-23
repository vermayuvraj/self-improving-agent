"""Run EXP-006: does other-task experience memory help?

Two new arms per model (`random`, `retrieved`); the `none` arm reuses the
EXP-003b baseline, which used the identical greedy configuration. Resumable
via cells.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from sia.bench import BenchTask, load_tasks
from sia.llm import OpenAICompatClient
from sia.memory import MemoryStore, Retriever, build_memory_messages
from sia.runner import run_benchmark

ROOT = Path(__file__).resolve().parent.parent
EXP_DIR = ROOT / "experiments" / "EXP-006"
CELLS = EXP_DIR / "cells.json"

BENCH = "mbpp+"
K_EXEMPLARS = 2
SEED = 7

BASELINES = {
    "qwen2.5-coder:1.5b-instruct": "7ce4c1224d11",
    "qwen2.5-coder:3b-instruct": "0b1aff369e5c",
    "qwen2.5-coder:7b": "f0f2559baf8d",
}


def main() -> int:
    tasks = load_tasks(BENCH)
    cells = json.loads(CELLS.read_text(encoding="utf-8")) if CELLS.exists() else {}

    # The `none` arm is the existing baseline — identical config, no re-run.
    for model, run_id in BASELINES.items():
        cells.setdefault(f"{model}|{BENCH}|none|k=0", run_id)

    for model in BASELINES:
        store = MemoryStore.load(EXP_DIR / f"memory-{model.replace(':', '_')}.jsonl")
        retriever = Retriever(store)
        print(f"\n### {model}  (store={len(store)})", flush=True)

        for condition in ("random", "retrieved"):
            label = f"{model}|{BENCH}|{condition}|k=0"
            if label in cells:
                print(f"skip (done): {label}", flush=True)
                continue

            def build(task: BenchTask, _cond: str = condition, _r: Retriever = retriever) -> list:
                exclude = {task.task_id}
                if _cond == "retrieved":
                    picked = _r.retrieve(task.instruction, k=K_EXEMPLARS, exclude_task_ids=exclude)
                else:
                    # Seeded per task so the control is reproducible but not
                    # the same two exemplars for every task.
                    picked = _r.random_items(
                        k=K_EXEMPLARS,
                        exclude_task_ids=exclude,
                        seed=SEED + hash(task.task_id) % 10_000,
                    )
                return build_memory_messages(task, picked)

            client = OpenAICompatClient(model)
            try:
                client.check_available()
                summary = run_benchmark(
                    BENCH,
                    client,
                    tasks=tasks,
                    seed=SEED,
                    temperature=0.0,
                    exec_timeout_s=60.0,
                    message_builder=build,
                    extra_config={"memory_condition": condition, "exemplars": K_EXEMPLARS},
                )
            finally:
                client.close()

            cells[label] = summary.run_id
            CELLS.parent.mkdir(parents=True, exist_ok=True)
            CELLS.write_text(json.dumps(cells, indent=2), encoding="utf-8")
            print(
                f"  {condition:<10} pass@1={summary.pass_rates['pass@1']:.3f} "
                f"run={summary.run_id} wall={summary.totals['wall_s']:.0f}s",
                flush=True,
            )

    print("\n=== EXP-006 complete ===", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
