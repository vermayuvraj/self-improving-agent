"""EXP-006 analysis: memory conditions, paired contrasts, Holm correction.

Also checks that the arms are genuinely distinct runs — identical pass rates
between two arms can be coincidence or can be a bug in which both received
the same prompts, and those look the same in aggregate.
"""

from __future__ import annotations

import json
from pathlib import Path

from sia.analysis import analyze_run, mcnemar_exact, paired_bootstrap_diff
from sia.bench import wilson_ci

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
CELLS = json.loads((ROOT / "experiments" / "EXP-006" / "cells.json").read_text(encoding="utf-8"))

MODELS = ["qwen2.5-coder:1.5b-instruct", "qwen2.5-coder:3b-instruct", "qwen2.5-coder:7b"]
CONDITIONS = ["none", "random", "retrieved"]
BENCH = "mbpp+"


def holm(pairs: list[tuple[str, float]]) -> dict[str, tuple[float, bool]]:
    ordered = sorted(pairs, key=lambda kv: kv[1])
    m = len(ordered)
    out, running = {}, 0.0
    for i, (label, p) in enumerate(ordered):
        adj = min(1.0, max(running, (m - i) * p))
        running = adj
        out[label] = (adj, adj < 0.05)
    return out


def prompts_of(run_id: str) -> dict[str, str]:
    """First user prompt per task — used to prove two arms really differed."""
    out = {}
    for line in (RUNS / run_id / "trace.jsonl").read_text(encoding="utf-8").splitlines():
        e = json.loads(line)
        if e["type"] != "llm_call":
            continue
        d = e["data"]
        out.setdefault(d["task_id"], d["messages"][-1]["content"])
    return out


def main() -> None:
    reports = {}
    for model in MODELS:
        for cond in CONDITIONS:
            run_id = CELLS[f"{model}|{BENCH}|{cond}|k=0"]
            reports[(model, cond)] = analyze_run(run_id, runs_dir=RUNS)

    print("=" * 76)
    print("SANITY: are the random and retrieved arms actually different runs?")
    print("=" * 76)
    for model in MODELS:
        pr = prompts_of(CELLS[f"{model}|{BENCH}|random|k=0"])
        pt = prompts_of(CELLS[f"{model}|{BENCH}|retrieved|k=0"])
        shared = sorted(set(pr) & set(pt))
        same_prompt = sum(1 for t in shared if pr[t] == pt[t])
        a = reports[(model, "random")].outcomes
        b = reports[(model, "retrieved")].outcomes
        same_outcome = sum(1 for t in shared if a.get(t) == b.get(t))
        print(
            f"{model:<30} identical prompts {same_prompt:>4}/{len(shared)}  "
            f"identical outcomes {same_outcome:>4}/{len(shared)}"
        )

    print("\n" + "=" * 76)
    print("PASS@1 (MBPP+, n=378, greedy)")
    print("=" * 76)
    print(f"{'model':<30} " + "".join(f"{c:>22}" for c in CONDITIONS))
    for model in MODELS:
        cells = []
        for cond in CONDITIONS:
            r = reports[(model, cond)]
            lo, hi = wilson_ci(r.passed, r.tasks)
            cells.append(f"{r.pass_rate:.3f} [{lo:.3f},{hi:.3f}]")
        print(f"{model:<30} " + "".join(f"{c:>22}" for c in cells))

    print("\n" + "=" * 76)
    print("TRUNCATION (threat a)")
    print("=" * 76)
    for model in MODELS:
        parts = [
            f"{cond}={reports[(model, cond)].budget_exhausted}" for cond in CONDITIONS
        ]
        print(f"{model:<30} " + "  ".join(parts))

    print("\n" + "=" * 76)
    print("PAIRED CONTRASTS (McNemar exact + bootstrap CI, Holm-corrected)")
    print("=" * 76)
    contrasts = [("retrieved", "random"), ("random", "none"), ("retrieved", "none")]
    raw, detail = [], {}
    for model in MODELS:
        for hi_c, lo_c in contrasts:
            ra, rb = reports[(model, lo_c)], reports[(model, hi_c)]
            shared = sorted(set(ra.outcomes) & set(rb.outcomes))
            a = [ra.outcomes[t] for t in shared]
            b = [rb.outcomes[t] for t in shared]
            _, _, p = mcnemar_exact(a, b)
            diff, lo, hi = paired_bootstrap_diff(a, b, iterations=10000)
            label = f"{model.split(':')[1][:4]} {hi_c}-{lo_c}"
            raw.append((label, p))
            detail[label] = (diff, lo, hi, p)

    adjusted = holm(raw)
    print(f"{'contrast':<28} {'diff':>8} {'95% CI':>20} {'raw p':>9} {'Holm p':>9}  sig")
    for label, (diff, lo, hi, p) in detail.items():
        adj, sig = adjusted[label]
        print(
            f"{label:<28} {diff:>+8.3f} [{lo:>+6.3f},{hi:>+6.3f}] {p:>9.4f} {adj:>9.4f}  "
            f"{'YES' if sig else 'no'}"
        )


if __name__ == "__main__":
    main()
