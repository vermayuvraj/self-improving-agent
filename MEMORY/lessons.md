# Lessons learned

## 2026-07-22 — The control decides what the experiment can conclude

EXP-004's headline depends entirely on which baseline the treatment is
compared against. Against *no repair*, feedback looks like a +12.2 pp win at
1.5B and the write-up would have been "self-repair works." Against *blind
resampling at matched budget*, the same data show feedback **losing by 6.1
pp** while costing twice the tokens.

Nothing about the treatment changed. The control changed, and the conclusion
inverted.

**Rules:**
1. For any capability that adds context to a prompt, the control is not
   "without the capability" — it is "with an equally expensive but
   uninformative alternative." Otherwise the measurement captures the budget,
   not the idea.
2. When a result contradicts a pre-registered hypothesis, check the threats
   *before* believing it (here: 0% truncation ruled out the EXP-001 confound),
   then look for the mechanism. A mechanism that also explains an unexpected
   secondary pattern — anchoring cost falling with scale explained H3's
   shrinking gap — is much stronger evidence than the headline alone.
3. Mechanism analyses are often already sitting in traces you have.
   EXP-005 required no new inference, only reading what was recorded — which
   is the payoff of [[trace-first design]].

## 2026-07-22 — A control that cannot vary is not a control

The M3 repair loop initially inherited the project's greedy default
(temperature 0). Greedy decoding is deterministic, so every retry returned the
*byte-identical* solution — confirmed in the trace: three consecutive
`feedback` iterations produced the same 30-token answer character-for-character.
Varying the seed changed nothing, because seed has no effect at temperature 0.

The damage would have been subtle rather than loud. Every k-curve would have
been flat, `resample` would have measured nothing, and the experiment would
have reported "no benefit from repair" — a *plausible* result matching part of
the literature, with no error anywhere to notice. Caught only by reading actual
model outputs in a smoke run before launching the real sweep.

**Rules:**
1. Before running an ablation, verify each arm can actually produce a
   different outcome. A control whose output is fixed by construction measures
   nothing.
2. **Read raw model outputs from a smoke run before spending real compute.**
   Aggregate metrics looked fine; only the text revealed identical responses.
3. Defaults inherited from a different context (greedy is right for
   *measuring* a baseline, wrong for *resampling*) are a recurring hazard —
   same family as [[the matched-budget confound]] where a setting that was
   correct for one arm was wrong for another.

## 2026-07-21 — Capture *both* output streams from executed code

The EvalPlus harness prints its failing-input diagnostics to stdout and exits
non-zero with a bare `SystemExit` on stderr. Verdict events recorded only
`stderr_tail`, so 97% of real wrong-answers were bucketed as
`other_runtime_error` — and, far worse, the informative part of the failure
(failing input, expected vs actual) was **discarded before it reached the
trace**. M3's repair loop feeds exactly that text back to the model, so the
`feedback` condition would have been starved of its signal while still
*looking* like it ran correctly.

**Rule:** whenever the harness executes something, persist stdout and stderr
together. Test-runner conventions about which stream carries meaning vary,
and a trace is only as good as what it captured — you cannot recover a stream
you never wrote down. Same family as [[extraction-as-instrumentation]].

## 2026-07-21 — A "matched" budget that binds on one arm is a confound

EXP-001 gave both models `max_tokens=2048`, which looks like a fair control.
It was slack for qwen2.5-coder (median 88 completion tokens, 0 truncations)
and binding for qwen3 (median 1759, 42% truncated mid-reasoning). The raw
28-point pass@1 gap measured *budget fit*, not coding ability — conditional
on emitting code the ranking **reverses** (97.9% vs 85.4%).

**Rule:** before reporting any matched-budget comparison, verify the
constraint is slack for every arm. A binding constraint on one side is a
treatment, not a control. Generalises to every budget knob this platform
will use for ablations — tokens, iterations, wall-clock, tool calls.

**Corollary on latency:** measure from recorded per-call `llm_latency_ms`,
never wall-clock deltas. Wall clock implied 350 s/task for qwen3; summed
call latency showed 4.77 h of work inside a 15.2 h window — the laptop idled
overnight and the difference was pure artifact.

Both bugs are the same family as [[extraction-as-instrumentation]] and the
scored-artifact lesson below: **the measurement apparatus produces confident
wrong numbers far more readily than obvious failures.**

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
