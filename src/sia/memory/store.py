"""Episodic store of solved tasks, mined from our own run traces (ADR-0003).

The store is the payoff of trace-first design: every benchmark and repair run
already recorded what the model wrote and whether it worked, so experience
costs no new inference to collect.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from sia.bench import extract_code
from sia.trace import read_jsonl

# Trailing response-format directives shared by every benchmark instruction.
_FORMAT_MARKERS = ("Respond with the complete", "Complete the following Python function")


def _strip_format_instruction(instruction: str) -> str:
    text = instruction.strip()
    for marker in _FORMAT_MARKERS:
        index = text.find(marker)
        if index != -1:
            text = text[:index].rstrip()
    return text


@dataclass(frozen=True)
class MemoryItem:
    """One solved task: the problem as posed, and code that passed its tests."""

    task_id: str
    bench: str
    instruction: str
    code: str
    source_run: str
    source_model: str

    def as_exemplar(self) -> str:
        """Render for inclusion in a prompt: problem statement, then solution.

        The response-format instruction is stripped from the exemplar's text.
        It belongs to the task the model is actually being asked to solve;
        repeating it once per exemplar is noise that competes with the real
        instruction at the end of the prompt.
        """
        problem = _strip_format_instruction(self.instruction)
        return f"Problem:\n{problem}\n\nWorking solution:\n```python\n{self.code.strip()}\n```"


class MemoryStore:
    """A collection of solved tasks, deduplicated by task_id."""

    def __init__(self, items: list[MemoryItem] | None = None) -> None:
        self._by_task: dict[str, MemoryItem] = {}
        for item in items or []:
            self.add(item)

    def add(self, item: MemoryItem) -> None:
        # Keep the first solution seen for a task. Later duplicates come from
        # other models solving the same problem and add no new information
        # about *that* problem.
        self._by_task.setdefault(item.task_id, item)

    @property
    def items(self) -> list[MemoryItem]:
        return list(self._by_task.values())

    def __len__(self) -> int:
        return len(self._by_task)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(asdict(i)) + "\n" for i in self.items), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> MemoryStore:
        items = [
            MemoryItem(**json.loads(line))
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        return cls(items)


def mine_from_runs(
    run_ids: list[str],
    *,
    runs_dir: Path = Path("runs"),
    bench_filter: str | None = None,
    instructions: dict[str, str] | None = None,
) -> MemoryStore:
    """Extract solved (task, code) pairs from completed run traces.

    ``instructions`` supplies the task text by id (the trace stores prompts
    inside message payloads; passing the loaded benchmark is cheaper and
    exact).
    """
    store = MemoryStore()
    for run_id in run_ids:
        run_dir = runs_dir / run_id
        manifest_path = run_dir / "manifest.json"
        trace_path = run_dir / "trace.jsonl"
        if not trace_path.exists() or not manifest_path.exists():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        bench = manifest["config"]["bench"]
        if bench_filter and bench != bench_filter:
            continue
        model = manifest.get("model", "")

        # Pair each passing verdict with the response that produced it. Keyed
        # by (task, sample, iteration) so repair traces resolve correctly.
        responses: dict[tuple, str] = {}
        for event in read_jsonl(trace_path):
            data = event["data"]
            key = (data.get("task_id"), data.get("sample"), data.get("iteration"))
            if event["type"] == "llm_response":
                responses[key] = data["content"]
            elif event["type"] == "verdict" and data.get("passed"):
                content = responses.get(key)
                if not content:
                    continue
                code = extract_code(content)
                if not code.strip():
                    continue
                task_id = data["task_id"]
                instruction = (instructions or {}).get(task_id)
                if instruction is None:
                    continue
                store.add(
                    MemoryItem(
                        task_id=task_id,
                        bench=bench,
                        instruction=instruction,
                        code=code,
                        source_run=run_id,
                        source_model=model,
                    )
                )
    return store
