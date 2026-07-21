# Experiments

## Protocol

Every experiment gets an ID (`EXP-NNN`), a directory `experiments/EXP-NNN/`
(config, results, analysis), and a registry row below. An experiment is not
"done" until its failure analysis is written. Negative results are recorded
with the same rigor as positive ones — they are paper material.

Required fields per experiment:

- **Hypothesis** — falsifiable statement, tied to an RQ where applicable
- **Method** — agent config, capability toggles, budget caps
- **Configuration** — exact config file (hash) + model ID + seed(s)
- **Dataset** — benchmark + split + task IDs if subset
- **Metrics** — pass@1, cost (USD), tokens, latency, iterations, repair rate
- **Results** — table + pointer to raw traces
- **Failure analysis** — taxonomy counts + ≥3 hand-inspected failure traces
- **Future work** — what this result changes about the plan

Budget-matching rule (ADR-0005): capability comparisons run at equal
token/cost ceilings. Report both "at matched budget" and "at natural
completion" numbers when they differ.

Sample-size note: HumanEval (164) and MBPP-test (500) are small; report 95%
CIs (Wilson) on pass rates and run ≥3 seeds for any headline comparison where
the model is nondeterministic.

## Registry

| ID | Date | RQ | Hypothesis (short) | Benchmark | Result | Status |
|----|------|----|--------------------|-----------|--------|--------|
| EXP-001 | 2026-07-20 | — | code-specialized 7B ≥ general 8B on code benchmarks | HumanEval + MBPP | Supported at matched budget (85.4% vs 57.3%), but **reversed** conditional on emitting code (85.4% vs 97.9%) — budget was binding for one arm only | ✅ closed |
| EXP-002 | planned | RQ8 | test-time reasoning pays for itself per unit latency | HumanEval + MBPP | — | planned |
| EXP-003 | 2026-07-21 | — | EvalPlus baseline + harness validation | HumanEval+/MBPP+ | 80.5% / 70.9%, within 0.8–3.6 pts of published; MBPP+ has usable headroom, HumanEval+ does not | ✅ closed |
| EXP-003b | 2026-07-22 | — | smaller models give the headroom and a scale axis | HumanEval+/MBPP+ | 54.3→80.5% HumanEval+, 56.6→70.9% MBPP+; MBPP+ powered at every scale (110–164 failures), HumanEval+ at none | ✅ closed |

## EXP-003 — EvalPlus baseline + harness validation (2026-07-21)

**Purpose.** Establish the ablation substrate for M3 and check our harness
against published numbers. Not a hypothesis test.

**Results** (`qwen2.5-coder:7b`, greedy, seed 7), with the Qwen2.5-Coder
technical report (arXiv:2409.12186, Table 16) as the external reference:

| Benchmark | Ours | Published | Δ | Tasks | **Failures** |
|---|---|---|---|---|---|
| HumanEval | 0.854 | 0.884 | −3.0 | 164 | 24 |
| HumanEval+ | 0.805 | 0.841 | −3.6 | 164 | 32 |
| MBPP | 0.748 | 0.835 | −8.7 | 500 | 126 |
| **MBPP+** | **0.709** | **0.717** | **−0.8** | 378 | **110** |

**Harness validity.** Three of four land within ~3.6 points of published, and
MBPP+ within 0.8 — strong evidence the EvalPlus differential-testing
implementation (oracle, contract stripping, float tolerance) is correct. The
residual ~3-point deficit is expected and explained: we run Q4_K_M quantised
weights, zero-shot, with our own prompt. The MBPP outlier (−8.7) is a
protocol difference, not a harness bug — the report uses a different MBPP
setup; our MBPP+ figure, which is the one M3 will use, agrees closely.

**Headroom (the reason for this experiment).** EvalPlus does *not* deliver
the 10–20 point drop the literature reports for older models — Qwen2.5-Coder
is simply robust to the harder tests (−4.9 on HumanEval, −3.9 on MBPP).
Consequence for the M2 exit criterion (≥100 failing tasks per benchmark):

- **MBPP+ passes** — 110 failures.
- **HumanEval+ fails** — 32 failures. Underpowered for detecting the effect
  sizes M3 cares about; it stays as a secondary benchmark, not a primary one.

**Consequence — model scale becomes an experimental dimension.** Rather than
hunt for a harder benchmark, add smaller models from the same family, whose
published scores give ample headroom (1.5B: 66.5 HumanEval+ / 59.4 MBPP+;
3B: 80.5 / 62.4). This is strictly better than a benchmark swap because it
**converts the headroom problem into the paper's central axis**: the two
papers bracketing RQ1 differ in model scale (0.5–1.5B vs frontier), so
measuring repair benefit across 1.5B → 3B → 7B *is* the contribution.
Baselines for 1.5B/3B are being collected as EXP-003b.

**Bug found and fixed.** The initial taxonomy put 97% of EvalPlus failures in
`other_runtime_error`: the harness writes its failing-input diagnostics to
**stdout**, but verdict events only captured stderr. Runs now record
`stdout_tail` too, and classification reads both streams. This is load-bearing
for M3 — that stdout diagnostic (failing input, expected vs actual) *is* the
feedback the repair loop hands back to the model, so without the fix the
`feedback` condition would have been silently starved of its signal.

## EXP-003b — Model-scale baselines (2026-07-22)

**Purpose.** Supply the statistical power EvalPlus alone did not (EXP-003),
and establish the scale axis M3's design now rests on.

| Model | HumanEval+ | failures | MBPP+ | failures |
|---|---|---|---|---|
| qwen2.5-coder:1.5b-instruct | 0.543 [0.466, 0.617] | 75 | 0.566 [0.516, 0.615] | **164** |
| qwen2.5-coder:3b-instruct | 0.738 [0.666, 0.799] | 43 | 0.598 [0.548, 0.646] | **152** |
| qwen2.5-coder:7b | 0.805 [0.738, 0.858] | 32 | 0.709 [0.661, 0.753] | **110** |

Monotonic in scale on both benchmarks, as expected. Full table with paired
statistics: `experiments/EXP-003b/report.md`.

**Exit criterion (≥100 failing tasks per cell): met on MBPP+ at every scale
(110–164), not met on HumanEval+ at any scale (32–75).** Decision:
**MBPP+ is M3's primary benchmark; HumanEval+ is secondary** and reported for
comparability with the literature, not relied on for significance. Pooling the
two is rejected — different task distributions and difficulty, so a pooled
rate would be a weighted average of two different things.

**Validation against the Qwen2.5-Coder report (Table 16).** MBPP+ agrees
closely at every scale (−0.8, −2.6, −2.8); HumanEval+ agreement degrades as
the model shrinks (−3.6, −6.7, −12.2). That pattern is consistent with Q4_K_M
quantisation costing small models more than large ones — a documented effect,
and one that argues for treating our absolute HumanEval+ numbers for the 1.5B
model as a lower bound rather than a published-score reproduction. It does not
threaten the ablations, which are *within-model* paired comparisons where
quantisation is held constant.

**Note on adoption.** These runs predate the grid launcher. They were adopted
into `cells.json` only after verifying each run's recorded config matches what
the spec would have produced; a 12-task smoke run was correctly rejected by
that check. Results are never attributed to a configuration that did not run.

## EXP-001 — Default model selection (pre-registered before run)

**Hypothesis.** The code-specialized `qwen2.5-coder:7b` matches or beats the
newer general-purpose `qwen3:8b` on function-level code generation, at lower
latency (smaller model, no thinking tokens).

**Method.** Single-shot agent (one call per task), greedy decoding
(temperature 0.0, seed 7), max_tokens 2048, exec timeout 10 s. Full
HumanEval (164) and MBPP test split (500) per model. Smoke run
(`--limit 10`) first to validate the pipeline; smoke results are discarded,
not pooled.

**Decision rule (fixed in advance).** Default model = higher mean pass@1
averaged over the two benchmarks. If the difference is within overlapping
95% Wilson CIs on both benchmarks, prefer the model with lower median
per-task latency. Loser stays available for RQ8 transfer checks.

**Metrics.** pass@1 per benchmark (95% CI), tokens in/out, per-task LLM
latency, wall time, extraction-fallback rate (from traces).

**Threats.** (a) Greedy decoding may under-represent qwen3 if it relies on
sampling diversity — accepted: our platform default is deterministic runs.
(b) 6 GB VRAM may force partial CPU offload for the 8B model, inflating its
latency — we record `ollama ps` VRAM split alongside results. (c) Known
contamination risk on HumanEval/MBPP for both models — scores are used for
relative comparison, not as absolute capability claims.

**Status.** ✅ Closed 2026-07-21. Arm 1 complete (both benchmarks); arm 2
HumanEval complete, MBPP dropped (deviation below). Smoke run `c120ff7c58cc`
validated the pipeline (10/10, discarded per protocol).

### Decision: `qwen2.5-coder:7b` is the project default

**On the pre-registered metric it is not close.** At the matched 2048-token
budget qwen2.5-coder scores 85.4% on HumanEval against qwen3's 57.3%, with
non-overlapping 95% CIs ([79.1, 90.0] vs [49.7, 64.6]). It is also **25×
faster** (median 4.5 s vs 113.3 s per task).

**But that headline number is not a capability comparison, and must not be
cited as one.** 68 of qwen3's 70 failures (97%) never emitted code at all —
they exhausted the token budget mid-reasoning. Conditional on producing a
code block, **qwen3 passes 97.9% versus qwen2.5-coder's 85.4%**. qwen3 is the
*more capable* model; it is disqualified here on budget efficiency and
throughput, not on ability. See "Confound" below.

| Metric (HumanEval, n=164) | qwen2.5-coder:7b | qwen3:8b |
|---|---|---|
| pass@1 @ 2048-token budget | **0.854** [0.791, 0.900] | 0.573 [0.497, 0.646] |
| pass rate given code emitted | 0.854 | **0.979** |
| budget-exhausted responses | 0 (0%) | 69 (42.1%) |
| median LLM latency | **4.5 s** | 113.3 s |
| median completion tokens | 88 | 1759 |
| CPU/GPU split (6 GB card) | 18% / 82% | 30% / 70% |

Rationale for the platform default: an experiment engine whose thesis is
dense matched-budget ablations cannot afford a 25× latency tax per cell, and
a model that needs >2048 tokens to answer a HumanEval prompt makes
"matched token budget" comparisons awkward for every downstream module.
qwen3's higher underlying capability is recorded as a live finding, not
dismissed — it is the natural candidate for final high-stakes evaluation
runs and for RQ8 transfer checks.

### Confound discovered: the token budget was binding for only one arm

`max_tokens=2048` was pre-registered as a *matched* budget. It is not
matched in effect: non-binding for a terse model (median 88 completion
tokens, 0 truncations) and severely binding for a reasoning model (median
1759, 42.1% truncated). The raw pass@1 gap therefore measures
*budget fit*, not coding ability, and reporting it unqualified would have
been a false capability claim.

Caught by adding `budget_exhausted` as a first-class failure class in
`scripts/analyze_failures.py`, which now also reports a conditional pass
rate. **Generalised rule for this platform:** any budget parameter that
binds on one arm and not another is a confound, not a control. Future
matched-budget comparisons must verify the constraint is slack for every arm
before the comparison is valid.

A second measurement error was caught alongside it: wall-clock elapsed time
implied 350 s/task for qwen3, but summed per-call latency accounts for only
4.77 h of a 15.2 h window — the machine was idle overnight. **Latency is
reported from recorded `llm_latency_ms`, never from wall-clock deltas.**

### Results — arm 1: qwen2.5-coder:7b (2026-07-20)

| Benchmark | Tasks | pass@1 | 95% CI (Wilson) | Wall | s/task | LLM errors | Run |
|---|---|---|---|---|---|---|---|
| HumanEval | 164 | **0.854** | [0.791, 0.900] | 878 s | 5.4 | 0 | `090a8adcdc48` |
| MBPP (test) | 500 | **0.748** | [0.708, 0.784] | 1543 s | 3.1 | 0 | `b2e16d243112` |

Tokens: 34.3k in / 16.4k out (HumanEval), 91.9k in / 29.4k out (MBPP).
VRAM split throughout: **18% CPU / 82% GPU**, 4096-token context — the model
does not fit entirely in 6 GB, so a slice is CPU-offloaded (see Threats (b);
this is the measured cause of GPU utilisation sitting near 50% rather than
saturating).

Both figures sit in the range published for this model, which is the
harness's external sanity check: our assembly + sandbox path is not
silently deflating scores.

### Failure analysis — arm 1

Classified with `scripts/analyze_failures.py` (M2 taxonomy prototype):

| Class | HumanEval (24 fails) | MBPP (126 fails) |
|---|---|---|
| wrong_answer (assertion) | 22 (92%) | 118 (94%) |
| type_error | 1 | 3 |
| lookup_error | 1 | 1 |
| name_error | — | 2 |
| timeout | — | 2 |
| **syntax_error** | **0** | **0** |

**Finding (harness validity).** Zero syntax or indentation errors across 664
generated programs. The extraction → assembly → execution path is not a
source of measurement error, which is exactly the failure mode the
[MEMORY/lessons.md] indentation bug would have caused. Zero LLM errors, zero
malformed responses.

**Finding (motivates M3).** ~93% of failures are *semantic*: the program runs
and returns a wrong value. Three hand-inspected cases (`HumanEval/10`
`make_palindrome`, `HumanEval/26` `remove_duplicates`, `mbpp/14`
`find_Volume`) all produce clean `AssertionError` tracebacks naming the
failing input and the expected output. This is the ideal regime for the M3
repair loop — the execution feedback is informative and localised, not a
stack trace about broken syntax. It also sharpens **RQ1**: if repair helps
anywhere, it should help here, so a *null* result on this distribution would
be a strong negative finding rather than a setup artifact.

### Protocol deviation — qwen3:8b MBPP arm dropped (2026-07-20)

Measured after 12 HumanEval tasks, qwen3:8b runs at **96.4 s/task vs
qwen2.5-coder:7b's 5.4 s/task — an 18× gap**. Two compounding causes, both
measured rather than inferred:

- **Thinking tokens:** 1392 mean completion tokens/task vs 100 (14×). qwen3
  emits a reasoning trace before answering.
- **VRAM ceiling:** qwen3 loads at 30% CPU / 70% GPU vs 18%/82% (6.0 GB vs
  5.1 GB resident against a 6 GB card), so a larger share runs on CPU. This
  is pre-registered Threat (b), now confirmed with numbers.

Completing both arms as specified would take **~17.5 h** (4 h HumanEval +
13.5 h MBPP). **Decision: run the HumanEval arm to completion, drop the
qwen3 MBPP arm.** Rationale: HumanEval alone gives a full head-to-head on
matched tasks, which is what the accuracy comparison needs; a second
benchmark at 13.5 h buys precision we do not need to pick a *development*
default, and would monopolise the only GPU for a day.

This is a deviation from the pre-registration and is recorded as such rather
than quietly rewriting the plan. It affects the decision rule: with only one
benchmark for arm 2, "higher mean pass@1 across both benchmarks" cannot be
evaluated as written. **Amended rule (fixed now, before the HumanEval arm
finishes):** if the two models' HumanEval CIs overlap, the 18× latency gap
decides it for qwen2.5-coder. If qwen3 wins HumanEval with
*non-overlapping* CIs, that is a genuine accuracy/throughput trade-off — the
coder model still becomes the default for ablation grids (an 18× tax on
every future experiment is disqualifying for a platform whose thesis is
dense, matched-budget ablations on one workstation), and qwen3 gets recorded
as a candidate for final high-stakes evaluation runs, to be settled by its
own experiment.

**Spun off as EXP-002 (not yet run):** qwen3:8b at a *slack* token budget
(≥4096, verified 0% truncation) vs qwen2.5-coder:7b — the comparison
EXP-001 could not make. Sharper now that the 97.9% conditional pass rate is
known: the question is not "is qwen3 better" (evidence says yes) but
"does test-time reasoning pay for itself per unit latency?" At 25× the cost
for ~12 points of conditional accuracy, the answer is likely no for
iteration work and yes for final evaluation — worth measuring rather than
assuming.

**Future work.** (a) The 18%/82% CPU/GPU spill is the latency bottleneck;
test whether flash attention + quantised KV cache fits the model entirely in
6 GB, as a controlled infrastructure experiment *after* EXP-001 closes (never
mid-comparison). (b) MBPP's 2 timeouts warrant checking whether 10 s is
generous enough for legitimately slow-but-correct solutions.
