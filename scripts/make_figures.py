"""Generate the paper's figures directly from run artifacts.

Everything is recomputed from runs/ and the EXP cells.json files, so a figure
can never disagree with the numbers in EXPERIMENTS.md. Output: PDF (for
LaTeX) and PNG (for the dashboard/README) under PAPERS/capability-ablations/figures/.

Run: uv run --group paper python scripts/make_figures.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sia.analysis import analyze_run, mcnemar_exact, paired_bootstrap_diff

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
FIG = ROOT / "PAPERS" / "capability-ablations" / "figures"
FIG.mkdir(parents=True, exist_ok=True)

MODELS = ["qwen2.5-coder:1.5b-instruct", "qwen2.5-coder:3b-instruct", "qwen2.5-coder:7b"]
SHORT = {m: m.split(":")[1].replace("-instruct", "") for m in MODELS}
REPAIR_CONDS = ["resample", "placebo", "feedback", "reflect"]
MEM_CONDS = ["none", "random", "retrieved"]
K_MAX = 8

# Consistent colours (validated categorical order) and readable defaults.
COLOR = {
    "resample": "#2a78d6",
    "placebo": "#898781",
    "feedback": "#e34948",
    "reflect": "#008300",
    "none": "#898781",
    "random": "#eda100",
    "retrieved": "#2a78d6",
}
plt.rcParams.update(
    {
        "font.size": 9,
        "font.family": "sans-serif",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.dpi": 150,
        "savefig.bbox": "tight",
    }
)

EXP004 = json.loads((ROOT / "experiments" / "EXP-004" / "cells.json").read_text(encoding="utf-8"))
EXP006 = json.loads((ROOT / "experiments" / "EXP-006" / "cells.json").read_text(encoding="utf-8"))


def repair_curve(model: str, cond: str) -> tuple[list[float], int, int]:
    """Return (pass@1 for k=0..K_MAX, out_tokens, n_tasks) for one repair arm."""
    run_id = EXP004[f"{model}|mbpp+|{cond}|k={K_MAX}"]
    run_dir = RUNS / run_id
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8-sig"))
    n_tasks = int(manifest["totals"]["tasks"])
    rows = [
        json.loads(x)
        for x in (run_dir / "results.jsonl").read_text(encoding="utf-8").splitlines()
        if x.strip()
    ]
    solved_at_baseline = n_tasks - len(rows)
    curve = []
    for k in range(K_MAX + 1):
        extra = sum(1 for r in rows if any(r["passed_at"][: k + 1]))
        curve.append((solved_at_baseline + extra) / n_tasks)
    return curve, int(manifest["totals"]["completion_tokens"]), n_tasks


def repair_outcomes(model: str, cond: str, k: int) -> dict[str, bool]:
    run_id = EXP004[f"{model}|mbpp+|{cond}|k={K_MAX}"]
    run_dir = RUNS / run_id
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8-sig"))
    n_tasks = int(manifest["totals"]["tasks"])
    rows = [
        json.loads(x)
        for x in (run_dir / "results.jsonl").read_text(encoding="utf-8").splitlines()
        if x.strip()
    ]
    out = {r["task_id"]: any(r["passed_at"][: k + 1]) for r in rows}
    # Baseline-passed tasks are absent from results.jsonl but solved in every arm.
    for i in range(n_tasks - len(rows)):
        out[f"__base_{i}"] = True
    return out


# --- Figure 1: k-curves, 3-panel ------------------------------------------
def fig_kcurves() -> None:
    fig, axes = plt.subplots(1, 3, figsize=(9.5, 3.0), sharey=False)
    for ax, model in zip(axes, MODELS, strict=True):
        for cond in REPAIR_CONDS:
            curve, _, _ = repair_curve(model, cond)
            ax.plot(
                range(K_MAX + 1),
                curve,
                marker="o",
                ms=3,
                lw=1.6 if cond == "resample" else 1.2,
                color=COLOR[cond],
                label=cond,
                zorder=3 if cond == "resample" else 2,
            )
        ax.set_title(SHORT[model], fontsize=10)
        ax.set_xlabel("repair iterations $k$")
        ax.grid(True, alpha=0.25, lw=0.5)
    axes[0].set_ylabel("pass@1 (MBPP+)")
    axes[0].legend(frameon=False, fontsize=8, loc="lower right")
    fig.suptitle(
        "Self-repair k-curves: blind resampling (blue) dominates at every scale",
        fontsize=10,
        y=1.02,
    )
    _save(fig, "fig1_kcurves")


# --- Figure 2: forest plot of k=8 contrasts -------------------------------
def fig_forest() -> None:
    contrasts = [("feedback", "resample"), ("placebo", "resample"), ("reflect", "resample")]
    rows = []
    for model in MODELS:
        for hi, lo in contrasts:
            a = repair_outcomes(model, lo, K_MAX)
            b = repair_outcomes(model, hi, K_MAX)
            ids = sorted(set(a) & set(b))
            va, vb = [a[t] for t in ids], [b[t] for t in ids]
            diff, clo, chi = paired_bootstrap_diff(va, vb, iterations=10000)
            _, _, p = mcnemar_exact(va, vb)
            rows.append((f"{SHORT[model]}: {hi}", diff, clo, chi, p))

    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    ys = range(len(rows))
    for y, (_label, diff, clo, chi, p) in zip(ys, rows, strict=True):
        sig = p < 0.05 / 3
        color = "#d03b3b" if diff < 0 and sig else ("#898781" if not sig else "#0ca30c")
        ax.plot([clo, chi], [y, y], color=color, lw=2)
        ax.plot(diff, y, "o", color=color, ms=6)
    ax.axvline(0, color="#333", lw=1, ls="--", alpha=0.7)
    ax.set_yticks(list(ys))
    ax.set_yticklabels([r[0] for r in rows], fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("$\\Delta$ pass@1 vs blind resampling (k=8, 95% CI)")
    ax.set_title("Every own-output condition is at or below zero", fontsize=10)
    ax.grid(True, axis="x", alpha=0.25, lw=0.5)
    _save(fig, "fig2_forest")


# --- Figure 3: anchoring similarity bars -----------------------------------
def _similarity(model: str, cond: str) -> float:
    import difflib

    from sia.bench import extract_code

    run_id = EXP004[f"{model}|mbpp+|{cond}|k={K_MAX}"]
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


def fig_anchoring() -> dict:
    sims = {(m, c): _similarity(m, c) for m in MODELS for c in REPAIR_CONDS}
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    width = 0.2
    xs = range(len(MODELS))
    for i, cond in enumerate(REPAIR_CONDS):
        vals = [sims[(m, cond)] for m in MODELS]
        ax.bar(
            [x + (i - 1.5) * width for x in xs],
            vals,
            width,
            color=COLOR[cond],
            label=cond,
        )
    ax.set_xticks(list(xs))
    ax.set_xticklabels([SHORT[m] for m in MODELS])
    ax.set_ylabel("mean inter-attempt\ncode similarity")
    ax.set_title("Anchoring: shown its own code, the model edits instead of rethinking", fontsize=9)
    ax.legend(frameon=False, fontsize=8, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    ax.grid(True, axis="y", alpha=0.25, lw=0.5)
    _save(fig, "fig3_anchoring")
    return sims


# --- Figure 4: Pareto (pass@1 vs tokens) -----------------------------------
def fig_pareto() -> None:
    fig, ax = plt.subplots(figsize=(6.0, 4.0))
    markers = {SHORT[MODELS[0]]: "o", SHORT[MODELS[1]]: "s", SHORT[MODELS[2]]: "^"}
    for model in MODELS:
        for cond in REPAIR_CONDS:
            curve, tokens, _ = repair_curve(model, cond)
            ax.scatter(
                tokens / 1000,
                curve[-1],
                color=COLOR[cond],
                marker=markers[SHORT[model]],
                s=55,
                edgecolor="white",
                lw=0.5,
                zorder=3,
            )
    # Legends: colour = condition, marker = model.
    from matplotlib.lines import Line2D

    cond_handles = [
        Line2D([], [], marker="o", ls="", color=COLOR[c], label=c) for c in REPAIR_CONDS
    ]
    model_handles = [
        Line2D([], [], marker=markers[SHORT[m]], ls="", color="#555", label=SHORT[m])
        for m in MODELS
    ]
    leg1 = ax.legend(
        handles=cond_handles, frameon=False, fontsize=8, loc="lower right", title="condition"
    )
    ax.add_artist(leg1)
    ax.legend(handles=model_handles, frameon=False, fontsize=8, loc="upper left", title="model")
    ax.set_xlabel("output tokens at k=8 (thousands, log scale)")
    ax.set_ylabel("pass@1 at k=8 (MBPP+)")
    ax.set_xscale("log")
    ax.set_title("Blind resampling is Pareto-optimal: best accuracy, least cost", fontsize=9.5)
    ax.grid(True, alpha=0.25, lw=0.5)
    _save(fig, "fig4_pareto")


# --- Figure 5: anchoring vs pass@1 (the ordering result) -------------------
def fig_ordering(sims: dict) -> None:
    fig, ax = plt.subplots(figsize=(5.6, 4.2))
    own = ["placebo", "feedback", "reflect"]
    for model in MODELS:
        pts = []
        for cond in own:
            curve, _, _ = repair_curve(model, cond)
            pts.append((sims[(model, cond)], curve[-1], cond))
        pts.sort()
        ax.plot(
            [p[0] for p in pts],
            [p[1] for p in pts],
            "-",
            color="#ccc",
            lw=1,
            zorder=1,
        )
        for sim, acc, cond in pts:
            ax.scatter(sim, acc, color=COLOR[cond], s=60, zorder=3, edgecolor="white", lw=0.5)
            ax.annotate(
                f"{SHORT[model][:3]}·{cond[:4]}",
                (sim, acc),
                fontsize=6.5,
                xytext=(3, 3),
                textcoords="offset points",
                color="#555",
            )
    ax.set_xlabel("mean inter-attempt similarity (more anchored →)")
    ax.set_ylabel("pass@1 at k=8")
    ax.set_title("Among own-output conditions,\nmore anchoring = worse accuracy", fontsize=9.5)
    ax.grid(True, alpha=0.25, lw=0.5)
    _save(fig, "fig5_ordering")


# --- Figure 6: memory null -------------------------------------------------
def fig_memory() -> None:
    fig, ax = plt.subplots(figsize=(6.0, 3.4))
    width = 0.25
    xs = range(len(MODELS))
    for i, cond in enumerate(MEM_CONDS):
        vals = []
        for m in MODELS:
            r = analyze_run(EXP006[f"{m}|mbpp+|{cond}|k=0"], runs_dir=RUNS)
            vals.append(r.pass_rate)
        ax.bar(
            [x + (i - 1) * width for x in xs],
            vals,
            width,
            color=COLOR[cond],
            label=cond,
        )
    ax.set_xticks(list(xs))
    ax.set_xticklabels([SHORT[m] for m in MODELS])
    ax.set_ylabel("pass@1 (MBPP+)")
    ax.set_ylim(0.4, 0.8)
    ax.set_title("Retrieved experience: a clean null at every scale", fontsize=9.5)
    ax.legend(frameon=False, fontsize=8, ncol=3, loc="upper left")
    ax.grid(True, axis="y", alpha=0.25, lw=0.5)
    _save(fig, "fig6_memory")


def _save(fig: plt.Figure, name: str) -> None:
    for ext in ("pdf", "png"):
        fig.savefig(FIG / f"{name}.{ext}")
    plt.close(fig)
    print(f"wrote {name}.pdf / .png")


def main() -> None:
    fig_kcurves()
    fig_forest()
    sims = fig_anchoring()
    fig_pareto()
    fig_ordering(sims)
    fig_memory()
    print(f"\nAll figures in {FIG}")


if __name__ == "__main__":
    main()
