"""Aggregate grid results into a paper-ready table.

Comparisons are paired against a per-(model, bench) baseline cell, because
every arm runs the same task set (ADR-0005). Reporting a bare pass rate per
arm would hide that pairing and overstate the evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sia.analysis import analyze_run, mcnemar_exact, paired_bootstrap_diff
from sia.analysis.taxonomy import DEFAULT_RUNS_DIR
from sia.bench import wilson_ci


@dataclass
class Row:
    model: str
    bench: str
    condition: str
    repair_k: int
    run_id: str
    tasks: int
    passed: int
    pass_rate: float
    ci: tuple[float, float]
    budget_exhausted: int
    conditional_pass: float | None
    # Paired comparison against this cell's baseline (condition="none", k=0).
    delta: float | None = None
    delta_ci: tuple[float, float] | None = None
    p_value: float | None = None
    is_baseline: bool = False


def build_report(
    cell_runs: dict[str, str],
    *,
    runs_dir: Path = DEFAULT_RUNS_DIR,
    bootstrap_iterations: int = 10_000,
) -> list[Row]:
    """Build rows from ``{cell_label: run_id}``.

    Cell labels are ``model|bench|condition|k=N`` (see ``GridCell.label``).
    """
    reports = {}
    for label, run_id in cell_runs.items():
        try:
            reports[label] = analyze_run(run_id, runs_dir=runs_dir)
        except FileNotFoundError:
            continue

    rows: list[Row] = []
    for label, report in reports.items():
        model, bench, condition, k_part = label.split("|")
        repair_k = int(k_part.removeprefix("k="))
        lo, hi = wilson_ci(report.passed, report.tasks) if report.tasks else (0.0, 0.0)
        rows.append(
            Row(
                model=model,
                bench=bench,
                condition=condition,
                repair_k=repair_k,
                run_id=report.run_id,
                tasks=report.tasks,
                passed=report.passed,
                pass_rate=report.pass_rate,
                ci=(lo, hi),
                budget_exhausted=report.budget_exhausted,
                conditional_pass=report.conditional_pass,
                is_baseline=condition == "none" and repair_k == 0,
            )
        )

    # Pair every non-baseline arm against its own model+bench baseline.
    baselines = {
        (r.model, r.bench): reports[f"{r.model}|{r.bench}|{r.condition}|k={r.repair_k}"]
        for r in rows
        if r.is_baseline
    }
    for row in rows:
        if row.is_baseline:
            continue
        base = baselines.get((row.model, row.bench))
        if base is None:
            continue
        arm = reports[f"{row.model}|{row.bench}|{row.condition}|k={row.repair_k}"]
        shared = sorted(set(base.outcomes) & set(arm.outcomes))
        if not shared:
            continue
        a = [base.outcomes[t] for t in shared]
        b = [arm.outcomes[t] for t in shared]
        _, _, p = mcnemar_exact(a, b)
        diff, lo, hi = paired_bootstrap_diff(a, b, iterations=bootstrap_iterations)
        row.delta, row.delta_ci, row.p_value = diff, (lo, hi), p

    rows.sort(key=lambda r: (r.model, r.bench, r.condition, r.repair_k))
    return rows


def format_markdown(rows: list[Row]) -> str:
    """Render rows as a Markdown table ready to paste into a paper draft."""
    if not rows:
        return "_no completed runs_"
    out = [
        "| Model | Benchmark | Condition | k | pass@1 | 95% CI | Δ vs baseline | Δ 95% CI | p |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        delta = "—" if r.delta is None else f"{r.delta:+.3f}"
        dci = "—" if r.delta_ci is None else f"[{r.delta_ci[0]:+.3f}, {r.delta_ci[1]:+.3f}]"
        p = "—" if r.p_value is None else (f"{r.p_value:.4f}" if r.p_value >= 1e-4 else "<0.0001")
        flag = " ⚠" if r.budget_exhausted else ""
        out.append(
            f"| {r.model} | {r.bench} | {r.condition} | {r.repair_k} "
            f"| {r.pass_rate:.3f}{flag} | [{r.ci[0]:.3f}, {r.ci[1]:.3f}] "
            f"| {delta} | {dci} | {p} |"
        )
    if any(r.budget_exhausted for r in rows):
        out.append("")
        out.append(
            "⚠ = some responses exhausted the token budget before emitting code; "
            "that cell measures budget fit, not capability."
        )
    return "\n".join(out)
