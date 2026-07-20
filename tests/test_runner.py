import json

from sia.bench.humaneval import parse_humaneval
from sia.llm import FakeLLM
from sia.runner import run_benchmark
from sia.trace import RunManifest, read_trace

FIXTURE = "\n".join(
    json.dumps(row)
    for row in [
        {
            "task_id": "HumanEval/0",
            "prompt": 'def add(a, b):\n    """Add two numbers."""\n',
            "entry_point": "add",
            "canonical_solution": "    return a + b\n",
            "test": "def check(candidate):\n    assert candidate(1, 2) == 3",
        },
        {
            "task_id": "HumanEval/1",
            "prompt": 'def sub(a, b):\n    """Subtract b from a."""\n',
            "entry_point": "sub",
            "canonical_solution": "    return a - b\n",
            "test": "def check(candidate):\n    assert candidate(3, 1) == 2",
        },
    ]
)


def test_run_benchmark_end_to_end(tmp_path):
    tasks = parse_humaneval(FIXTURE)
    llm = FakeLLM(
        [
            "```python\ndef add(a, b):\n    return a + b\n```",  # correct
            "```python\ndef sub(a, b):\n    return a + b\n```",  # wrong
        ]
    )
    lines = []
    summary = run_benchmark(
        "humaneval",
        llm,
        tasks=tasks,
        runs_dir=tmp_path / "runs",
        seed=1,
        progress=lines.append,
    )

    assert summary.n_tasks == 2
    assert summary.pass_rates == {"pass@1": 0.5}
    assert summary.ci95 is not None
    assert len(lines) == 2

    manifest = RunManifest.load(summary.run_dir / "manifest.json")
    assert manifest.outcome == "completed"
    assert manifest.totals["llm_calls"] == 2
    assert manifest.totals["pass@1"] == 0.5
    assert manifest.config["agent"] == "single_shot"

    events = read_trace(summary.run_dir / "trace.jsonl")
    types = [e["type"] for e in events]
    assert types.count("task_start") == 2
    assert types.count("llm_call") == 2
    assert types.count("llm_response") == 2
    assert types.count("verdict") == 2
    verdicts = [e["data"]["passed"] for e in events if e["type"] == "verdict"]
    assert verdicts == [True, False]

    rows = [
        json.loads(line) for line in (summary.run_dir / "results.jsonl").read_text().splitlines()
    ]
    assert [r["passed"] for r in rows] == [True, False]


def test_run_benchmark_multi_sample_pass_at_k(tmp_path):
    tasks = parse_humaneval(FIXTURE)[:1]
    llm = FakeLLM(
        [
            "```python\ndef add(a, b):\n    return a + b\n```",
            "```python\ndef add(a, b):\n    return a - b\n```",
        ]
    )
    summary = run_benchmark(
        "humaneval",
        llm,
        tasks=tasks,
        samples=2,
        temperature=0.8,
        runs_dir=tmp_path / "runs",
    )
    assert summary.pass_rates["pass@1"] == 0.5
    assert summary.pass_rates["pass@2"] == 1.0
    assert summary.ci95 is None


def test_llm_error_recorded_not_fatal(tmp_path):
    tasks = parse_humaneval(FIXTURE)
    llm = FakeLLM(["```python\ndef add(a, b):\n    return a + b\n```"])  # second call errors
    summary = run_benchmark("humaneval", llm, tasks=tasks, runs_dir=tmp_path / "runs")

    assert summary.pass_rates["pass@1"] == 0.5
    assert summary.totals["llm_errors"] == 1
    events = read_trace(summary.run_dir / "trace.jsonl")
    assert any(e["type"] == "error" for e in events)
