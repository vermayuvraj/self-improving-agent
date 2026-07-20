import json

import pytest

from sia.bench import assemble_program, extract_code, pass_at_k, wilson_ci
from sia.bench.humaneval import parse_humaneval
from sia.bench.mbpp import parse_mbpp
from sia.sandbox import run_python

# --- pass@k -----------------------------------------------------------------


def test_pass_at_k_known_values():
    assert pass_at_k(1, 1, 1) == 1.0
    assert pass_at_k(1, 0, 1) == 0.0
    assert pass_at_k(2, 1, 1) == pytest.approx(0.5)
    assert pass_at_k(5, 0, 5) == 0.0
    assert pass_at_k(10, 3, 10) == 1.0  # n - c < k
    # n=4, c=2, k=2: 1 - C(2,2)/C(4,2) = 1 - 1/6
    assert pass_at_k(4, 2, 2) == pytest.approx(1 - 1 / 6)


def test_pass_at_k_validation():
    with pytest.raises(ValueError):
        pass_at_k(0, 0, 1)
    with pytest.raises(ValueError):
        pass_at_k(5, 6, 1)


def test_wilson_ci_sanity():
    lo, hi = wilson_ci(50, 100)
    assert lo < 0.5 < hi
    assert (lo, hi) == pytest.approx((0.404, 0.596), abs=0.01)
    lo0, hi0 = wilson_ci(0, 20)
    assert lo0 == 0.0 and hi0 < 0.25


# --- code extraction ----------------------------------------------------------


def test_extract_python_fence():
    text = "Here you go:\n```python\ndef f():\n    return 1\n```\nHope it helps!"
    assert extract_code(text) == "def f():\n    return 1"


def test_extract_prefers_def_block():
    text = "```python\nx = 1\n```\n```python\ndef f():\n    return 1\n```"
    assert "def f" in extract_code(text)


def test_extract_generic_fence_and_raw():
    assert extract_code("```\ndef g(): pass\n```") == "def g(): pass"
    assert extract_code("def h(): pass") == "def h(): pass"


# --- program assembly ---------------------------------------------------------

HUMANEVAL_FIXTURE = json.dumps(
    {
        "task_id": "HumanEval/0",
        "prompt": 'def add(a, b):\n    """Add two numbers."""\n',
        "entry_point": "add",
        "canonical_solution": "    return a + b\n",
        "test": "def check(candidate):\n    assert candidate(1, 2) == 3",
    }
)

MBPP_FIXTURE = "\n".join(
    json.dumps(row)
    for row in [
        {
            "task_id": 11,
            "text": "Write a function to add two numbers.",
            "code": "def add(a, b):\n    return a + b",
            "test_list": ["assert add(1, 2) == 3", "assert add(0, 0) == 0"],
            "test_setup_code": "",
        },
        {
            "task_id": 999,  # outside test split, must be filtered
            "text": "ignore",
            "code": "",
            "test_list": [],
            "test_setup_code": "",
        },
    ]
)


def test_humaneval_parse_and_standalone_assembly():
    task = parse_humaneval(HUMANEVAL_FIXTURE)[0]
    assert task.task_id == "HumanEval/0"
    assert "def add" in task.instruction

    output = "```python\ndef add(a, b):\n    return a + b\n```"
    program = assemble_program(task, output)
    assert run_python(program).ok


def test_humaneval_completion_fallback_assembly():
    task = parse_humaneval(HUMANEVAL_FIXTURE)[0]
    # Bare body, no def: must be appended to the source prompt.
    program = assemble_program(task, "    return a + b")
    assert program.startswith("def add")
    assert run_python(program).ok


def test_humaneval_fallback_reindents_unindented_body():
    task = parse_humaneval(HUMANEVAL_FIXTURE)[0]
    program = assemble_program(task, "return a + b")
    assert run_python(program).ok


def test_humaneval_canonical_solution_passes_own_tests():
    task = parse_humaneval(HUMANEVAL_FIXTURE)[0]
    program = f"{task.canonical_solution}\n\n{task.tests}\n"
    assert run_python(program).ok


def test_mbpp_parse_filters_split_and_assembles():
    tasks = parse_mbpp(MBPP_FIXTURE)
    assert [t.task_id for t in tasks] == ["mbpp/11"]
    task = tasks[0]
    program = assemble_program(task, "```python\ndef add(a, b):\n    return a + b\n```")
    assert run_python(program).ok
    bad = assemble_program(task, "```python\ndef add(a, b):\n    return a - b\n```")
    assert not run_python(bad).ok


# --- real datasets (network) ----------------------------------------------------


@pytest.mark.network
def test_real_datasets_load_and_canonical_solutions_pass(tmp_path):
    """Harness self-check: canonical solutions must pass our assembly+sandbox."""
    from sia.bench import load_tasks

    he_tasks = load_tasks("humaneval", data_dir=tmp_path)
    assert len(he_tasks) == 164
    mbpp_tasks = load_tasks("mbpp", data_dir=tmp_path)
    assert len(mbpp_tasks) == 500

    for task in he_tasks[:10]:
        program = f"{task.canonical_solution}\n\n{task.tests}\n"
        assert run_python(program).ok, f"canonical failed: {task.task_id}"
    for task in mbpp_tasks[:10]:
        program = f"{task.canonical_solution}\n\n{task.tests}\n"
        assert run_python(program).ok, f"canonical failed: {task.task_id}"
