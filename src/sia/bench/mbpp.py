from __future__ import annotations

import json
from pathlib import Path

from sia.bench.base import DEFAULT_DATA_DIR, BenchTask, fetch_cached

MBPP_URL = (
    "https://raw.githubusercontent.com/google-research/google-research/master/mbpp/mbpp.jsonl"
)

# Canonical split from the MBPP paper: task_ids 11-510 are the test set.
TEST_ID_RANGE = range(11, 511)

_INSTRUCTION_TEMPLATE = """\
{text}

Your solution must pass these tests:

```python
{tests}
```

Respond with the complete Python solution in a single ```python code block. No explanations."""


def parse_mbpp(jsonl_text: str, ids: range = TEST_ID_RANGE) -> list[BenchTask]:
    tasks = []
    for line in jsonl_text.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row["task_id"] not in ids:
            continue
        setup = row.get("test_setup_code") or ""
        test_lines = [setup, *row["test_list"]] if setup else row["test_list"]
        tests = "\n".join(test_lines)
        tasks.append(
            BenchTask(
                bench="mbpp",
                task_id=f"mbpp/{row['task_id']}",
                instruction=_INSTRUCTION_TEMPLATE.format(
                    text=row["text"].strip(), tests="\n".join(row["test_list"])
                ),
                tests=tests,
                entry_point=None,
                canonical_solution=row["code"],
            )
        )
    return tasks


def load_mbpp(data_dir: Path = DEFAULT_DATA_DIR) -> list[BenchTask]:
    raw = fetch_cached(MBPP_URL, data_dir / "mbpp.jsonl")
    return parse_mbpp(raw.decode("utf-8"))
