import json

from sia.trace import TraceWriter, read_jsonl, read_trace


def test_read_jsonl_survives_exotic_unicode_line_separators(tmp_path):
    """Model output can contain U+2028/U+2029/U+0085, which json.dumps does not
    escape but str.splitlines() splits on — shattering a valid record. The
    canonical reader must not do that. (Regression: DeepSeek-1.3B emitted
    U+2028 in sampled code, corrupting the anchoring measure until fixed.)"""
    path = tmp_path / "trace.jsonl"
    nasty = "def f():     return 1   #  trailing"
    with TraceWriter(path, run_id="r") as tw:
        tw.event("llm_response", task_id="T/1", content=nasty)
        tw.event("verdict", task_id="T/1", passed=True)

    # The failure mode: splitlines() over-splits and json.loads fails.
    raw = path.read_text(encoding="utf-8")
    assert " " in raw  # the writer stored it literally, unescaped
    assert len(raw.splitlines()) > 2  # splitlines() sees phantom extra lines

    # The fix: read_jsonl splits on \n only, so every record round-trips.
    events = read_jsonl(path)
    assert len(events) == 2
    assert events[0]["data"]["content"] == nasty
    assert events[1]["data"]["passed"] is True


def test_read_trace_is_alias_for_read_jsonl():
    assert read_trace is read_jsonl


def test_read_jsonl_skips_blank_lines(tmp_path):
    path = tmp_path / "t.jsonl"
    path.write_text(
        json.dumps({"a": 1}) + "\n\n" + json.dumps({"a": 2}) + "\n", encoding="utf-8"
    )
    assert [r["a"] for r in read_jsonl(path)] == [1, 2]
