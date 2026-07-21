# Research

## Landscape (as of 2026-07, verified via web search 2026-07-20)

**State of the field.** SWE-bench Verified is the de-facto repo-level benchmark;
frontier systems score ~70–80%+, and the benchmark is mature enough that
contamination caveats now apply to top scores. Function-level benchmarks
(HumanEval, MBPP) are saturated for frontier models but remain useful as fast,
cheap regression tests and for studying *smaller* models where headroom exists.

**Scaffold minimalism.** SWE-agent introduced the Agent-Computer Interface
(ACI) idea; its successor **mini-swe-agent** reaches ~74% on SWE-bench Verified
with a ~100-line bash-first loop, and **Agentless** showed a fixed
localize–repair–validate pipeline (no agency at all) is competitive. Lesson:
with strong models, scaffold complexity is mostly dead weight — which makes
*measuring* each capability's marginal value the interesting question.

**Self-improvement.** The current frontier. **Darwin Gödel Machine**
(arXiv:2505.22954) evolves agent code against benchmark fitness with an archive
of variants (heavy compute). **Live-SWE-agent** (arXiv:2511.13646) self-evolves
its scaffold *during* problem solving, starting from a bash-only base.
**SWE-Exp** (arXiv:2507.23361) distills experience from past issue-resolution
trajectories to guide new ones. Related: Reflexion (verbal RL / episodic
memory), Self-Refine, AlphaCodium (test-driven flow engineering),
"Agent Learning via Early Experience" (arXiv:2510.08558).

**Open scaffolds to study/compare:** mini-swe-agent (baseline of record),
OpenHands (platform-scale, ~72% Verified), Agentless (pipeline), DGM reference
implementation (github.com/jennyzzt/dgm).

## Self-repair: what is already settled, and what is not (survey 2026-07-21)

This is M3's literature check, done before implementation. Two recent papers
bracket the question from opposite ends:

**Small frozen models — feedback content does help.** *Falsification, Not
Exposure* (arXiv:2606.31511) runs a **preregistered, placebo-controlled**
decomposition on frozen 0.5–1.5B code models over **HumanEval+/MBPP+**. It
separates the feedback packet into components and compares against
(a) blind resampling at matched output budget and (b) content-free,
shape-matched placebos. Result: code-plus-facts feedback recovers **+18 over
bare code and +15 over generic placebos**, while *instruction-only* effects
are indistinguishable from noise. Its contribution is explicitly methodological
— making "feedback content works" falsifiable rather than assumed.

**Frontier agents on repo tasks — execution barely helps.** *To Run or Not to
Run* (arXiv:2606.26978) finds prohibiting code execution costs only **1.25 pp**
resolve-rate (McNemar, p>0.05) while cutting tokens 56–62% and wall-clock
48–54%. Diagnosis: 54–66% of cases need a single edit (the model is right
first time), only 48.8% of reproduction executions yield actionable output,
and 81–100% of failures pass the agent's own tests but fail official
evaluation. Recommendation: treat execution as a costed resource, not a
default.

**The gap we take.** The two ends disagree, and neither maps the curve between
them. Open: (i) the **7B function-level middle ground** — large enough to
often be right first time, small enough that feedback might still pay;
(ii) the **shape of the k-curve** — everyone reports a single iteration
budget, nobody reports where the knee is; (iii) whether the placebo
discipline survives being applied *consistently across capabilities*
(repair, memory, reflection) rather than to one module in isolation. That
third point is the paper's spine.

**Methodological debts, cited not disguised:** the placebo/matched-budget
design is adopted from arXiv:2606.31511; the "execution is a costed resource"
framing from arXiv:2606.26978; pass@k from Chen et al. 2021; EvalPlus
(HumanEval+/MBPP+, 80×/35× more tests) as the evaluation substrate, chosen
both for rigour and because it is what the small-model repair work uses,
making our numbers directly comparable.

## Our positioning

The self-improvement papers demonstrate *that* agents can improve themselves
but rarely isolate *which* ingredient does the work, at what compute cost, and
whether gains transfer across task distributions. Ablations, when present, are
usually at unmatched budgets. Our platform is built so that every capability
(repair iterations, memory, reflection, retrieval, role decomposition, scaffold
evolution) is an independent toggle evaluated under **matched token/cost
budgets** on a **single-workstation compute envelope** — a reproducibility
story most labs' setups cannot offer and most practitioners actually need.

We deliberately run in the **small-model regime** (7–8B local models,
ADR-0006): function-level benchmarks are unsaturated there, capability
ablations produce measurable effect sizes, anyone can reproduce our results
for free, and the "does it transfer to frontier models?" question (RQ8)
becomes a contribution rather than a threat to validity.

## Research questions

| ID | Question | Milestone |
|----|----------|-----------|
| RQ1 | Where is the cost/benefit knee in repair iterations k, and does execution-feedback *content* beat blind resampling at matched budget for a 7B model? (Bracketed by arXiv:2606.31511 at 0.5–1.5B and arXiv:2606.26978 at frontier scale; middle unmeasured.) | M3 |
| RQ2 | Can the agent predict failure before execution (confidence calibration)? | M3 |
| RQ3 | Does explicit retrieval beat agent-driven grep at matched budget? | M4 |
| RQ4 | Does cross-task experience memory improve success/cost? How should SE experience be represented (trajectory vs. lesson vs. skill)? | M5 |
| RQ5 | Does structured reflection beat the control of simply re-prompting with the failure log? | M6 |
| RQ6 | Does planner/programmer/reviewer decomposition beat a single agent at matched budget? | M7 |
| RQ7 | Which scaffold dimensions (prompt, tools, iteration policy) yield self-improvement gains under a fixed validation budget? | M8 |
| RQ8 | Do capability gains measured on small models transfer to frontier models, and vice versa? | cross-cutting |

Candidate additions (not yet scheduled): optimal trace granularity for
experience mining; whether failure-taxonomy labels can be predicted online and
used for routing; memory forgetting/consolidation policies.

## Sources

- SWE-bench Verified leaderboards: [Steel.dev](https://leaderboard.steel.dev/leaderboards/swe-bench-verified/), [CodeSOTA](https://www.codesota.com/benchmark/swe-bench-verified-agentic)
- [UTBoost: Rigorous Evaluation of Coding Agents on SWE-Bench](https://arxiv.org/pdf/2506.09289) (contamination/test-design caveats)
- [mini-swe-agent overview](https://vibecodinghub.org/tools/mini-swe-agent)
- [OpenHands vs SWE-Agent comparison](https://localaimaster.com/blog/openhands-vs-swe-agent)
- [Darwin Gödel Machine](https://arxiv.org/abs/2505.22954) · [reference impl](https://github.com/jennyzzt/dgm)
- [Live-SWE-agent](https://arxiv.org/abs/2511.13646)
- [SWE-Exp: Experience-Driven Software Issue Resolution](https://arxiv.org/html/2507.23361v2)
- [Agent Learning via Early Experience](https://arxiv.org/abs/2510.08558)
- [Skywork-SWE: Data Scaling Laws for SWE in LLMs](https://arxiv.org/pdf/2506.19290)
- [Falsification, Not Exposure: Placebo-Controlled Decomposition of Self-Repair Feedback in Frozen Small Code Models](https://arxiv.org/abs/2606.31511) — placebo design, HumanEval+/MBPP+
- [To Run or Not to Run: Cost-Effectiveness of Code Execution in LLM-Based Program Repair](https://arxiv.org/html/2606.26978)
- [EvalPlus (HumanEval+ / MBPP+)](https://evalplus.github.io/) — 80×/35× more tests

Per-module literature reviews are done at the start of each milestone and
recorded here; this section is the project-level map only.
