"""Analyse a replication experiment (EXP-009 FP16 / EXP-010 DeepSeek).

Reports k-curves, Holm-corrected paired contrasts and the anchoring measure,
and prints the Q4 1.5B reference row alongside so the replication can be read
against the original directly.

Usage: uv run python scripts/analyze_replication.py EXP-009
"""

from __future__ import annotations

import difflib
import json
import sys
from pathlib import Path

from sia.analysis import mcnemar_exact, paired_bootstrap_diff
from sia.bench import extract_code, wilson_ci

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
BENCH = "mbpp+"
K_MAX = 8
CONDITIONS = ["resample", "placebo", "feedback"]

# The original Q4 1.5B numbers this replication is compared against (EXP-004/005).
REFERENCE = {
    "label": "Q4 1.5B (EXP-004)",
    "baseline": 0.566,
    "pass": {"resample": 0.749, "placebo": 0.688, "feedback": 0.688},
    "anchor": {"resample": 0.509, "placebo": 0.828, "feedback": 0.862},
}


def manifest(run_id: str) -> dict:
    return json.loads((RUNS / run_id / "manifest.json").read_text(encoding="utf-8-sig"))


def rows(run_id: str) -> list[dict]:
    p = RUNS / run_id / "results.jsonl"
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def baseline_outcomes(cells: dict, model: str) -> tuple[dict[str, bool], int]:
    run_id = cells[f"{model}|{BENCH}|none|k=0"]
    out = {r["task_id"]: bool(r.get("passed")) for r in rows(run_id) if r.get("sample", 0) == 0}
    return out, int(manifest(run_id)["totals"]["tasks"])


def arm(cells: dict, model: str, cond: str, base: dict[str, bool]) -> tuple[dict[str, bool], int]:
    run_id = cells[f"{model}|{BENCH}|{cond}|k={K_MAX}"]
    out = dict(base)
    for r in rows(run_id):
        out[r["task_id"]] = any(r["passed_at"][: K_MAX + 1])
    return out, int(manifest(run_id)["totals"]["completion_tokens"])


def curve(cells: dict, model: str, cond: str, base: dict[str, bool], n: int) -> list[float]:
    solved = sum(1 for v in base.values() if v)
    rs = rows(cells[f"{model}|{BENCH}|{cond}|k={K_MAX}"])
    return [
        (solved + sum(1 for r in rs if any(r["passed_at"][: k + 1]))) / n
        for k in range(K_MAX + 1)
    ]


def similarity(cells: dict, model: str, cond: str) -> float:
    run_id = cells[f"{model}|{BENCH}|{cond}|k={K_MAX}"]
    by_task: dict[str, list[tuple[int, str]]] = {}
    for line in (RUNS / run_id / "trace.jsonl").read_text(encoding="utf-8").splitlines():
        e = json.loads(line)
        if e["type"] != "llm_response":
            continue
        d = e["data"]
        by_task.setdefault(d["task_id"], []).append((d["iteration"], extract_code(d["content"])))
    sims = []
    for att in by_task.values():
        att.sort()
        for (_, a), (_, b) in zip(att, att[1:], strict=False):
            if a.strip() and b.strip():
                sims.append(difflib.SequenceMatcher(None, a, b).ratio())
    return sum(sims) / len(sims) if sims else 0.0


def holm(pairs: list[tuple[str, float]]) -> dict[str, tuple[float, bool]]:
    ordered = sorted(pairs, key=lambda kv: kv[1])
    m, out, running = len(ordered), {}, 0.0
    for i, (label, p) in enumerate(ordered):
        adj = min(1.0, max(running, (m - i) * p))
        running = adj
        out[label] = (adj, adj < 0.05)
    return out


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    exp_id = sys.argv[1]
    cells = json.loads((ROOT / "experiments" / exp_id / "cells.json").read_text(encoding="utf-8"))
    model = next(iter(cells)).split("|")[0]

    base, n = baseline_outcomes(cells, model)
    n_pass = sum(1 for v in base.values() if v)
    lo, hi = wilson_ci(n_pass, n)

    print("=" * 76)
    print(f"{exp_id}   {model}   MBPP+ (n={n})")
    print("=" * 76)
    print(f"baseline pass@1 = {n_pass/n:.3f} [{lo:.3f},{hi:.3f}]   "
          f"(reference {REFERENCE['label']}: {REFERENCE['baseline']:.3f})")

    print("\nk-curves:")
    arms, toks = {}, {}
    for c in CONDITIONS:
        arms[c], toks[c] = arm(cells, model, c, base)
        print(f"  {c:<9} " + " ".join(f"{v:.3f}" for v in curve(cells, model, c, base, n))
              + f"   [{toks[c]/1000:.0f}k tok]")

    print("\npass@1 at k=8 vs reference:")
    print(f"  {'condition':<10} {'this':>8} {'ref(Q4)':>9} {'delta':>8}")
    for c in CONDITIONS:
        v = sum(1 for t in base if arms[c][t]) / n
        r = REFERENCE["pass"][c]
        print(f"  {c:<10} {v:>8.3f} {r:>9.3f} {v-r:>+8.3f}")

    print("\npaired contrasts at k=8 (McNemar exact + bootstrap CI, Holm):")
    ids = sorted(base)
    raw, detail = [], {}
    for hi_c, lo_c in [("placebo", "resample"), ("feedback", "resample"), ("feedback", "placebo")]:
        a = [arms[lo_c][t] for t in ids]
        b = [arms[hi_c][t] for t in ids]
        _, _, p = mcnemar_exact(a, b)
        diff, clo, chi = paired_bootstrap_diff(a, b, iterations=10000)
        lab = f"{hi_c}-{lo_c}"
        raw.append((lab, p))
        detail[lab] = (diff, clo, chi, p)
    adj = holm(raw)
    for lab, (diff, clo, chi, p) in detail.items():
        a_p, sig = adj[lab]
        print(f"  {lab:<20} {diff:>+7.3f} [{clo:>+6.3f},{chi:>+6.3f}] "
              f"raw p={p:.4f}  Holm p={a_p:.4f}  {'SIG' if sig else 'n.s.'}")

    print("\nanchoring (mean inter-attempt similarity):")
    print(f"  {'condition':<10} {'this':>8} {'ref(Q4)':>9}")
    for c in CONDITIONS:
        s = similarity(cells, model, c)
        print(f"  {c:<10} {s:>8.3f} {REFERENCE['anchor'][c]:>9.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
