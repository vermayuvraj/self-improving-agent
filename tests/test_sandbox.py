from sia.sandbox import run_python
from sia.sandbox.local import TRUNCATION_MARKER


def test_success():
    result = run_python("print(1 + 1)")
    assert result.ok
    assert result.exit_code == 0
    assert result.stdout.strip() == "2"
    assert result.duration_ms > 0


def test_assertion_failure_nonzero_exit():
    result = run_python("assert 1 == 2, 'nope'")
    assert not result.ok
    assert result.exit_code != 0
    assert "AssertionError" in result.stderr


def test_infinite_loop_times_out():
    result = run_python("while True: pass", timeout_s=1.5)
    assert result.timed_out
    assert not result.ok
    assert result.exit_code is None
    assert result.duration_ms >= 1500


def test_output_truncation():
    result = run_python("print('x' * 100_000)", max_output_chars=1000)
    assert result.ok
    assert len(result.stdout) <= 1000 + len(TRUNCATION_MARKER)
    assert result.stdout.endswith(TRUNCATION_MARKER)


def test_isolated_cwd_is_temp():
    result = run_python("import os; print(os.getcwd())")
    assert result.ok
    assert "sia-exec-" in result.stdout
