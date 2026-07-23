import json

from sia.bench.humaneval import parse_humaneval
from sia.memory import (
    MEMORY_CONDITIONS,
    MemoryItem,
    MemoryStore,
    Retriever,
    build_memory_messages,
    mine_from_runs,
)
from sia.memory.retrieve import tokenize

TASK = parse_humaneval(
    json.dumps(
        {
            "task_id": "HumanEval/0",
            "prompt": 'def add(a, b):\n    """Add two numbers."""\n',
            "entry_point": "add",
            "canonical_solution": "    return a + b\n",
            "test": "def check(candidate):\n    assert candidate(1, 2) == 3",
        }
    )
)[0]


def item(task_id, instruction, code="def f(): pass"):
    return MemoryItem(
        task_id=task_id,
        bench="mbpp+",
        instruction=instruction,
        code=code,
        source_run="r",
        source_model="m",
    )


# --- store ------------------------------------------------------------------


def test_store_dedupes_by_task():
    s = MemoryStore([item("T/1", "first"), item("T/1", "second"), item("T/2", "other")])
    assert len(s) == 2
    assert next(i for i in s.items if i.task_id == "T/1").instruction == "first"


def test_store_roundtrip(tmp_path):
    s = MemoryStore([item("T/1", "sort a list"), item("T/2", "reverse a string")])
    p = tmp_path / "mem.jsonl"
    s.save(p)
    assert {i.task_id for i in MemoryStore.load(p).items} == {"T/1", "T/2"}


def _write_run(tmp_path, run_id, rows, bench="mbpp+"):
    d = tmp_path / run_id
    d.mkdir(parents=True)
    (d / "manifest.json").write_text(
        json.dumps({"run_id": run_id, "model": "m", "config": {"bench": bench}}),
        encoding="utf-8",
    )
    lines = []
    for i, (task_id, passed, content) in enumerate(rows):
        lines.append(
            json.dumps(
                {
                    "type": "llm_response",
                    "seq": 2 * i,
                    "data": {"task_id": task_id, "sample": 0, "content": content},
                }
            )
        )
        lines.append(
            json.dumps(
                {
                    "type": "verdict",
                    "seq": 2 * i + 1,
                    "data": {"task_id": task_id, "sample": 0, "passed": passed},
                }
            )
        )
    (d / "trace.jsonl").write_text("\n".join(lines), encoding="utf-8")


def test_mine_keeps_only_solved(tmp_path):
    _write_run(
        tmp_path,
        "r1",
        [
            ("T/1", True, "```python\ndef good(): return 1\n```"),
            ("T/2", False, "```python\ndef bad(): return 0\n```"),
        ],
    )
    store = mine_from_runs(
        ["r1"], runs_dir=tmp_path, instructions={"T/1": "task one", "T/2": "task two"}
    )
    assert [i.task_id for i in store.items] == ["T/1"]
    assert "def good" in store.items[0].code


def test_mine_skips_tasks_without_instructions(tmp_path):
    _write_run(tmp_path, "r1", [("T/1", True, "```python\ndef x(): pass\n```")])
    assert len(mine_from_runs(["r1"], runs_dir=tmp_path, instructions={})) == 0


def test_mine_respects_bench_filter(tmp_path):
    _write_run(tmp_path, "r1", [("T/1", True, "```python\ndef x(): pass\n```")], bench="humaneval+")
    got = mine_from_runs(["r1"], runs_dir=tmp_path, bench_filter="mbpp+", instructions={"T/1": "t"})
    assert len(got) == 0


# --- retrieval --------------------------------------------------------------


def test_tokenize_drops_boilerplate():
    tokens = tokenize("Write a python function to reverse a string")
    assert "reverse" in tokens and "string" in tokens
    assert "python" not in tokens  # appears in every instruction
    assert "write" not in tokens


def test_retrieval_prefers_topically_similar():
    store = MemoryStore(
        [
            item("T/1", "Write a function to sort a list of integers ascending"),
            item("T/2", "Write a function to compute the factorial of a number"),
            item("T/3", "Write a function to sort a list of tuples by second element"),
        ]
    )
    got = Retriever(store).retrieve("Write a function to sort a list descending", k=2)
    assert {i.task_id for i in got} == {"T/1", "T/3"}


def test_retrieval_excludes_query_task_leakage_guard():
    """Retrieving a task's own solution is leakage, not memory."""
    store = MemoryStore(
        [
            item("T/1", "reverse a string quickly"),
            item("T/2", "reverse a string quickly"),
        ]
    )
    got = Retriever(store).retrieve("reverse a string quickly", k=5, exclude_task_ids={"T/1"})
    assert [i.task_id for i in got] == ["T/2"]


def test_retrieval_is_deterministic():
    store = MemoryStore([item(f"T/{i}", f"sort list variant {i}") for i in range(10)])
    r = Retriever(store)
    assert [i.task_id for i in r.retrieve("sort list", k=3)] == [
        i.task_id for i in r.retrieve("sort list", k=3)
    ]


def test_random_items_matched_count_but_unrelated():
    store = MemoryStore([item(f"T/{i}", f"task about topic {i}") for i in range(20)])
    r = Retriever(store)
    picked = r.random_items(k=3, exclude_task_ids={"T/0"}, seed=1)
    assert len(picked) == 3
    assert "T/0" not in {i.task_id for i in picked}
    # Deterministic given the seed, so the control arm is reproducible.
    assert [i.task_id for i in picked] == [
        i.task_id for i in r.random_items(k=3, exclude_task_ids={"T/0"}, seed=1)
    ]


def test_no_match_returns_empty_not_noise():
    store = MemoryStore([item("T/1", "quantum chromodynamics simulation")])
    assert Retriever(store).retrieve("sort a list", k=2) == []


# --- prompts ----------------------------------------------------------------


def test_no_exemplars_matches_baseline_prompt():
    msgs = build_memory_messages(TASK, [])
    assert msgs[-1].content == TASK.instruction


def test_exemplar_strips_response_format_boilerplate():
    """The format directive belongs to the real task, not to every exemplar."""
    inst = (
        "Write a function to sort a list.\n\n"
        "Respond with the complete Python solution in a single ```python code block."
    )
    rendered = item("T/1", inst, "def s(x): return sorted(x)").as_exemplar()
    assert "sort a list" in rendered
    assert "Respond with the complete" not in rendered


def test_exemplars_precede_task_and_task_is_last():
    ex = [item("T/1", "add two numbers", "def add(a,b): return a+b")]
    body = build_memory_messages(TASK, ex)[-1].content
    assert "add two numbers" in body
    assert "def add(a,b): return a+b" in body
    # The task the model must solve is the final thing it reads.
    assert body.rstrip().endswith(TASK.instruction.rstrip())


def test_random_and_retrieved_arms_share_structure():
    """Only relevance differs, so a difference cannot be a formatting artifact."""
    a = build_memory_messages(TASK, [item("T/1", "sort a list", "def s(): pass")])[-1].content
    b = build_memory_messages(TASK, [item("T/2", "parse json", "def p(): pass")])[-1].content
    for body in (a, b):
        assert body.startswith("Here are solved problems")
        assert "Now solve this problem:" in body
    assert abs(len(a) - len(b)) < 60


def test_conditions_declared():
    assert MEMORY_CONDITIONS == ("none", "random", "retrieved")
