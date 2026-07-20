from __future__ import annotations

import gzip
import json
from pathlib import Path

from sia.bench.base import DEFAULT_DATA_DIR, BenchTask, fetch_cached

HUMANEVAL_URL = "https://github.com/openai/human-eval/raw/master/data/HumanEval.jsonl.gz"

_INSTRUCTION_TEMPLATE = """\
Complete the following Python function. Respond with the complete function \
(including the signature shown) in a single ```python code block. No explanations.

```python
{prompt}
```"""


def parse_humaneval(jsonl_text: str) -> list[BenchTask]:
    tasks = []
    for line in jsonl_text.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        tests = f"{row['test']}\n\ncheck({row['entry_point']})"
        tasks.append(
            BenchTask(
                bench="humaneval",
                task_id=row["task_id"],
                instruction=_INSTRUCTION_TEMPLATE.format(prompt=row["prompt"].rstrip()),
                tests=tests,
                entry_point=row["entry_point"],
                source_prompt=row["prompt"],
                canonical_solution=row["prompt"] + row["canonical_solution"],
            )
        )
    return tasks


def load_humaneval(data_dir: Path = DEFAULT_DATA_DIR) -> list[BenchTask]:
    raw = fetch_cached(HUMANEVAL_URL, data_dir / "HumanEval.jsonl.gz")
    return parse_humaneval(gzip.decompress(raw).decode("utf-8"))
