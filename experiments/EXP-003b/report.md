# EXP-003b — Model-scale baselines on EvalPlus

Not a hypothesis test. Establishes baseline pass rates and — the reason this
exists — enough failing tasks per cell to power the M3 repair ablations.
EvalPlus alone did not deliver the headroom the literature reported for older
models (EXP-003), so scale becomes the axis that provides it.


| Model | Benchmark | Condition | k | pass@1 | 95% CI | Δ vs baseline | Δ 95% CI | p |
|---|---|---|---|---|---|---|---|---|
| qwen2.5-coder:1.5b-instruct | humaneval+ | none | 0 | 0.543 | [0.466, 0.617] | — | — | — |
| qwen2.5-coder:1.5b-instruct | mbpp+ | none | 0 | 0.566 | [0.516, 0.615] | — | — | — |
| qwen2.5-coder:3b-instruct | humaneval+ | none | 0 | 0.738 | [0.666, 0.799] | — | — | — |
| qwen2.5-coder:3b-instruct | mbpp+ | none | 0 | 0.598 | [0.548, 0.646] | — | — | — |
| qwen2.5-coder:7b | humaneval+ | none | 0 | 0.805 | [0.738, 0.858] | — | — | — |
| qwen2.5-coder:7b | mbpp+ | none | 0 | 0.709 | [0.661, 0.753] | — | — | — |
