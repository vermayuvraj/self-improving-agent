"""EXP-008 analysis: the frontier-scale (Llama-3.3-70B) arm.

Answers the pre-registered questions: does the feedback-vs-resample penalty
that shrank across 1.5B -> 3B -> 7B reach parity (H1) at ~70B, and does the
anchoring signal weaken (H2)? Slots the frontier point onto the 7B row for a
direct comparison.
"""

from __future__ import annotations

import difflib
import json
from pathlib import Path

from sia.analysis import mcnemar_exact, paired_bootstrap_diff
from sia.bench import extract_code, wilson_ci

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
CELLS = json.loads((ROOT / "experiments" / "EXP-008" / "cells.json").read_text(encoding="utf-8"))

# Discover the model tag from the cells (single frontier model).
MODEL_TAG = next(iter(CELLS)).split("|")[0]
BENCH = "mbpp+"
K_MAX = 8
CONDITIONS = ["resample", "feedback", "reflect"]


def _manifest(run_id: str) -> dict:
    return json.loads((RUNS / run_id / "manifest.json").read_text(encoding="utf-8-sig"))


def baseline_outcomes() -> tuple[dict[str, bool], int]:
    """Per-task pass at k=0 from the frontier baseline run."""
    run_id = CELLS[f"{MODEL_TAG}|{BENCH}|none|k=0"]
    out: dict[str, bool] = {}
    for line in (RUNS / run_id / "results.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("sample", 0) == 0:
            out[r["task_id"]] = bool(r.get("passed"))
    n = int(_manifest(run_id)["totals"]["tasks"])
    return out, n


def arm_outcomes(cond: str, base: dict[str, bool]) -> tuple[dict[str, bool], int, int]:
    """Per-task pass at k=8 for a repair arm, filled in from the baseline for
    tasks that never needed repair. Returns (outcomes, out_tokens, n_tasks)."""
    run_id = CELLS[f"{MODEL_TAG}|{BENCH}|{cond}|k={K_MAX}"]
    manifest = _manifest(run_id)
    n = int(manifest["totals"]["tasks"])
    out = dict(base)  # tasks solved at baseline stay solved
    for line in (RUNS / run_id / "results.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        out[r["task_id"]] = any(r["passed_at"][: K_MAX + 1])
    return out, int(manifest["totals"]["completion_tokens"]), n


def kcurve(cond: str, base: dict[str, bool], n: int) -> list[float]:
    run_id = CELLS[f"{MODEL_TAG}|{BENCH}|{cond}|k={K_MAX}"]
    rows = [
        json.loads(x)
        for x in (RUNS / run_id / "results.jsonl").read_text(encoding="utf-8").splitlines()
        if x.strip()
    ]
    solved_base = sum(1 for v in base.values() if v)
    curve = []
    for k in range(K_MAX + 1):
        extra = sum(1 for r in rows if any(r["passed_at"][: k + 1]))
        curve.append((solved_base + extra) / n)
    return curve


def similarity(cond: str) -> float:
    run_id = CELLS[f"{MODEL_TAG}|{BENCH}|{cond}|k={K_MAX}"]
    by_task: dict[str, list[tuple[int, str]]] = {}
    for line in (RUNS / run_id / "trace.jsonl").read_text(encoding="utf-8").splitlines():
        e = json.loads(line)
        if e["type"] != "llm_response":
            continue
        d = e["data"]
        by_task.setdefault(d["task_id"], []).append((d["iteration"], extract_code(d["content"])))
    sims = []
    for attempts in by_task.values():
        attempts.sort()
        for (_, a), (_, b) in zip(attempts, attempts[1:], strict=False):
            if a.strip() and b.strip():
                sims.append(difflib.SequenceMatcher(None, a, b).ratio())
    return sum(sims) / len(sims) if sims else 0.0


def main() -> None:
    base, n = baseline_outcomes()
    base_pass = sum(1 for v in base.values() if v) / n
    lo, hi = wilson_ci(sum(1 for v in base.values() if v), n)
    print("=" * 74)
    print(f"EXP-008  {MODEL_TAG}  (MBPP+, n={n})")
    print("=" * 74)
    n_fail = n - sum(1 for v in base.values() if v)
    print(f"baseline pass@1 = {base_pass:.3f} [{lo:.3f}, {hi:.3f}]   failures = {n_fail}")

    print("\nk-curves:")
    arms = {}
    for cond in CONDITIONS:
        arms[cond] = arm_outcomes(cond, base)
        curve = kcurve(cond, base, n)
        toks = arms[cond][1]
        print(f"  {cond:<9} " + " ".join(f"{v:.3f}" for v in curve) + f"   [{toks/1000:.0f}k tok]")

    print("\ncontrasts at k=8 (McNemar exact + bootstrap CI):")
    ids = sorted(base)
    for hi_c, lo_c in [("feedback", "resample"), ("reflect", "resample"), ("reflect", "feedback")]:
        a = [arms[lo_c][0][t] for t in ids]
        b = [arms[hi_c][0][t] for t in ids]
        _, _, p = mcnemar_exact(a, b)
        diff, clo, chi = paired_bootstrap_diff(a, b, iterations=10000)
        sig = "YES" if p < 0.05 / 3 else "no"
        print(f"  {hi_c}-{lo_c:<9} {diff:+.3f} [{clo:+.3f},{chi:+.3f}]  p={p:.4f}  Holm-sig={sig}")

    print("\nanchoring (inter-attempt similarity; resample is the floor):")
    for cond in CONDITIONS:
        s = similarity(cond)
        print(f"  {cond:<9} {s:.3f}")

    print("\nCompare to 7B (EXP-004): feedback-resample was -0.011 (n.s.);")
    print("similarity resample/feedback 0.607/0.914.")


if __name__ == "__main__":
    main()
