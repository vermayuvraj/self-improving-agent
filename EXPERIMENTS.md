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
| EXP-001 | 2026-07-20 | — | code-specialized 7B ≥ general 8B on code benchmarks | HumanEval + MBPP | — | pre-registered |

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

**Status.** Pre-registered; blocked on model downloads.
