"""EXP-004 analysis: k-curves, paired contrasts, Holm correction, threat checks.

Reads repair runs and reconstructs full per-task outcome vectors (tasks that
passed at baseline pass in every arm, so they are concordant but must still be
present for the pass-rate difference to be on the right scale).
"""

from __future__ import annotations

import json
from pathlib import Path

from sia.analysis import mcnemar_exact, paired_bootstrap_diff

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
CELLS = json.loads((ROOT / "experiments" / "EXP-004" / "cells.json").read_text(encoding="utf-8"))

MODELS = ["qwen2.5-coder:1.5b-instruct", "qwen2.5-coder:3b-instruct", "qwen2.5-coder:7b"]
CONDITIONS = ["resample", "placebo", "feedback"]
K_MAX = 8


def load_arm(run_id: str) -> dict:
    run_dir = RUNS / run_id
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8-sig"))
    rows = [
        json.loads(line)
        for line in (run_dir / "results.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    n_tasks = int(manifest["totals"]["tasks"])
    n_repaired = len(rows)
    n_baseline_passed = n_tasks - n_repaired

    # Truncation check (pre-registered threat a): did any arm run out of
    # budget before emitting code? Counted over repair responses only.
    truncated = 0
    total_resp = 0
    max_tokens = manifest["config"]["max_tokens"]
    for line in (run_dir / "trace.jsonl").read_text(encoding="utf-8").splitlines():
        e = json.loads(line)
        if e["type"] != "llm_response":
            continue
        total_resp += 1
        d = e["data"]
        if d["completion_tokens"] >= max_tokens - 8 or "```" not in d["content"]:
            truncated += 1

    outcomes = {}
    for r in rows:
        passed_at = r["passed_at"]
        outcomes[r["task_id"]] = [
            any(passed_at[: k + 1]) for k in range(K_MAX + 1)
        ]
    return {
        "run_id": run_id,
        "manifest": manifest,
        "n_tasks": n_tasks,
        "n_baseline_passed": n_baseline_passed,
        "outcomes": outcomes,
        "truncated": truncated,
        "total_resp": total_resp,
        "out_tokens": manifest["totals"]["completion_tokens"],
    }


def vector(arm: dict, task_ids: list[str], k: int) -> list[bool]:
    """Full 378-length outcome vector at iteration budget k."""
    return [arm["outcomes"][t][k] if t in arm["outcomes"] else True for t in task_ids]


def holm(pairs: list[tuple[str, float]]) -> dict[str, tuple[float, bool]]:
    """Holm-Bonferroni. Returns {label: (adjusted_p, significant_at_0.05)}."""
    ordered = sorted(pairs, key=lambda kv: kv[1])
    m = len(ordered)
    out = {}
    running = 0.0
    for i, (label, p) in enumerate(ordered):
        adj = min(1.0, max(running, (m - i) * p))
        running = adj
        out[label] = (adj, adj < 0.05)
    return out


def main() -> None:
    arms = {}
    for model in MODELS:
        for cond in CONDITIONS:
            label = f"{model}|mbpp+|{cond}|k={K_MAX}"
            arms[(model, cond)] = load_arm(CELLS[label])

    print("=" * 78)
    print("THREAT CHECK (a): budget exhaustion per arm")
    print("=" * 78)
    print(f"{'model':<30} {'cond':<10} {'responses':>10} {'truncated':>10} {'rate':>7}")
    worst = 0.0
    for model in MODELS:
        for cond in CONDITIONS:
            a = arms[(model, cond)]
            rate = a["truncated"] / max(a["total_resp"], 1)
            worst = max(worst, rate)
            print(
                f"{model:<30} {cond:<10} {a['total_resp']:>10} {a['truncated']:>10} {rate:>6.1%}"
            )
    verdict = "OK" if worst < 0.05 else "ARMS ARE BUDGET-LIMITED"
    print(f"\nworst truncation rate = {worst:.1%}  ->  {verdict}")

    print("\n" + "=" * 78)
    print("K-CURVES (pass@1 on MBPP+, n=378)")
    print("=" * 78)
    for model in MODELS:
        print(f"\n{model}")
        for cond in CONDITIONS:
            a = arms[(model, cond)]
            ids = sorted(a["outcomes"])
            base_pass = a["n_baseline_passed"]
            curve = [
                (base_pass + sum(a["outcomes"][t][k] for t in ids)) / a["n_tasks"]
                for k in range(K_MAX + 1)
            ]
            tok = a["out_tokens"]
            print(
                f"  {cond:<9} " + " ".join(f"{v:.3f}" for v in curve) + f"   [{tok/1000:.0f}k tok]"
            )

    print("\n" + "=" * 78)
    print("PAIRED CONTRASTS AT k=8 (McNemar exact + bootstrap CI on difference)")
    print("=" * 78)
    contrasts = [("feedback", "placebo"), ("placebo", "resample"), ("feedback", "resample")]
    raw: list[tuple[str, float]] = []
    detail = {}
    for model in MODELS:
        task_ids = sorted(arms[(model, "resample")]["outcomes"])
        n_base = arms[(model, "resample")]["n_baseline_passed"]
        all_ids = task_ids + [f"__baseline_pass_{i}" for i in range(n_base)]
        for hi, lo in contrasts:
            a_lo = vector(arms[(model, lo)], all_ids, K_MAX)
            a_hi = vector(arms[(model, hi)], all_ids, K_MAX)
            n01, n10, p = mcnemar_exact(a_lo, a_hi)
            diff, ci_lo, ci_hi = paired_bootstrap_diff(a_lo, a_hi, iterations=10000)
            label = f"{model.split(':')[1][:4]} {hi}-{lo}"
            raw.append((label, p))
            detail[label] = (diff, ci_lo, ci_hi, n01, n10, p)

    adjusted = holm(raw)
    print(f"{'contrast':<26} {'diff':>8} {'95% CI':>20} {'raw p':>9} {'Holm p':>9}  sig")
    for label, (diff, lo, hi, _n01, _n10, p) in detail.items():
        adj, sig = adjusted[label]
        print(
            f"{label:<26} {diff:>+8.3f} [{lo:>+6.3f},{hi:>+6.3f}] {p:>9.4f} {adj:>9.4f}  "
            f"{'YES' if sig else 'no'}"
        )

    print("\n" + "=" * 78)
    print("MARGINAL GAIN PER ITERATION (H4: knee)")
    print("=" * 78)
    for model in MODELS:
        a = arms[(model, "resample")]
        ids = sorted(a["outcomes"])
        curve = [
            (a["n_baseline_passed"] + sum(a["outcomes"][t][k] for t in ids)) / a["n_tasks"]
            for k in range(K_MAX + 1)
        ]
        marg = [curve[k] - curve[k - 1] for k in range(1, K_MAX + 1)]
        total = curve[-1] - curve[0]
        share_by_2 = (curve[2] - curve[0]) / total if total else 0
        print(f"{model:<30} marginal: " + " ".join(f"{m:+.3f}" for m in marg))
        print(f"{'':<30} share of total gain by k=2: {share_by_2:.0%}")


if __name__ == "__main__":
    main()
