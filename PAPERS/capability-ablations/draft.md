# Try Again, Don't Look Back: Blind Resampling Outperforms Self-Repair in Small Code Models

*Draft — results final, prose in progress. Numbers here are generated from
`experiments/` and must be regenerated, not hand-edited, if runs change.*

## Abstract

Self-repair — showing a code model its failed attempt and asking it to fix
the problem — is a standard component of agentic coding systems, and is
usually evaluated against a no-repair baseline. We show that this comparison
is the wrong one. Across three model scales (1.5B/3B/7B, Qwen2.5-Coder) on
MBPP+, we run a placebo-controlled ablation in which retry attempts receive
either nothing, a content-free failure notice, or real execution feedback,
all at a matched iteration budget and against a blind-resampling control.
**Blind resampling wins at every scale, using roughly half the tokens.**
Conditioning on the model's own failed attempt costs 6.1 points at 1.5B
(p=0.003) and 4.2 points at 3B (p=0.042); execution-feedback content adds
nothing over a content-free placebo anywhere. We identify the mechanism as
**anchoring**: shown its own code, the model regenerates a near-identical
solution 33–68% of the time, versus 2–14% when resampling blind. A
complementary experiment shows retrieved *other-task* exemplars have no
effect in either direction (all contrasts n.s., bounded to ±3.5 pp),
establishing that the penalty is specific to self-conditioning rather than a
general context-dilution effect. The anchoring penalty shrinks with scale
(−6.1 → −4.2 → −1.1 pp), interpolating toward the null reported for frontier
agents; we argue this reflects anchoring becoming *cheaper*, not feedback
becoming useful.

## 1. Introduction

Contributions:

1. A placebo-controlled decomposition of the self-repair feedback packet at
   three model scales, with blind resampling as the control that prior work
   omits.
2. The finding that self-repair is *worse than retrying* below 7B, on both
   accuracy and cost.
3. A mechanism — anchoring — measured directly from inter-attempt code
   similarity, which also explains the scale trend.
4. A null result on retrieved experience that isolates the mechanism as
   self-specific.
5. An open, reproducible harness that runs entirely on one consumer GPU.

## 2. Related work

- **arXiv:2606.31511** — placebo-controlled feedback decomposition on
  0.5–1.5B models; reports feedback content beating generic placebos. We
  adopt its placebo methodology and find its central contrast
  indistinguishable from zero in our setting, while adding the
  blind-resampling control.
- **arXiv:2606.26978** — frontier agents on repo-level tasks; execution
  worth 1.25 pp (n.s.) at 56–62% token savings. Our 7B row is consistent;
  our smaller scales show active harm, a regime that work does not cover.
- Retrieval-augmented few-shot prompting reports consistent gains from
  relevance-based exemplar selection on classification tasks. We find no such
  effect for code synthesis with lexical retrieval (§5).

## 3. Method

**Models.** Qwen2.5-Coder 1.5B/3B/7B-Instruct, Q4_K_M, served locally.
**Benchmark.** MBPP+ (378 tasks, EvalPlus). HumanEval+ reported as secondary;
it is underpowered here (32–75 failing tasks per cell vs 110–164 on MBPP+).
**Baseline.** Greedy single-shot. All repair arms start from the *same*
baseline run, so pairing between baseline and arm is exact rather than
statistical.

**Conditions.** Retries differ only in what follows the original instruction:

| Condition | Retry prompt adds | Isolates |
|---|---|---|
| `resample` | nothing | value of another draw |
| `placebo` | own code + content-free notice | value of seeing your attempt |
| `feedback` | own code + real execution output | value of the facts |
| `reflect` | as `feedback` + "diagnose, then fix" | value of verbal reasoning |

**Decoding.** Retries sample at T=0.8, identically across conditions; only
the shared k=0 point is greedy. This is forced: at T=0 the model returns the
byte-identical solution every iteration, which would reduce `resample` to a
no-op and flatten every curve by construction (§7.1).

**Nested k.** One k=8 trajectory records a verdict after every iteration, so
all k ≤ 8 derive from a single run — cheaper, and better paired, since arms
share the trajectory prefix rather than merely the task.

**Statistics.** Paired McNemar exact per contrast, bootstrap CI on the
difference, Holm correction across the primary contrasts, α=0.05. All
hypotheses, decision rules and falsification criteria were registered in
`EXPERIMENTS.md` before each run.

## 4. Self-repair is worse than retrying (EXP-004)

[Table: k-curves, 3 models × 3 conditions — `experiments/EXP-004/`]
[Table: Holm-corrected contrasts at k=8]
[Figure 1: k-curves, 3-panel]
[Figure 2: forest plot of contrasts]
[Figure 4: pass rate vs cumulative tokens — resample dominates on both axes]

Headline numbers in `findings.md`.

## 5. The mechanism is anchoring (EXP-005)

[Table: inter-attempt similarity by condition and scale]
[Figure 3: similarity distributions]

## 6. Retrieved experience does nothing — and that is informative (EXP-006)

[Table: memory conditions × scale]

The null bounds any memory effect to ±3.5 pp and, critically, shows the
EXP-004 penalty is not a generic long-prompt effect.

## 7. Threats to validity

**7.1 Instrumentation bugs caught pre-registration.** Four measurement
failures were found and fixed before they could reach a result, each of which
would have produced a *plausible but wrong* number:
(i) code extraction stripped leading indentation, invalidating
completion-style outputs; (ii) a missing model produced a full manifest of
zeros indistinguishable from a real 0% score; (iii) `max_tokens` bound one
arm and not another, so a raw pass-rate gap measured budget fit rather than
capability; (iv) greedy retries returned byte-identical solutions, which
would have flattened every k-curve. Details in `MEMORY/lessons.md`.

**7.2 Budget exhaustion.** 0.0% of 8,082 repair responses and 0 of all
memory responses hit the token cap. No arm is budget-limited.

**7.3 Unequal token spend.** Arms differ in tokens because early exit on
success is intended (cost is an outcome). The direction favours the losing
arms: the winner spends the least.

**7.4 Test leakage.** Feedback quotes failing inputs from the same suite used
for scoring; any leakage would inflate the arm that lost. Memory retrieval
was audited before running: 1.2–1.7% of exemplars exceed 0.8 similarity to
the gold solution.

**7.5 Scope.** One benchmark family, one model family, ≤7B, Q4 quantized,
function-level synthesis. The 7B result is consistent with frontier findings
but we do not test frontier models. Retrieval is lexical BM25; a semantic
retriever is untested.

## 8. Practical implications

At these scales, an agent that fails a test should **retry from scratch, not
patch**. Iteration budgets beyond k≈2 buy little (46–53% of attainable gain
arrives by k=2). Execution feedback should be treated as a costed resource
with a demonstrated benefit, not a default.

## Reproduction

```bash
uv sync
uv run python scripts/run_exp004.py    # repair ablation
uv run python scripts/analyze_exp004.py
uv run python scripts/analyze_anchoring.py
uv run python scripts/build_memory.py  # includes leakage audit
uv run python scripts/run_exp006.py
```

Every number traces to a run manifest and a replayable JSONL trace under
`runs/`.
