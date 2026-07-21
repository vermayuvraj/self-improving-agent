"""EvalPlus (HumanEval+ / MBPP+) — rigorous test suites for the base benchmarks.

EvalPlus does not ship expected outputs. It ships *inputs* (``base_input`` +
``plus_input``) and a ``canonical_solution`` that acts as the oracle: a
candidate passes an input if it agrees with the reference on that input.
This module builds that differential-testing program.

Adopted because (a) the base suites are weak enough that a 7B model scores
85%, leaving too few failures to ablate against, and (b) it is the evaluation
substrate used by the small-model self-repair literature, so our numbers are
directly comparable.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any

from sia.bench.base import DEFAULT_DATA_DIR, BenchTask, fetch_cached

HUMANEVAL_PLUS_URL = (
    "https://github.com/evalplus/humanevalplus_release/releases/download/"
    "v0.1.10/HumanEvalPlus.jsonl.gz"
)
MBPP_PLUS_URL = (
    "https://github.com/evalplus/mbppplus_release/releases/download/v0.2.0/MbppPlus.jsonl.gz"
)

# Contract assertions validate inputs; they are not part of the solution under
# test and must be stripped from the oracle before it is used as ground truth.
CONTRACT_MARKER = "# $_CONTRACT_$"

_HUMANEVAL_INSTRUCTION = """\
Complete the following Python function. Respond with the complete function \
(including the signature shown) in a single ```python code block. No explanations.

```python
{prompt}
```"""

_MBPP_INSTRUCTION = """\
{text}

Your solution must satisfy:

```python
{assertion}
```

Respond with the complete Python solution in a single ```python code block. No explanations."""


def _strip_contract(solution: str) -> str:
    return "\n".join(line for line in solution.splitlines() if CONTRACT_MARKER not in line)


# The oracle harness. Runs candidate and reference over every input and
# compares. Kept in a template rather than generated ad hoc so the comparison
# semantics (float tolerance, exception equivalence) are auditable in one place.
_HARNESS = """\
import json
import math
import os
import sys

# The sandbox runs `python -I`, which omits the script directory from sys.path.
# Restore just that directory so the auxiliary modules resolve, without giving
# up the rest of isolated mode.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import reference
import solution

ENTRY = {entry!r}
ATOL = {atol!r}

with open("inputs.json", encoding="utf-8") as fh:
    INPUTS = json.load(fh)

candidate = getattr(solution, ENTRY, None)
if candidate is None:
    raise SystemExit(f"solution does not define {{ENTRY}}")
oracle = getattr(reference, ENTRY)


def equal(a, b):
    if isinstance(a, float) or isinstance(b, float):
        try:
            if math.isnan(a) and math.isnan(b):
                return True
        except TypeError:
            return False
        if ATOL:
            try:
                return math.isclose(a, b, rel_tol=1e-9, abs_tol=ATOL)
            except TypeError:
                return False
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(equal(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(equal(a[k], b[k]) for k in a)
    try:
        return a == b
    except Exception:
        return False


failures = 0
for index, args in enumerate(INPUTS):
    try:
        expected = oracle(*args)
    except BaseException:
        continue  # oracle rejects this input; not a fair test
    try:
        actual = candidate(*args)
    except BaseException as exc:
        print(f"input#{{index}} raised {{type(exc).__name__}}: {{exc}}")
        print(f"  args={{args!r:.400}}")
        failures += 1
        if failures >= 3:
            break
        continue
    if not equal(actual, expected):
        print(f"input#{{index}} wrong answer")
        print(f"  args={{args!r:.400}}")
        print(f"  expected={{expected!r:.200}}")
        print(f"  actual  ={{actual!r:.200}}")
        failures += 1
        if failures >= 3:
            break

if failures:
    raise SystemExit(f"{{failures}} failing input(s) of {{len(INPUTS)}}")
"""


def build_program(task: BenchTask, solution_code: str) -> tuple[str, dict[str, str]]:
    """Return (main program, auxiliary files) for differential testing."""
    spec: dict[str, Any] = json.loads(task.tests)
    harness = _HARNESS.format(entry=task.entry_point, atol=spec["atol"])
    return harness, {
        "solution.py": solution_code,
        "reference.py": spec["reference"],
        "inputs.json": json.dumps(spec["inputs"]),
    }


def _parse(rows: list[dict[str, Any]], bench: str) -> list[BenchTask]:
    tasks = []
    for row in rows:
        if bench == "humaneval+":
            reference = row["prompt"] + _strip_contract(row["canonical_solution"])
            instruction = _HUMANEVAL_INSTRUCTION.format(prompt=row["prompt"].rstrip())
        else:
            reference = _strip_contract(row["canonical_solution"])
            text = row["prompt"].strip().strip('"').strip()
            instruction = _MBPP_INSTRUCTION.format(
                text=text.split("assert")[0].strip(), assertion=row["assertion"].strip()
            )
        spec = {
            "reference": reference,
            "inputs": list(row["base_input"]) + list(row["plus_input"]),
            "atol": row.get("atol", 0),
        }
        tasks.append(
            BenchTask(
                bench=bench,
                task_id=row["task_id"],
                instruction=instruction,
                tests=json.dumps(spec),
                entry_point=row["entry_point"],
                source_prompt=row["prompt"] if bench == "humaneval+" else "",
                canonical_solution=reference,
            )
        )
    return tasks


def load_evalplus(bench: str, data_dir: Path = DEFAULT_DATA_DIR) -> list[BenchTask]:
    url, name = (
        (HUMANEVAL_PLUS_URL, "HumanEvalPlus")
        if bench == "humaneval+"
        else (MBPP_PLUS_URL, "MbppPlus")
    )
    raw = fetch_cached(url, data_dir / f"{name}.jsonl.gz")
    rows = [
        json.loads(line)
        for line in gzip.decompress(raw).decode("utf-8").splitlines()
        if line.strip()
    ]
    return _parse(rows, bench)
