# Lessons learned

## 2026-07-20 — A broken run must never produce a scored artifact

The EXP-001 chain was scheduled to run `qwen3:8b` while that model was still
downloading. The runner treats an LLM error as per-task and non-fatal (correct
for transient API failures), so a missing model would have recorded 664
errors and still written a manifest with `pass@1 = 0.0` and
`outcome = completed` — indistinguishable from a real result, and the
dashboard exporter would have published it. Fixed with a preflight
`check_available()` that aborts before any artifact is created.

**Rule:** distinguish *per-task* failures (record and continue — they are
data) from *configuration* failures (abort before writing anything — they are
not results). Any code path that can emit a scored artifact needs to be
audited for which kind it is handling. Related: the same instinct as
[[extraction-as-instrumentation]] — the measurement apparatus can fabricate
results as easily as it can lose them.

## 2026-07-20 — Code extraction must preserve indentation

`extract_code` used `.strip()` on extracted blocks, which deletes the leading
indent of completion-style outputs (`    return a + b`) and produces invalid
Python when appended to a HumanEval prompt. Caught by a unit test before any
benchmark ran. General rule: **any transformation between model output and
executed program is part of the measured system** — bugs there silently
deflate benchmark scores and would have looked like "the model is weak."
Treat extraction/assembly code as measurement instrumentation: test it with
canonical solutions (our network self-check runs official solutions through
the full assembly+sandbox path).
