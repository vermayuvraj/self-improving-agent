import pytest

from sia.trace import RunManifest, TraceWriter, config_hash, read_trace


def test_events_roundtrip(tmp_path):
    path = tmp_path / "trace.jsonl"
    with TraceWriter(path, run_id="abc") as tw:
        tw.event("task_start", task_id="HumanEval/0")
        tw.event("llm_call", messages=[{"role": "user", "content": "hi"}])
        tw.event("verdict", task_id="HumanEval/0", passed=True)

    events = read_trace(path)
    assert [e["seq"] for e in events] == [0, 1, 2]
    assert all(e["run_id"] == "abc" for e in events)
    assert all(e["ts"] for e in events)
    assert events[2]["data"] == {"task_id": "HumanEval/0", "passed": True}


def test_unknown_event_type_rejected(tmp_path):
    with TraceWriter(tmp_path / "t.jsonl", run_id="x") as tw, pytest.raises(ValueError):
        tw.event("banana")


def test_config_hash_key_order_independent():
    assert config_hash({"a": 1, "b": [2, 3]}) == config_hash({"b": [2, 3], "a": 1})
    assert config_hash({"a": 1}) != config_hash({"a": 2})


def test_manifest_roundtrip(tmp_path):
    m = RunManifest(run_id="r1", config={"model": "m", "temp": 0.0}, model="m", seed=7)
    m.totals = {"llm_calls": 3, "prompt_tokens": 100}
    m.outcome = "completed"
    path = tmp_path / "manifest.json"
    m.save(path)

    loaded = RunManifest.load(path)
    assert loaded == m
    assert loaded.config_hash == config_hash({"model": "m", "temp": 0.0})
