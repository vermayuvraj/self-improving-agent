import json

import pytest

from sia.analysis import analyze_run, classify, mcnemar_exact, paired_bootstrap_diff

# --- taxonomy ---------------------------------------------------------------


def test_budget_exhausted_outranks_runtime_signal():
    # A truncated response's downstream error says nothing about the model.
    assert classify("SyntaxError: bad", False, budget_exhausted=True) == "budget_exhausted"
    assert classify("", True, budget_exhausted=True) == "budget_exhausted"


def test_classify_buckets():
    assert classify("AssertionError", False) == "wrong_answer"
    assert classify("input#3 wrong answer", False) == "wrong_answer"
    assert classify("SyntaxError: x", False) == "syntax_error"
    assert classify("solution does not define f", False) == "missing_entry_point"
    assert classify("", True) == "timeout"
    assert classify("", False) == "no_output"
    assert classify("ValueError: nope", False) == "other_runtime_error"


def test_classify_evalplus_differential_failure():
    # The EvalPlus harness reports on stdout and exits non-zero; the combined
    # output must classify as a wrong answer, not "other".
    output = (
        "input#7 wrong answer\n  args=[1, 2]\n  expected=3\n  actual  =-1\n"
        "SystemExit: 1 failing input(s) of 999"
    )
    assert classify(output, False) == "wrong_answer"


def test_classify_prefers_crash_over_wrong_answer():
    # EvalPlus prints both signals for a crashing candidate; the crash is the
    # more specific diagnosis.
    output = "input#2 raised TypeError: bad operand\nSystemExit: 1 failing input(s) of 500"
    assert classify(output, False) == "type_error"


def test_failure_output_combines_streams_and_tolerates_old_traces():
    from sia.analysis import failure_output

    assert failure_output({"stdout_tail": "out", "stderr_tail": "err"}) == "out\nerr"
    # Pre-M2 traces have no stdout_tail at all.
    assert failure_output({"stderr_tail": "err"}) == "err"
    assert failure_output({}) == ""


def _write_run(tmp_path, run_id, rows, max_tokens=2048):
    d = tmp_path / run_id
    d.mkdir(parents=True)
    (d / "manifest.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "model": "m",
                "config": {"bench": "humaneval+", "max_tokens": max_tokens},
            }
        ),
        encoding="utf-8",
    )
    lines = []
    for i, (task_id, passed, tokens, content, output) in enumerate(rows):
        lines.append(
            json.dumps(
                {
                    "type": "llm_response",
                    "data": {
                        "task_id": task_id,
                        "sample": 0,
                        "completion_tokens": tokens,
                        "content": content,
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
                        "stderr_tail": output,
                    },
                    "seq": 2 * i + 1,
                }
            )
        )
    (d / "trace.jsonl").write_text("\n".join(lines), encoding="utf-8")
    return d


def test_analyze_run_separates_truncation(tmp_path):
    _write_run(
        tmp_path,
        "r1",
        [
            ("T/1", True, 100, "```python\nok\n```", ""),
            ("T/2", False, 100, "```python\nbad\n```", "AssertionError"),
            ("T/3", False, 2048, "thinking forever", ""),  # truncated
        ],
    )
    report = analyze_run("r1", runs_dir=tmp_path)
    assert report.tasks == 3
    assert report.passed == 1
    assert report.budget_exhausted == 1
    assert report.taxonomy["budget_exhausted"] == 1
    assert report.taxonomy["wrong_answer"] == 1
    assert report.pass_rate == pytest.approx(1 / 3)
    # Conditional rate excludes the truncated task: 1 of 2 scoreable.
    assert report.conditional_pass == pytest.approx(0.5)


def test_conditional_pass_none_when_nothing_truncated(tmp_path):
    _write_run(tmp_path, "r2", [("T/1", True, 50, "```python\nx\n```", "")])
    assert analyze_run("r2", runs_dir=tmp_path).conditional_pass is None


def test_outcomes_keyed_for_pairing(tmp_path):
    _write_run(
        tmp_path,
        "r3",
        [("T/1", True, 10, "```", ""), ("T/2", False, 10, "```", "AssertionError")],
    )
    assert analyze_run("r3", runs_dir=tmp_path).outcomes == {"T/1": True, "T/2": False}


# --- paired statistics ------------------------------------------------------


def test_mcnemar_identical_arms_not_significant():
    a = [True, False, True, False]
    n01, n10, p = mcnemar_exact(a, a)
    assert (n01, n10) == (0, 0)
    assert p == 1.0


def test_mcnemar_counts_discordant_pairs_only():
    a = [True, True, False, False]
    b = [True, False, True, True]
    n01, n10, p = mcnemar_exact(a, b)
    assert n01 == 2  # only b solved
    assert n10 == 1  # only a solved
    assert 0 < p <= 1


def test_mcnemar_strong_effect_is_significant():
    a = [False] * 20
    b = [True] * 20
    _, _, p = mcnemar_exact(a, b)
    assert p < 0.001


def test_mcnemar_rejects_unequal_lengths():
    with pytest.raises(ValueError):
        mcnemar_exact([True], [True, False])


def test_bootstrap_ci_brackets_observed_difference():
    a = [False] * 50 + [True] * 50
    b = [True] * 70 + [False] * 30
    observed, lo, hi = paired_bootstrap_diff(a, b, iterations=2000, seed=1)
    assert observed == pytest.approx(0.2)
    assert lo < observed < hi


def test_bootstrap_no_difference_ci_includes_zero():
    a = [True, False] * 40
    observed, lo, hi = paired_bootstrap_diff(a, list(a), iterations=1000, seed=2)
    assert observed == 0.0
    assert lo <= 0 <= hi
