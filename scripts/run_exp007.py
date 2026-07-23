"""Run EXP-007: the `reflect` arm, on the same harness as EXP-004.

Reuses EXP-004's cells.json so the reflect arm sits alongside the other three
conditions and the analysis script picks it up without special-casing.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from sia.llm import OpenAICompatClient
from sia.repair.runner import run_repair

ROOT = Path(__file__).resolve().parent.parent
CELLS = ROOT / "experiments" / "EXP-004" / "cells.json"
BENCH = "mbpp+"
K_MAX = 8
CONDITION = "reflect"

BASELINES = {
    "qwen2.5-coder:1.5b-instruct": "7ce4c1224d11",
    "qwen2.5-coder:3b-instruct": "0b1aff369e5c",
    "qwen2.5-coder:7b": "f0f2559baf8d",
}


def main() -> int:
    cells = json.loads(CELLS.read_text(encoding="utf-8")) if CELLS.exists() else {}
    for model, baseline in BASELINES.items():
        label = f"{model}|{BENCH}|{CONDITION}|k={K_MAX}"
        if label in cells:
            print(f"skip (done): {label}", flush=True)
            continue
        print(f"\n=== {label} ===", flush=True)
        client = OpenAICompatClient(model)
        try:
            client.check_available()
            summary = run_repair(
                BENCH,
                client,
                condition=CONDITION,
                k_max=K_MAX,
                baseline_run_id=baseline,
                seed=7,
                progress=lambda line: print(line, flush=True),
            )
        finally:
            client.close()
        cells[label] = summary.run_id
        CELLS.write_text(json.dumps(cells, indent=2), encoding="utf-8")
        curve = "  ".join(f"k={k}:{v:.3f}" for k, v in sorted(summary.pass_at_k.items()))
        print(f"  run={summary.run_id}\n  {curve}", flush=True)
        print(
            f"  tokens={summary.totals['completion_tokens']:.0f} out, "
            f"wall={summary.totals['wall_s']:.0f}s",
            flush=True,
        )
    print("\n=== EXP-007 complete ===", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
