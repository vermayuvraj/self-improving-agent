# SIA — Self-Improving Software Engineering Agent

An open-source research platform for autonomous software engineering. The goal is not
another coding assistant: it is a system that solves real software engineering tasks,
measures itself on public benchmarks, learns from its own execution traces, and
ultimately improves its own scaffold — with every capability implemented as a
**toggleable, benchmarkable module** so that its contribution can be measured in
controlled ablations.

**Preprint:** [Try Again, Don't Look Back: Blind Resampling Outperforms Self-Repair in Small Code Models](https://arxiv.org/abs/2607.26117) · [Results, baseline, and citation](https://www.yuvrajverma.tech/publications/blind-resampling)

## Research thesis

Minimal agent scaffolds (a bash loop + a strong LLM) already solve ~70% of
SWE-bench Verified. Most published agent systems add machinery — memory, reflection,
retrieval, multi-agent roles — without controlled evidence of what each part buys.
SIA is built as a **capability-ablation platform**: a deliberately minimal baseline
agent plus independently switchable capability modules, evaluated under fixed
budgets on public benchmarks. The long-term direction is experience-driven
self-improvement (the agent mining its own traces to improve future runs) under
realistic, single-machine compute.

## Project documents

| File | Purpose |
|---|---|
| [ROADMAP.md](ROADMAP.md) | Milestones, exit criteria, current status |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design and Architecture Decision Records |
| [RESEARCH.md](RESEARCH.md) | Literature landscape, research questions, positioning |
| [EXPERIMENTS.md](EXPERIMENTS.md) | Experiment protocol and registry |
| [TODO.md](TODO.md) | Active task list for the current milestone |
| [CHANGELOG.md](CHANGELOG.md) | Notable changes per milestone |
| [MEMORY/](MEMORY/) | Persistent project memory: lessons, failures, decisions |
| [PAPERS/](PAPERS/) | Accumulating material for future publications |

## Headline finding

**Self-repair is worse than retrying, below 7B.** In a placebo-controlled
ablation across three model scales on MBPP+, blind resampling beat every
condition that showed the model its own failed attempt — by 6.1 points at
1.5B (p=0.006) while using 2.5–5.5× fewer tokens. Execution-feedback content
added nothing over a content-free placebo at any scale.

The mechanism is **anchoring**: shown its own code, the model regenerates a
near-identical solution 33–68% of the time, versus 2–14% resampling blind. It
edits when it should reconsider. Two controls pin this down — retrieved
*other-task* exemplars have no effect at all (so the harm is specific to
self-conditioning, not long prompts), and verbal reflection, which loosens
the anchor most, performs best among own-output conditions while still losing
on cost. Anchoring rank predicts performance rank exactly.

The methodological point generalises: **for any capability that adds context
to a prompt, the control must be an equally expensive but uninformative
alternative.** Measured against a no-repair baseline, feedback looks like a
+12.2 pp win. Measured against blind resampling at matched budget, it loses.
Only the control changed.

Full results: [EXPERIMENTS.md](EXPERIMENTS.md) ·
Paper draft: [PAPERS/capability-ablations/](PAPERS/capability-ablations/draft.md) ·
[Live dashboard](https://self-improving-agent-wheat.vercel.app)

## Status

**M0–M3, M5, M6 complete** (2026-07-22); seven experiments closed, all
pre-registered before running. Paper draft assembled. Repo-level work
(SWE-bench), multi-agent decomposition and the self-improving scaffold loop
are deferred to a second paper — see [ROADMAP.md](ROADMAP.md) for why
(context length, not effort).

```bash
uv sync
uv run pytest                                  # 104 tests
uv run sia run --bench mbpp+ --model qwen2.5-coder:7b
uv run python scripts/analyze_exp004.py        # reproduce the headline table
```

## Hardware envelope

Development and experiments target a single workstation: i7-14700HX (20C/28T),
RTX 4050 Laptop 6 GB VRAM, 16 GB DDR5, 1 TB NVMe, Windows 11 (+ WSL2 for
containerized benchmarks). Experiments that exceed this envelope are designed as
optional cloud extensions, never as requirements.
