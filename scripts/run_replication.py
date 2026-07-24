"""Replicate the EXP-004 decomposition for one local model (EXP-009 / EXP-010).

Runs a greedy baseline, then the repair conditions seeded from it, exactly as
EXP-004 did — the only thing that varies between invocations is the model.
Resumable via experiments/<exp_id>/cells.json.

Usage:
    uv run python scripts/run_replication.py EXP-009 qwen2.5-coder:1.5b-instruct-fp16
    uv run python scripts/run_replication.py EXP-010 deepseek-coder:1.3b-instruct
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from sia.bench import load_tasks
from sia.llm import OpenAICompatClient
from sia.repair.runner import run_repair
from sia.runner import run_benchmark

ROOT = Path(__file__).resolve().parent.parent
BENCH = "mbpp+"
K_MAX = 8
SEED = 7
# `reflect` omitted: it is secondary, and both review objections concern the
# feedback/placebo/resample decomposition.
CONDITIONS = ("resample", "placebo", "feedback")


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    exp_id, model = sys.argv[1], sys.argv[2]

    exp_dir = ROOT / "experiments" / exp_id
    exp_dir.mkdir(parents=True, exist_ok=True)
    cells_path = exp_dir / "cells.json"
    cells = json.loads(cells_path.read_text(encoding="utf-8")) if cells_path.exists() else {}

    tasks = load_tasks(BENCH)
    print(f"=== {exp_id}: {model} on {BENCH} ({len(tasks)} tasks) ===", flush=True)

    def client() -> OpenAICompatClient:
        return OpenAICompatClient(model, timeout_s=600.0)

    # 1) Greedy baseline — the k=0 point and the seed for every repair arm.
    base_label = f"{model}|{BENCH}|none|k=0"
    if base_label not in cells:
        c = client()
        try:
            c.check_available()
            s = run_benchmark(
                BENCH, c, tasks=tasks, seed=SEED, temperature=0.0, exec_timeout_s=60.0,
                extra_config={"exp": exp_id},
                progress=lambda line: print(line, flush=True),
            )
        finally:
            c.close()
        cells[base_label] = s.run_id
        cells_path.write_text(json.dumps(cells, indent=2), encoding="utf-8")
        print(f"  baseline pass@1={s.pass_rates['pass@1']:.3f} run={s.run_id}", flush=True)

    baseline_run = cells[base_label]

    # 2) Repair arms.
    for condition in CONDITIONS:
        label = f"{model}|{BENCH}|{condition}|k={K_MAX}"
        if label in cells:
            print(f"skip (done): {label}", flush=True)
            continue
        print(f"\n=== {condition} ===", flush=True)
        c = client()
        try:
            s = run_repair(
                BENCH, c, condition=condition, k_max=K_MAX,
                baseline_run_id=baseline_run, tasks=tasks, seed=SEED,
                exec_timeout_s=60.0,
                progress=lambda line: print(line, flush=True),
            )
        finally:
            c.close()
        cells[label] = s.run_id
        cells_path.write_text(json.dumps(cells, indent=2), encoding="utf-8")
        curve = "  ".join(f"k={k}:{v:.3f}" for k, v in sorted(s.pass_at_k.items()))
        print(f"  run={s.run_id}\n  {curve}", flush=True)
        print(f"  tokens={s.totals['completion_tokens']:.0f} out", flush=True)

    print(f"\n=== {exp_id} complete ===", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
