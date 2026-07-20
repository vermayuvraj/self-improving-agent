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
| RQ1 | How does repair success scale with iteration count k; where is the cost/benefit knee? | M3 |
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

Per-module literature reviews are done at the start of each milestone and
recorded here; this section is the project-level map only.
