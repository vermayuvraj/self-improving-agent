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
| EXP-006 | 2026-07-22 | RQ4 | other-task experience helps, and relevance matters | MBPP+ | **Clean null.** All 9 contrasts n.s. after Holm; bounded to ±3.5 pp. Isolates EXP-004's harm as specific to *self*-conditioning. | ✅ closed |
| EXP-008 | 2026-07-24 | RQ8 | anchoring penalty vanishes at frontier scale | MBPP+ | **Partial.** Baseline done: Llama-3.3-70B = 0.704, ties the 7B *specialist* (scale ≠ capability here). Repair arms blocked by hard free-tier daily-token caps (Groq 100k TPD, OpenRouter throttle). Needs paid tier or documented as future work. | ⚠ partial |
| EXP-007 | 2026-07-22 | RQ5 | verbal reflection breaks the anchor | MBPP+ | **Partially — and still loses.** Anchoring drops most of any own-output arm (−0.11/−0.04/−0.12 similarity vs feedback), and ranking tracks it exactly; but reflect still loses to resample at 1.5B (−6.1 pp, p=0.006) and ties at 7B for 2.5× the tokens. | ✅ closed |
| EXP-005 | 2026-07-22 | RQ1 | anchoring is the mechanism: feedback arms show lower inter-attempt diversity | MBPP+ | **Confirmed.** Inter-attempt similarity +0.30–0.38 vs resample at every scale; 33–68% of retries near-identical when shown own code vs 2–14% blind. | ✅ closed |
| EXP-003 | 2026-07-21 | — | EvalPlus baseline + harness validation | HumanEval+/MBPP+ | 80.5% / 70.9%, within 0.8–3.6 pts of published; MBPP+ has usable headroom, HumanEval+ does not | ✅ closed |
| EXP-004 | 2026-07-22 | RQ1 | execution-feedback content beats blind resampling at matched budget; effect shrinks with scale | MBPP+ (primary) | **Refuted, sign reversed.** Blind resampling wins at every scale (−6.1/−4.2/−1.1 pp vs feedback) using ~half the tokens; feedback−placebo ≈ 0 everywhere. Knee at k≈2 (46–53% of gain). | ✅ closed |
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

## EXP-009 — Is the anchoring penalty a quantization artifact? (pre-registered 2026-07-24)

**Motivation (external review).** Every result to date uses $Q4\_K\_M$
weights. Quantization is documented to degrade *in-context learning* more than
unconditional generation, and the conditions we find wanting (`placebo`,
`feedback`) are exactly those that place extra material in context. So the
penalty could in principle be precision loss rather than anchoring. This is
the strongest objection raised against the paper and it is directly testable.

**Design.** Exact replication of the EXP-004 decomposition at the scale where
the effect is largest, with the *only* change being precision:
`qwen2.5-coder:1.5b-instruct-fp16` (~3.1 GB, fits 6 GB VRAM fully, so no CPU
spill) versus the existing $Q4$ 1.5B arms. MBPP+, k≤8, temperature 0.8 on
retries, seed 7 — identical harness, identical prompts. Conditions:
`resample`, `placebo`, `feedback` (reflect omitted; it is secondary and the
objection concerns feedback).

**Hypotheses, fixed before running.**
- **H1 (the load-bearing one).** The penalty survives at FP16:
  `feedback − resample` remains significantly negative at 1.5B. If so,
  quantization is excluded as the cause.
- **H2.** `feedback − placebo` remains null at FP16, i.e. execution-feedback
  content still adds nothing.
- **H3 (mechanism).** Inter-attempt similarity remains far higher for
  own-output conditions than for `resample` (the $\approx{+}0.3$ gap). This
  measure has no obvious precision dependence, so a large change here would
  itself be informative.

**Falsification.** If `feedback − resample` is null or positive at FP16 while
being $-6.1$ pp at $Q4$, the headline result is a quantization artifact and
the paper's central claim must be restricted to quantized deployment. That
would be a major revision, and we would report it.

**Status.** Pre-registered; launching 2026-07-24.

## EXP-010 — Does anchoring generalize beyond the Qwen family? (pre-registered 2026-07-24)

**Motivation (external review).** All models are Qwen2.5-Coder, so the effect
may reflect one pre-training distribution rather than small code models
generally.

**Design.** Replicate the decomposition on an independent family at the scale
where our effect is strongest: **`deepseek-coder:1.3b-instruct`** (different
lab, different pre-training corpus, different tokenizer) against
`qwen2.5-coder:1.5b-instruct`. MBPP+, k≤8, same harness, seed 7. Conditions:
`resample`, `placebo`, `feedback`. We deliberately replicate at ~1.3--1.5B
rather than 7B because that is where the Qwen penalty is largest ($-6.1$ pp)
and therefore where a family-specific artifact would be most visible; a null
at 7B would be uninformative since the Qwen penalty is already null there.

**Hypotheses.**
- **H1.** `feedback − resample` is significantly negative for DeepSeek too,
  i.e. the penalty is not Qwen-specific.
- **H2.** Inter-attempt similarity for own-output conditions exceeds
  `resample` by a comparable margin.
- **H3.** A materially *lower* baseline for DeepSeek is expected and is not a
  confound: contrasts are within-model and paired.

**Falsification.** If DeepSeek shows no penalty, the claim narrows to the Qwen
family and the paper must say so in the title and abstract.

**Threats (both experiments).** (a) FP16 at 1.5B changes memory layout and may
change throughput; latency is reported but is not the outcome. (b) DeepSeek's
instruction format differs; we keep our prompt identical rather than tuning
per model, which is conservative — a tuned prompt could only help the
own-output arms we expect to lose. (c) Both are single-seed like the rest of
the study.

**Status.** Pre-registered; launching 2026-07-24.

## EXP-008 — Does the anchoring penalty vanish at frontier scale? (pre-registered 2026-07-23)

**RQ8 / the reviewer's first question.** EXP-004 found the
`feedback − resample` gap shrinks monotonically with scale (−6.1 → −4.2 →
−1.1 pp for 1.5B → 3B → 7B). The mechanism (EXP-005) attributes this to
anchoring becoming *cheaper* as a model's first attempt gets better, not to
feedback becoming useful. Both accounts predict the same thing at frontier
scale, which is the clean test: **does self-repair reach parity with — or
finally beat — blind resampling once the model is strong enough?**

**Design.** Identical harness to EXP-004, one added scale point via a
free OpenAI-compatible endpoint (OpenRouter `:free` / Gemini / Groq — the
client is provider-agnostic). MBPP+, k≤8, temperature 0.8 on retries.
Conditions: `resample`, `feedback`, `reflect` (placebo dropped to conserve
rate-limited budget; `resample` vs `feedback` is the load-bearing contrast,
and `reflect` tests whether reasoning that failed to pay below 7B pays here).

**Hypotheses, fixed before running.**
- **H1.** `feedback − resample` at k=8 is **not significantly negative** at
  frontier scale (the penalty has vanished). Predicted by the scale trend.
- **H2 (mechanism).** Inter-attempt similarity for `feedback` sits closer to
  `resample` than it does at 7B — i.e. a stronger model anchors on a *better*
  attempt, so the same anchoring strength costs less.
- **H3.** If instead `feedback` significantly *beats* `resample`, the
  small-model story does not extrapolate and the anchoring account needs a
  scale boundary — a genuine finding either way.

**Analysis.** Same paired McNemar + bootstrap CI; this arm slots into
`scripts/analyze_exp004.py` and `make_figures.py` as a fourth model column.

**Threats.** (a) A different model *family* confounds scale with
architecture; prefer a `:free` Qwen3-Coder so it extends our own ladder.
(b) Free-tier rate limits force low concurrency and long wall-time; the
client retries 429s with backoff, and the run is resumable, so this costs
time not validity. (c) Some free endpoints are quantized or throttled
differently than a first-party API; recorded, not corrected.

**Status (2026-07-24).** Pipeline built and validated end-to-end. Model
chosen: **`google/gemma-4-31b-it:free`** — the only *non-reasoning* option in
the current OpenRouter free lineup (Nemotron-550B and gpt-oss-20b both emit
hidden reasoning tokens, which would re-introduce the EXP-001 truncation
confound and conflate scale with test-time reasoning). This makes EXP-008 a
**larger-scale, different-family** point (31B instruct, ~4.4$\times$ the 7B
top of our ladder), not a true frontier jump; reported as such.

### Partial result: baseline complete, repair arms blocked by free-tier daily caps

**Baseline (Llama-3.3-70B, MBPP+, greedy).** pass@1 = **0.704**
[0.66, 0.75], n=378. Caveat: 6 tasks errored on rate limits and are counted
as failures, so the true rate is 0.704–0.720. Used ~90k tokens.

**Finding from the baseline alone (worth keeping):** a **70B generalist ties
a 7B code specialist** on first-attempt MBPP+ quality (0.704 vs Qwen2.5-Coder
-7B's 0.709). Raw scale without code-specialization does *not* improve
first-attempt quality here — which reinforces the paper's "capability, not
size" framing of the anchoring cost. It also means this arm, even if
completed, would test scale-with-similar-capability, not
scale-with-higher-capability.

**Why the repair arms did not run: two hard free-tier walls, both measured.**
- **OpenRouter free**: dynamic throttling — ~1/6 calls HTTP 429 on a light
  burst, rising to ~2/3 under sustained load. Effective ~3 min/task; a
  rigorous sweep would take over a day.
- **Groq free**: a hard **100{,}000 tokens/day** cap on
  `llama-3.3-70b-versatile` (confirmed from the 429 body:
  `TPD Limit 100000, Used 99998`). The baseline alone consumed ~90k, so a
  single repair arm (~300k+ tokens) cannot fit one daily budget; the full
  three-arm sweep would need weeks of daily resets.

A backoff-cap bug was found and fixed along the way (`max_backoff_s`; uncapped
$4\text{s}\times2^{7}\approx512$s per call turned throttling into
multi-minute stalls; now capped at 30s, with a regression test).

**Conclusion.** A rigorous frontier repair contrast is not achievable on
current free tiers within a reasonable timeframe — the daily *token* caps,
not throughput, are the binding constraint. The pipeline, model choice, and
analysis are all validated and staged; the arm needs either a small paid tier
(a few dollars finishes it in ~1 hour) or is left as documented future work,
which the paper's design already accommodates. The clean baseline datapoint
is retained.

## EXP-007 — Does verbal reflection overcome anchoring? (pre-registered 2026-07-22)

**RQ5.** Does structured self-reflection beat simply re-prompting with the
failure log — and can it beat blind resampling?

**Why the answer is partly predictable.** Reflection is own-output
conditioning: the prompt contains the failed code, so EXP-005's anchoring
mechanism applies. The open part is whether an explicit verbal diagnosis
*breaks* the anchor — reasoning about *why* the approach failed could license
abandoning it, which is exactly what the anchored arms fail to do.

**Design.** One additional arm on the existing M3 harness: `reflect` =
`feedback` + "first diagnose the failure in two or three sentences, then
write a corrected version." Everything before the trailing instruction is
byte-identical to `feedback`, so the contrast isolates the reasoning step.
3 models × MBPP+ × k≤8, same baselines, same seeds, temperature 0.8.

**Hypotheses.**
- **H1.** `reflect` > `feedback` — the verbal step adds something.
- **H2 (the real question).** `reflect` > `resample`. EXP-004 predicts *no*:
  anchoring should dominate. If reflection *does* beat resampling, verbal
  reasoning breaks the anchor and the M3 conclusion needs qualifying.

**Predicted secondary effect.** `reflect` relaxes "no explanations", so
responses are longer and truncation risk rises. Monitored per arm; the
anchoring measure (inter-attempt similarity) is also computed, since the
mechanism predicts `reflect` should anchor *less* than `feedback` if it works
at all.

**Status.** ✅ Closed 2026-07-22.

### Result: reflection partially breaks the anchor — and still loses

pass@1 at k=8 on MBPP+, with the other conditions for context:

| Model | resample | placebo | feedback | **reflect** |
|---|---|---|---|---|
| 1.5B | **0.749** (63k tok) | 0.688 (90k) | 0.688 (129k) | 0.688 (**345k**) |
| 3B | **0.778** (76k) | 0.709 (89k) | 0.735 (84k) | 0.743 (**284k**) |
| 7B | 0.820 (49k) | 0.802 (59k) | 0.810 (55k) | **0.828** (**122k**) |

Holm-corrected paired contrasts (now over five contrasts per model):

| Contrast | 1.5B | 3B | 7B |
|---|---|---|---|
| reflect − feedback | +0.000 (p=1.00) | +0.008 (p=1.00) | +0.019 (p=1.00) |
| reflect − resample | **−0.061 (p=0.006)** | −0.034 (p=0.60) | +0.008 (p=1.00) |

- **H1 (reflect > feedback): not supported statistically.** The direction is
  consistently positive (+0.000/+0.008/+0.019) and monotone in scale, but no
  contrast survives correction.
- **H2 (reflect > resample): refuted.** Reflection loses significantly to
  blind resampling at 1.5B, loses non-significantly at 3B, and ties at 7B —
  while costing **2.5–5.5× the output tokens**.

### The mechanism prediction held: reflection anchors less

Pre-registered: *"reflect should anchor less than feedback if it works at
all."* Inter-attempt similarity (lower = more exploration):

| Model | resample | feedback | **reflect** | reflect − feedback |
|---|---|---|---|---|
| 1.5B | 0.509 (5.2% near-identical) | 0.862 (52.1%) | 0.751 (34.8%) | **−0.111** |
| 3B | 0.418 (1.8%) | 0.795 (37.9%) | 0.754 (28.4%) | −0.041 |
| 7B | 0.607 (13.7%) | 0.914 (65.8%) | 0.793 (39.1%) | **−0.121** |

**Reflection is the only own-output condition that meaningfully loosens the
anchor** — near-identical regeneration falls by roughly a third (52%→35%,
66%→39%). Verbal diagnosis does license abandoning a wrong approach, as
hypothesised.

But it loosens the anchor without escaping it: reflect still sits 0.19–0.34
above blind resampling in similarity, and its ranking among the own-output
conditions tracks that residual almost exactly — **reflect anchors least and
performs best of the three, feedback anchors most and performs worst**. The
mechanism predicts the outcome ordering quantitatively, which is stronger
evidence for anchoring than the headline contrast alone.

### The cost verdict is decisive even where accuracy ties

At 7B, reflection's +0.8 pp over resampling is not significant and costs
**2.5× the output tokens** (122k vs 49k). At 1.5B it is 5.5× the tokens for a
significant *loss*. On a cost-adjusted basis reflection is dominated at every
scale — there is no regime in this study where it is the right choice.

**Threat check.** Reflection relaxes "no explanations", so responses are much
longer; truncation was monitored and remained at 0% across all arms, so the
result is not budget-limited. The extra tokens are spent on prose the model
produces *before* the code, which is the intended cost of the condition.

### Consequence for RQ5

The pre-registered framing asked whether reflection beats *re-prompting with
the failure log*. It does not, statistically. The more useful answer is the
one the control set makes visible: **reflection is a partial and expensive
mitigation of a problem best solved by not conditioning on your own output at
all.**

## EXP-006 — Does *other-task* experience escape the anchoring trap? (pre-registered 2026-07-22)

**RQ4.** Does cross-task experience memory improve success, and is any gain
from the *relevance* of what is retrieved or merely from having worked
examples in context?

**Why this follows from EXP-004/005.** Own-attempt context *costs* accuracy
via anchoring. Retrieved experience is also context — but from other,
*solved* tasks, so it carries no failed attempt to anchor on. This is the
sharpest remaining question in the project: is the anchoring penalty specific
to self-conditioning, or does any added context hurt at these scales?

**Design.** Each model retrieves from **its own** solved MBPP+ tasks (mined
from its EXP-003b baseline trace) — experience memory in the self-improvement
sense, not cross-model distillation. Leave-one-out: a task never retrieves
itself. k=2 exemplars, BM25 lexical retrieval, greedy decoding to match the
existing baseline exactly (so the `none` arm is the EXP-003b run, free).

| Condition | Prompt | Isolates |
|---|---|---|
| `none` | task only | baseline (reuses EXP-003b) |
| `random` | + 2 arbitrary solved tasks | value of *any* worked examples |
| `retrieved` | + 2 most similar solved tasks | value of *relevance* |

`none → random` is the few-shot effect; `random → retrieved` is the retrieval
effect. Both memory arms share format, exemplar count, and comparable length,
so a difference between them cannot be a prompt-length artifact.

**Hypotheses, fixed before running.**
- **H1 (retrieval).** `retrieved` > `random` — relevance matters. The
  few-shot literature reports this consistently (e.g. TF-IDF retrieval
  +6–9 F1 in comparable settings), so a null here would be the surprise.
- **H2 (few-shot).** `random` > `none` — worked examples help even when
  irrelevant.
- **H3 (anchoring is self-specific).** `retrieved` ≥ `none` at every scale:
  other-task context does *not* incur the anchoring penalty that own-attempt
  context does (EXP-004).

**Analysis.** Paired McNemar exact + bootstrap CI, Holm-corrected over the
three primary contrasts, α=0.05.

**Falsification.** H3 is refuted if `retrieved` < `none` significantly. That
would be the stronger and more interesting result: added context *per se*
hurts small models, and EXP-004's anchoring finding is a special case of a
general context-dilution effect rather than a self-conditioning effect.

**Leakage audit, run before the experiment.** Retrieval over a benchmark that
also supplies the eval tasks is only legitimate under leave-one-out, and
near-duplicate tasks can still hand the model its answer. Measured similarity
between each retrieved exemplar's code and the query task's gold solution:
mean 0.38–0.39, p95 0.69–0.71, and **only 1.2–1.7% of exemplars exceed 0.8**.
Low enough not to drive a result, but non-zero and reported rather than
assumed away. Store coverage: 214/226/268 of 378 tasks (1.5B/3B/7B) — each
model's memory is exactly what it could actually solve.

**Threats.** (a) Longer prompts raise truncation risk on a 4096-token
context; `budget_exhausted` monitored per arm. (b) Exemplars consume context
the model might use for reasoning — a real mechanism, and if `random` loses
this is the likely explanation. (c) Store size differs by model (a stronger
model has more experience); this is intrinsic to "own experience" and is
reported, not corrected.

**Status.** ✅ Closed 2026-07-22.

### Result: a clean null — and that null is what makes EXP-004 interpretable

pass@1 on MBPP+ (n=378, greedy), 95% Wilson CIs:

| Model | `none` | `random` | `retrieved` |
|---|---|---|---|
| 1.5B | 0.566 [.516,.615] | 0.542 [.492,.592] | 0.542 [.492,.592] |
| 3B | 0.598 [.548,.646] | 0.595 [.545,.644] | 0.606 [.556,.654] |
| 7B | 0.709 [.661,.753] | 0.728 [.681,.770] | 0.696 [.648,.740] |

**All nine paired contrasts are non-significant after Holm correction.**
Every CI on the difference includes zero; the largest raw effect
(7B `retrieved − random`, −0.032, raw p=0.050) does not survive correction.

- **H1 (relevance) refuted.** `retrieved` − `random` is +0.000 / +0.011 /
  −0.032 — no retrieval effect at any scale.
- **H2 (few-shot) refuted.** `random` − `none` is −0.024 / −0.003 / +0.019.
  Worked examples neither help nor hurt.
- **H3 (anchoring is self-specific) supported.** `retrieved` is never
  significantly below `none`.

**Power.** With n=378 the CIs on differences are roughly ±0.035, so this
rules out effects larger than ~3.5 pp in either direction. It is a bounded
null, not an underpowered shrug — but it cannot exclude a genuine 1–2 pp
gain.

### Why this null matters: it isolates anchoring as *self*-specific

Put beside EXP-004, the pair of results is sharper than either alone:

| Context added to the prompt | Effect at 1.5B |
|---|---|
| The model's **own failed attempt** (EXP-004) | **−6.1 pp, p=0.003** |
| **Other tasks' solved code** (EXP-006) | −2.4 pp, n.s. (CI spans 0) |

Both add roughly comparable amounts of code to the context. If the EXP-004
penalty were a general context-dilution or distraction effect, retrieved
exemplars should have hurt similarly. They did not. **The damage is specific
to conditioning on your own failed attempt**, which is exactly what the
anchoring mechanism (EXP-005) predicts and what a generic "long prompts hurt
small models" story does not.

### Relation to prior work

This contradicts the retrieval-augmented few-shot literature, which reports
consistent gains from relevance-based exemplar selection (e.g. TF-IDF
retrieval improving F1 by 6–9 points in biomedical NER; retrieval-augmented
prompting beating random selection for vulnerability detection). Two honest
differences: those are *classification/detection* tasks where exemplars teach
an output convention, whereas MBPP+ tasks are self-contained function
synthesis with the required format already specified in the prompt — there is
less for an exemplar to teach. And our retriever is lexical BM25; a semantic
retriever might find relations BM25 misses. **We claim a null for
lexically-retrieved exemplars in small-model code generation, not a null for
retrieval in general.**

### Threats, checked

- **Arms genuinely differed:** 0/378 prompts identical between `random` and
  `retrieved` at every scale. (Outcomes coincide on 328–346 of 378 tasks
  because most tasks are easy or hard regardless of context — which is why
  the analysis is paired.)
- **Truncation: zero** in all nine arms. Not a budget artifact.
- **Leakage: audited before the run** — 1.2–1.7% of exemplars exceed 0.8
  similarity to the gold solution. Any leakage would *inflate* the
  `retrieved` arm, which did not win.

**Future work.** Semantic retrieval, distilled *lessons* rather than raw
solutions (RQ4's representation question is only partly answered — we tested
one representation), and larger stores. The store here covers 57–71% of the
benchmark; a store spanning many benchmarks might behave differently.

## EXP-004 — Does execution feedback content pay? (pre-registered 2026-07-22)

**RQ1.** Where is the cost/benefit knee in repair iterations *k*, and does
execution-feedback *content* beat blind resampling at matched budget — across
model scale?

**Why this is open.** arXiv:2606.31511 finds feedback content beats placebo by
+15 on 0.5–1.5B models; arXiv:2606.26978 finds execution worth only 1.25 pp
(n.s.) for frontier agents on repo tasks. Neither maps the middle, and neither
reports the *shape* of the k-curve. We measure 1.5B → 3B → 7B on the same
harness.

**Hypotheses, fixed before running.**
- **H1 (content).** `feedback` > `placebo` at k=8, paired, on MBPP+.
- **H2 (attempts).** `placebo` > `resample`, i.e. re-reading your own failed
  code helps even without knowing why it failed.
- **H3 (scale).** The `feedback − resample` gap *shrinks* as model scale
  grows, interpolating between the two bracketing papers.
- **H4 (knee).** Marginal gain per iteration decays sharply; most of the
  attainable gain arrives by k≈2.

**Design.** 3 models × 3 conditions × k_max=8, on **MBPP+** (378 tasks,
primary — the only benchmark powered at every scale per EXP-003b).
HumanEval+ reported as secondary, not used for significance.

Conditions differ *only* in what is appended after the original instruction:

| Condition | Retry prompt contains | Isolates |
|---|---|---|
| `resample` | original instruction only | value of another draw |
| `placebo` | + own previous code + content-free notice | value of seeing your attempt |
| `feedback` | + own previous code + real execution output | value of the facts |

**Controls.** All arms start from the *same* baseline run (identical first
attempts, so pairing is exact rather than statistical), share the token
budget (2048/attempt), the seed schedule, and the task set.

**Retries sample at temperature 0.8; the k=0 baseline stays greedy.** This is
forced, not stylistic, and was caught in smoke testing *before* any
experimental run (see MEMORY/lessons.md). At temperature 0 the model returns
the byte-identical solution on every iteration regardless of seed — verified
directly: three consecutive `feedback` retries produced the same 30-token
answer character-for-character. That would reduce `resample` to a no-op and
flatten every k-curve by construction, producing a null result that is an
artifact of decoding rather than evidence about feedback. 0.8 matches the
sampling temperature conventional for pass@k in the HumanEval line of work
and is applied **identically across all three conditions**, so the contrasts
remain matched; only the shared k=0 point is greedy. The code now refuses
temperature ≤ 0 for repair.

**Metrics.** pass@1 as a function of k (nested from one trajectory); tokens
consumed (the budget currency — batching-invariant, unlike latency);
iterations used; failure taxonomy shift.

**Analysis, fixed in advance.** Paired McNemar exact per contrast, bootstrap
CI on the difference. Primary contrast is `feedback` vs `placebo` at k=8 on
MBPP+. Three primary contrasts (H1–H3) → **Holm correction**; α=0.05.

**Falsification.** H1 is refuted if `feedback` − `placebo` has a CI including
zero at every scale. That is a publishable negative: it would say the gains
attributed to execution feedback in this regime are gains from retrying,
which is precisely the claim the placebo design exists to test.

**Threats.** (a) Repair prompts are longer than baseline prompts, so
truncation risk rises — `budget_exhausted` is monitored per arm and any arm
where it exceeds ~5% is reported as budget-limited, not capability-limited
(the EXP-001 lesson). (b) Early-exit on success means arms differ in tokens
spent; that is intended (cost is an outcome) but means pass rate must always
be read next to token cost. (c) MBPP+ tests are the same ones the feedback
quotes, so feedback could leak test content — inspected, since the model sees
only *failing input/expected/actual*, which is legitimate execution feedback,
but this is noted as a difference from settings where held-out tests exist.

**Status.** ✅ Closed 2026-07-22.

### Result: showing the model its own failed attempt *hurts*

**Blind resampling beats both feedback conditions at every scale.** The
headline is not "feedback fails to help" but the stronger and more surprising
"conditioning on your own failed code is actively harmful, and the execution
facts do not rescue it."

pass@1 on MBPP+ (n=378), k = 0…8:

| Model | Condition | k=0 | k=1 | k=2 | k=4 | k=8 | out-tokens |
|---|---|---|---|---|---|---|---|
| 1.5B | **resample** | .566 | .624 | .651 | .696 | **.749** | **63k** |
| 1.5B | placebo | .566 | .616 | .646 | .669 | .688 | 90k |
| 1.5B | feedback | .566 | .611 | .624 | .653 | .688 | 129k |
| 3B | **resample** | .598 | .651 | .693 | .735 | **.778** | **76k** |
| 3B | placebo | .598 | .646 | .661 | .685 | .709 | 89k |
| 3B | feedback | .598 | .632 | .646 | .693 | .735 | 84k |
| 7B | **resample** | .709 | .743 | .765 | .786 | **.820** | **49k** |
| 7B | placebo | .709 | .738 | .759 | .778 | .802 | 59k |
| 7B | feedback | .709 | .735 | .759 | .780 | .810 | 55k |

Paired contrasts at k=8 (McNemar exact, bootstrap CI, **Holm-corrected**
across the three primary contrasts):

| Contrast | 1.5B | 3B | 7B |
|---|---|---|---|
| feedback − placebo | +0.000 [−.026,+.029] p=1.00 | +0.026 [−.003,+.056] p=0.49 | +0.008 [−.013,+.029] p=1.00 |
| placebo − resample | **−0.061** [−.095,−.029] **p=0.003** | **−0.069** [−.103,−.037] **p=0.0006** | −0.019 [−.045,+.008] p=0.99 |
| feedback − resample | **−0.061** [−.095,−.029] **p=0.004** | **−0.042** [−.071,−.013] **p=0.042** | −0.011 [−.040,+.016] p=1.00 |

### Verdicts against the pre-registered hypotheses

- **H1 (feedback > placebo): refuted.** Every CI includes zero at every
  scale. This is exactly the pre-registered falsification criterion. The
  execution facts — failing input, expected value, actual value — buy nothing
  over a content-free "your solution was incorrect, try again."
- **H2 (placebo > resample): refuted, with the sign reversed.** Placebo is
  *significantly worse* than resample at 1.5B (−6.1 pp) and 3B (−6.9 pp).
  Seeing your own failed attempt is harmful, not merely useless.
- **H3 (gap shrinks with scale): supported.** `feedback − resample` is
  −0.061 → −0.042 → −0.011 as scale grows, monotonically shrinking toward the
  null the frontier-scale literature reports (arXiv:2606.26978's 1.25 pp,
  n.s.). The direction of our effect is negative throughout, which the
  hypothesis did not anticipate.
- **H4 (early knee): supported.** 46–53% of all attainable gain arrives by
  k=2 at every scale, with marginal gains decaying to ≈0 by k=7.

### Cost: the feedback arms are dominated on both axes

resample achieves the *best* pass rate using the *fewest* tokens — 63k vs
feedback's 129k at 1.5B (2.05×), and fewer attempts overall (it exits early
more often because it succeeds more). There is no cost/accuracy trade-off to
navigate here: at these scales, on this task distribution, conditioning on
the failed attempt is worse on both axes simultaneously.

### Mechanism: anchoring, confirmed (EXP-005)

Predicted before measuring: if conditioning on the failed attempt biases
sampling toward minor edits, the feedback arms should show markedly *lower*
inter-attempt diversity. Measured on the traces already collected (no new
inference), as mean similarity between consecutive attempts:

| Model | resample | placebo | feedback |
|---|---|---|---|
| 1.5B | 0.509 (5.2% near-identical) | 0.828 (45.6%) | 0.862 (**52.1%**) |
| 3B | 0.418 (1.8%) | 0.756 (29.3%) | 0.795 (37.9%) |
| 7B | 0.607 (13.7%) | 0.911 (67.8%) | 0.914 (**65.8%**) |

The effect is large, consistent, and in the predicted direction at every
scale (+0.30 to +0.38 similarity vs blind resampling). **Shown its own failed
code, the model regenerates a near-identical solution between a third and two
thirds of the time** — it edits rather than reconsiders. Blind resampling
redraws from a genuinely different region of the solution space.

This also explains H3's shrinking gap, which the hypothesis did not
anticipate. Anchoring *strength* is roughly constant across scale (+0.30–0.38
everywhere) — but its *cost* falls, because a larger model's failed first
attempt is a better thing to anchor on. At 1.5B the initial approach is more
often fundamentally wrong, so committing to it is expensive; at 7B it is
usually close, so the penalty nearly vanishes. The scale trend is not
feedback becoming more useful, it is anchoring becoming less harmful.

### Threats, checked

- **(a) Budget exhaustion: ruled out.** 0.0% truncation in all nine arms
  (0 of 8,082 responses). The result is not budget-limited. This mattered:
  the EXP-001 confound would have produced exactly this shape of result.
- **(b) Unequal token spend across arms: real but favourable.** The winning
  arm spends the least, so the finding cannot be explained by resample
  receiving more compute.
- **(c) Test leakage via feedback:** the model sees failing input / expected /
  actual, which is legitimate execution feedback, but MBPP+ evaluates on the
  same suite. Any leakage would *inflate* the feedback arm, so it cannot
  explain feedback losing.

### Relation to prior work

This partially contradicts arXiv:2606.31511, which reports feedback content
beating generic placebos on 0.5–1.5B models; we find that contrast
indistinguishable from zero at 1.5B–7B. It is consistent with, and extends,
arXiv:2606.26978: execution feedback is not worth its cost — and we add that
at small scale it is worse than not looking at your own output at all. The
blind-resampling control is what makes this visible; a study comparing only
feedback against no-repair would have reported "repair helps" and stopped.

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
