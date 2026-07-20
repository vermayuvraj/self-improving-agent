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
| —  | —    | —  | (none yet — first experiments land in M1) | — | — | — |
