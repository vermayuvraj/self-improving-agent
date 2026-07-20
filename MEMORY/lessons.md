# Lessons learned

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
