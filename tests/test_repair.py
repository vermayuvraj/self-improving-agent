import json

import pytest

from sia.bench.humaneval import parse_humaneval
from sia.llm import FakeLLM
from sia.repair import CONDITIONS, build_retry_messages, repair_task
from sia.repair.conditions import summarize_failure
from sia.repair.runner import load_baseline, run_repair
from sia.sandbox import ExecResult
from sia.trace import TraceWriter

FIXTURE = json.dumps(
    {
        "task_id": "HumanEval/0",
        "prompt": 'def add(a, b):\n    """Add two numbers."""\n',
        "entry_point": "add",
        "canonical_solution": "    return a + b\n",
        "test": "def check(candidate):\n    assert candidate(1, 2) == 3",
    }
)
TASK = parse_humaneval(FIXTURE)[0]

GOOD = "```python\ndef add(a, b):\n    return a + b\n```"
BAD = "```python\ndef add(a, b):\n    return a - b\n```"


def fail_result(stdout="input#0 wrong answer\n  expected=3\n  actual  =-1", stderr="SystemExit: 1"):
    return ExecResult(exit_code=1, stdout=stdout, stderr=stderr, timed_out=False, duration_ms=1.0)


# --- conditions: the placebo design -----------------------------------------


def test_resample_is_identical_to_first_attempt():
    """Any gain here is the value of another draw, not of feedback."""
    msgs = build_retry_messages(TASK, "resample", previous_code="def add(): pass", failure="boom")
    body = msgs[-1].content
    assert body == TASK.instruction
    assert "previous" not in body.lower()
    assert "boom" not in body


def test_placebo_shows_code_but_no_failure_facts():
    msgs = build_retry_messages(
        TASK, "placebo", previous_code="def add(a,b): return a-b", failure="expected=3 actual=-1"
    )
    body = msgs[-1].content
    assert "def add(a,b): return a-b" in body  # sees its own attempt
    assert "incorrect" in body  # told it failed
    assert "expected=3" not in body  # but not why
    assert "actual" not in body


def test_feedback_includes_the_facts():
    msgs = build_retry_messages(
        TASK, "feedback", previous_code="def add(a,b): return a-b", failure="expected=3 actual=-1"
    )
    body = msgs[-1].content
    assert "def add(a,b): return a-b" in body
    assert "expected=3 actual=-1" in body


def test_placebo_and_feedback_differ_only_by_facts():
    """The contrast that licenses attributing a gain to content."""
    common = {"previous_code": "code", "failure": "FACTS_HERE"}
    p = build_retry_messages(TASK, "placebo", **common)[-1].content
    f = build_retry_messages(TASK, "feedback", **common)[-1].content
    assert "FACTS_HERE" in f and "FACTS_HERE" not in p
    # Both carry the task, the code, and a comparable instruction.
    for body in (p, f):
        assert TASK.instruction in body
        assert "code" in body
        assert "incorrect" in body


def test_all_conditions_keep_the_original_instruction():
    for condition in CONDITIONS:
        msgs = build_retry_messages(TASK, condition, previous_code="c", failure="f")
        assert TASK.instruction in msgs[-1].content


def test_unknown_condition_rejected():
    with pytest.raises(ValueError, match="unknown repair condition"):
        build_retry_messages(TASK, "telepathy", previous_code="c", failure="f")


def test_summarize_failure_cases():
    assert "timed out" in summarize_failure("", "", timed_out=True)
    assert "no output" in summarize_failure("", "", timed_out=False)
    assert summarize_failure("out", "err", timed_out=False) == "out\nerr"
    long = "x" * 5000
    out = summarize_failure(long, "", timed_out=False)
    assert len(out) < 2000
    assert out.startswith("...[earlier output truncated]")
    assert out.endswith("x")  # keeps the tail, where the diagnosis lives


# --- loop: nested k ---------------------------------------------------------


def test_already_passing_task_costs_nothing(tmp_path):
    llm = FakeLLM([])
    with TraceWriter(tmp_path / "t.jsonl", "r") as tr:
        out = repair_task(
            TASK,
            llm,
            tr,
            condition="feedback",
            k_max=8,
            initial_code="x",
            initial_result=fail_result(),
            initial_passed=True,
        )
    assert out.passed_at == [True]
    assert out.iterations_used == 0
    assert llm.calls == []  # no LLM call made
    assert all(out.passed_by(k) for k in range(9))


def test_stops_early_on_success_and_nests_k(tmp_path):
    # Fails first retry, succeeds on the second.
    llm = FakeLLM([BAD, GOOD, GOOD])
    with TraceWriter(tmp_path / "t.jsonl", "r") as tr:
        out = repair_task(
            TASK,
            llm,
            tr,
            condition="feedback",
            k_max=8,
            initial_code="def add(a,b): return a-b",
            initial_result=fail_result(),
            initial_passed=False,
        )
    assert out.passed_at == [False, False, True]
    assert out.iterations_used == 2
    assert len(llm.calls) == 2  # stopped, did not burn the remaining 6

    # The nested k-curve: unsolved at k<2, solved from k=2 onward.
    assert not out.passed_by(0)
    assert not out.passed_by(1)
    assert out.passed_by(2)
    assert out.passed_by(8)


def test_never_succeeds_uses_full_budget(tmp_path):
    llm = FakeLLM([BAD] * 3)
    with TraceWriter(tmp_path / "t.jsonl", "r") as tr:
        out = repair_task(
            TASK,
            llm,
            tr,
            condition="placebo",
            k_max=3,
            initial_code="c",
            initial_result=fail_result(),
            initial_passed=False,
        )
    assert out.passed_at == [False, False, False, False]
    assert out.iterations_used == 3
    assert not out.passed_by(3)


def test_llm_error_ends_repair_without_crashing(tmp_path):
    llm = FakeLLM([BAD])  # second call raises
    with TraceWriter(tmp_path / "t.jsonl", "r") as tr:
        out = repair_task(
            TASK,
            llm,
            tr,
            condition="feedback",
            k_max=5,
            initial_code="c",
            initial_result=fail_result(),
            initial_passed=False,
        )
    assert not out.passed_by(5)
    assert len(out.passed_at) >= 2


def test_greedy_repair_is_rejected(tmp_path):
    """At temperature 0 every retry returns the identical solution, which
    silently reduces `resample` to a no-op and flattens every k-curve."""
    llm = FakeLLM([BAD])
    with (
        TraceWriter(tmp_path / "t.jsonl", "r") as tr,
        pytest.raises(ValueError, match="temperature > 0"),
    ):
        repair_task(
            TASK,
            llm,
            tr,
            condition="resample",
            k_max=2,
            temperature=0.0,
            initial_code="c",
            initial_result=fail_result(),
            initial_passed=False,
        )


def test_default_repair_temperature_samples():
    from sia.repair import REPAIR_TEMPERATURE

    assert REPAIR_TEMPERATURE > 0


def test_seed_varies_per_iteration_so_resample_redraws(tmp_path):
    """A fixed seed would make `resample` return the same sample forever,
    silently turning the control into a no-op."""
    seeds = []

    class SeedSpy(FakeLLM):
        def complete(self, messages, **kw):
            seeds.append(kw.get("seed"))
            return super().complete(messages, **kw)

    llm = SeedSpy([BAD, BAD])
    with TraceWriter(tmp_path / "t.jsonl", "r") as tr:
        repair_task(
            TASK,
            llm,
            tr,
            condition="resample",
            k_max=2,
            seed=7,
            initial_code="c",
            initial_result=fail_result(),
            initial_passed=False,
        )
    assert seeds == [8, 9]
    assert len(set(seeds)) == len(seeds)


# --- runner: baseline reuse -------------------------------------------------


def _write_baseline(tmp_path, outcomes):
    run_dir = tmp_path / "base"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text(
        json.dumps({"run_id": "base", "model": "m", "config": {"bench": "humaneval"}}),
        encoding="utf-8",
    )
    lines = []
    for i, (task_id, passed, content) in enumerate(outcomes):
        lines.append(
            json.dumps(
                {
                    "type": "llm_response",
                    "seq": 2 * i,
                    "data": {
                        "task_id": task_id,
                        "sample": 0,
                        "content": content,
                        "prompt_tokens": 10,
                        "completion_tokens": 10,
                        "latency_ms": 1,
                    },
                }
            )
        )
        lines.append(
            json.dumps(
                {
                    "type": "verdict",
                    "seq": 2 * i + 1,
                    "data": {
                        "task_id": task_id,
                        "sample": 0,
                        "passed": passed,
                        "timed_out": False,
                        "stdout_tail": "" if passed else "input#0 wrong answer",
                        "stderr_tail": "" if passed else "SystemExit: 1",
                    },
                }
            )
        )
    (run_dir / "trace.jsonl").write_text("\n".join(lines), encoding="utf-8")


def test_load_baseline_recovers_code_and_failure(tmp_path):
    _write_baseline(tmp_path, [("HumanEval/0", False, BAD)])
    loaded = load_baseline("base", "humaneval", runs_dir=tmp_path, tasks=[TASK])
    assert len(loaded) == 1
    assert loaded[0].passed is False
    assert "return a - b" in loaded[0].code
    assert "wrong answer" in loaded[0].stdout


def test_run_repair_skips_solved_tasks_and_reports_k_curve(tmp_path):
    task2 = parse_humaneval(
        json.dumps(
            {
                "task_id": "HumanEval/1",
                "prompt": 'def sub(a, b):\n    """Sub."""\n',
                "entry_point": "sub",
                "canonical_solution": "    return a - b\n",
                "test": "def check(candidate):\n    assert candidate(3, 1) == 2",
            }
        )
    )[0]
    # Task 0 already solved at baseline; task 1 failed.
    bad_sub = "```python\ndef sub(a,b): return a+b\n```"
    _write_baseline(tmp_path, [("HumanEval/0", True, GOOD), ("HumanEval/1", False, bad_sub)])

    llm = FakeLLM({"def sub": "```python\ndef sub(a, b):\n    return a - b\n```"})
    summary = run_repair(
        "humaneval",
        llm,
        condition="feedback",
        k_max=4,
        baseline_run_id="base",
        runs_dir=tmp_path,
        tasks=[TASK, task2],
        workers=1,
    )

    assert summary.totals["baseline_failures"] == 1  # only one task repaired
    assert len(llm.calls) == 1  # solved task cost nothing
    assert summary.pass_at_k[0] == pytest.approx(0.5)  # baseline
    assert summary.pass_at_k[1] == pytest.approx(1.0)  # repaired on first try
    assert summary.pass_at_k[4] == pytest.approx(1.0)  # monotonic in k


def test_pass_at_k_is_monotonic(tmp_path):
    _write_baseline(tmp_path, [("HumanEval/0", False, BAD)])
    llm = FakeLLM({"Add two numbers": BAD})  # never fixes it
    summary = run_repair(
        "humaneval",
        llm,
        condition="placebo",
        k_max=3,
        baseline_run_id="base",
        runs_dir=tmp_path,
        tasks=[TASK],
        workers=1,
    )
    values = [summary.pass_at_k[k] for k in range(4)]
    assert values == sorted(values)  # non-decreasing
    assert summary.totals["prompt_tokens"] > 0
