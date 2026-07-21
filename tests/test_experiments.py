import json

import pytest

from sia.experiments import ExperimentSpec, GridCell, build_report, format_markdown, load_spec
from sia.experiments.launcher import load_cells, run_experiment

# --- spec -------------------------------------------------------------------


def test_grid_is_full_product_and_deterministic():
    spec = ExperimentSpec(
        id="E",
        title="t",
        models=["m1", "m2"],
        benches=["humaneval+", "mbpp+"],
        conditions=["none", "feedback"],
        repair_ks=[0, 2],
    )
    grid = spec.grid()
    assert len(grid) == 2 * 2 * 2 * 2
    assert grid == spec.grid()  # stable ordering
    assert grid[0] == GridCell("m1", "humaneval+", "none", 0)


def test_spec_rejects_unknown_benchmark():
    with pytest.raises(ValueError, match="unknown benchmark"):
        ExperimentSpec(id="E", title="t", models=["m"], benches=["not-a-bench"])


def test_spec_requires_models_and_benches():
    with pytest.raises(ValueError, match="model"):
        ExperimentSpec(id="E", title="t", models=[], benches=["mbpp+"])
    with pytest.raises(ValueError, match="benchmark"):
        ExperimentSpec(id="E", title="t", models=["m"], benches=[])


def test_spec_rejects_negative_k():
    with pytest.raises(ValueError, match="non-negative"):
        ExperimentSpec(id="E", title="t", models=["m"], benches=["mbpp+"], repair_ks=[-1])


def test_load_spec_roundtrip(tmp_path):
    p = tmp_path / "s.toml"
    p.write_text(
        'id = "E1"\ntitle = "T"\nmodels = ["m"]\nbenches = ["mbpp+"]\nseed = 3\n',
        encoding="utf-8",
    )
    spec = load_spec(p)
    assert spec.id == "E1"
    assert spec.seed == 3
    assert spec.run_kwargs()["seed"] == 3


def test_load_spec_rejects_unknown_field(tmp_path):
    p = tmp_path / "s.toml"
    p.write_text('id="E"\ntitle="T"\nmodels=["m"]\nbenches=["mbpp+"]\ntypo=1\n', encoding="utf-8")
    with pytest.raises(ValueError, match="unknown spec field"):
        load_spec(p)


def test_real_spec_file_is_valid():
    from pathlib import Path

    spec = load_spec(Path("experiments/EXP-003b/spec.toml"))
    assert len(spec.grid()) == 6


# --- launcher ---------------------------------------------------------------


def test_dry_run_touches_nothing(tmp_path):
    spec = ExperimentSpec(id="E", title="t", models=["m"], benches=["mbpp+"])
    cells = run_experiment(spec, experiments_dir=tmp_path, dry_run=True)
    assert cells == {}
    assert not (tmp_path / "E" / "cells.json").exists()


def test_repair_conditions_refuse_to_fabricate(tmp_path):
    """Grid can express M3 conditions, but must not silently produce results."""
    from sia.experiments.launcher import _run_cell

    spec = ExperimentSpec(id="E", title="t", models=["m"], benches=["mbpp+"])
    with pytest.raises(NotImplementedError, match="M3 repair loop"):
        _run_cell(
            spec,
            GridCell("m", "mbpp+", "feedback", 2),
            base_url="http://x",
            api_key=None,
            runs_dir=tmp_path,
            progress=None,
        )


def test_load_cells_resumes(tmp_path):
    spec = ExperimentSpec(id="E", title="t", models=["m"], benches=["mbpp+"])
    d = tmp_path / "E"
    d.mkdir()
    (d / "cells.json").write_text(json.dumps({"m|mbpp+|none|k=0": "run1"}), encoding="utf-8")
    assert load_cells(spec, tmp_path) == {"m|mbpp+|none|k=0": "run1"}


# --- report -----------------------------------------------------------------


def _write_run(runs_dir, run_id, outcomes, max_tokens=2048):
    d = runs_dir / run_id
    d.mkdir(parents=True)
    (d / "manifest.json").write_text(
        json.dumps(
            {"run_id": run_id, "model": "m", "config": {"bench": "mbpp+", "max_tokens": max_tokens}}
        ),
        encoding="utf-8",
    )
    lines = []
    for i, (task_id, passed) in enumerate(outcomes):
        lines.append(
            json.dumps(
                {
                    "type": "llm_response",
                    "data": {
                        "task_id": task_id,
                        "sample": 0,
                        "completion_tokens": 50,
                        "content": "```python\nx\n```",
                    },
                    "seq": 2 * i,
                }
            )
        )
        lines.append(
            json.dumps(
                {
                    "type": "verdict",
                    "data": {
                        "task_id": task_id,
                        "sample": 0,
                        "passed": passed,
                        "timed_out": False,
                        "stdout_tail": "",
                        "stderr_tail": "" if passed else "AssertionError",
                    },
                    "seq": 2 * i + 1,
                }
            )
        )
    (d / "trace.jsonl").write_text("\n".join(lines), encoding="utf-8")


def test_report_pairs_arm_against_its_baseline(tmp_path):
    tasks = [f"T/{i}" for i in range(20)]
    base = [(t, i < 8) for i, t in enumerate(tasks)]  # 8/20
    arm = [(t, i < 14) for i, t in enumerate(tasks)]  # 14/20
    _write_run(tmp_path, "base", base)
    _write_run(tmp_path, "arm", arm)

    rows = build_report(
        {"m|mbpp+|none|k=0": "base", "m|mbpp+|feedback|k=2": "arm"},
        runs_dir=tmp_path,
        bootstrap_iterations=500,
    )
    baseline_row = next(r for r in rows if r.is_baseline)
    arm_row = next(r for r in rows if not r.is_baseline)

    assert baseline_row.delta is None  # baseline is not compared to itself
    assert arm_row.delta == pytest.approx(0.3)
    assert arm_row.p_value is not None and arm_row.p_value < 0.05
    assert arm_row.delta_ci[0] < arm_row.delta < arm_row.delta_ci[1]


def test_report_handles_missing_runs(tmp_path):
    _write_run(tmp_path, "base", [("T/1", True)])
    rows = build_report(
        {"m|mbpp+|none|k=0": "base", "m|mbpp+|feedback|k=1": "absent"},
        runs_dir=tmp_path,
        bootstrap_iterations=100,
    )
    assert len(rows) == 1


def test_format_markdown_shape_and_truncation_flag(tmp_path):
    _write_run(tmp_path, "r", [("T/1", True), ("T/2", False)])
    rows = build_report({"m|mbpp+|none|k=0": "r"}, runs_dir=tmp_path, bootstrap_iterations=100)
    md = format_markdown(rows)
    assert md.startswith("| Model |")
    assert "mbpp+" in md
    assert "⚠" not in md  # nothing truncated in this fixture

    assert format_markdown([]) == "_no completed runs_"
