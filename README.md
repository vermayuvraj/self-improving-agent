# SIA — Self-Improving Software Engineering Agent

An open-source research platform for autonomous software engineering. The goal is not
another coding assistant: it is a system that solves real software engineering tasks,
measures itself on public benchmarks, learns from its own execution traces, and
ultimately improves its own scaffold — with every capability implemented as a
**toggleable, benchmarkable module** so that its contribution can be measured in
controlled ablations.

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

## Status

**Milestone 0 (foundation) complete.** No agent code yet — M1 builds the minimal
baseline agent and evaluation harness. See [ROADMAP.md](ROADMAP.md).

## Hardware envelope

Development and experiments target a single workstation: i7-14700HX (20C/28T),
RTX 4050 Laptop 6 GB VRAM, 16 GB DDR5, 1 TB NVMe, Windows 11 (+ WSL2 for
containerized benchmarks). Experiments that exceed this envelope are designed as
optional cloud extensions, never as requirements.
