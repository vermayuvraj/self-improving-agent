import json

import pytest

from sia.bench import BenchTask, build_execution
from sia.bench.evalplus import CONTRACT_MARKER, _strip_contract
from sia.sandbox import run_python


def make_task(reference, inputs, entry="f", atol=0, bench="humaneval+"):
    return BenchTask(
        bench=bench,
        task_id="T/1",
        instruction="",
        tests=json.dumps({"reference": reference, "inputs": inputs, "atol": atol}),
        entry_point=entry,
    )


def test_strip_contract_removes_only_marked_lines():
    src = f"\n    assert x > 0, 'bad' {CONTRACT_MARKER}\n    return x + 1\n"
    out = _strip_contract(src)
    assert "assert" not in out
    assert "return x + 1" in out


def test_correct_solution_passes():
    task = make_task("def f(a, b):\n    return a + b\n", [[1, 2], [3, 4], [-1, 1]])
    program, aux = build_execution(task, "```python\ndef f(a, b):\n    return a + b\n```")
    result = run_python(program, files=aux)
    assert result.ok, result.stderr


def test_wrong_solution_fails_with_diagnostic():
    task = make_task("def f(a, b):\n    return a + b\n", [[1, 2], [3, 4]])
    program, aux = build_execution(task, "```python\ndef f(a, b):\n    return a - b\n```")
    result = run_python(program, files=aux)
    assert not result.ok
    combined = result.stdout + result.stderr
    assert "wrong answer" in combined
    assert "expected=" in combined


def test_exception_in_candidate_is_reported():
    task = make_task("def f(a):\n    return a\n", [[1]])
    program, aux = build_execution(task, "```python\ndef f(a):\n    raise ValueError('boom')\n```")
    result = run_python(program, files=aux)
    assert not result.ok
    assert "ValueError" in result.stdout + result.stderr


def test_missing_entry_point_fails_cleanly():
    task = make_task("def f(a):\n    return a\n", [[1]])
    program, aux = build_execution(task, "```python\ndef other(a):\n    return a\n```")
    result = run_python(program, files=aux)
    assert not result.ok
    assert "does not define f" in result.stdout + result.stderr


def test_float_tolerance_respected():
    task = make_task("def f(a):\n    return a / 3\n", [[1.0]], atol=1e-6)
    program, aux = build_execution(task, "```python\ndef f(a):\n    return a * 0.3333333333\n```")
    assert run_python(program, files=aux).ok


def test_oracle_rejected_inputs_are_skipped():
    # Oracle raises on the second input; candidate is correct on the first.
    ref = "def f(a):\n    if a < 0:\n        raise ValueError\n    return a * 2\n"
    task = make_task(ref, [[2], [-5]])
    program, aux = build_execution(task, "```python\ndef f(a):\n    return a * 2\n```")
    assert run_python(program, files=aux).ok


def test_sandbox_rejects_path_in_aux_filename():
    with pytest.raises(ValueError, match="must not contain a path"):
        run_python("pass", files={"../escape.py": "x = 1"})


@pytest.mark.network
@pytest.mark.parametrize("bench", ["humaneval+", "mbpp+"])
def test_real_evalplus_canonical_solutions_pass(bench, tmp_path):
    """Harness self-check: EvalPlus canonical solutions must pass EvalPlus tests.

    This is the check that catches oracle/contract handling bugs — a broken
    harness would silently deflate every score reported against it.
    """
    from sia.bench import load_tasks

    tasks = load_tasks(bench, data_dir=tmp_path)
    assert len(tasks) > 100
    for task in tasks[:15]:
        program, aux = build_execution(task, f"```python\n{task.canonical_solution}\n```")
        result = run_python(program, timeout_s=60, files=aux)
        assert result.ok, f"{task.task_id} failed:\n{result.stdout}\n{result.stderr}"
