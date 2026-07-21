# Roadmap

Milestones are ordered so that every capability lands on top of a measurable
baseline. A milestone is done only when its **exit criteria** are met and its
results are recorded in [EXPERIMENTS.md](EXPERIMENTS.md).

Legend: ✅ done · 🔨 in progress · ⬜ not started

## M0 — Foundation ✅ (2026-07-20)

Repo, management documents, literature grounding, architecture decisions.

## M1 — Minimal baseline agent + fast evaluation loop ✅ (2026-07-21)

Exit criteria met: HumanEval 85.4% / MBPP 74.8% for `qwen2.5-coder:7b`, both
in the published range for the model; runs are reproducible from config
alone (manifest records config hash, model, seed, git commit). EXP-001
closed. **Open issue for M2: statistical headroom** — an 85.4% baseline
leaves only 24 failing HumanEval tasks, too few to power capability
ablations. Add a harder benchmark or a weaker ablation subject before M3.

<details><summary>Original scope</summary>

The smallest agent that can be benchmarked, plus the harness to benchmark it.

- Provider-agnostic LLM client (Anthropic + any OpenAI-compatible endpoint)
- Minimal ReAct-style agent: system prompt + shell/edit tools, bounded steps
- Local sandboxed code execution (subprocess, timeout, resource caps)
- Benchmark runner for **HumanEval** and **MBPP** (fast, local, no Docker)
- Trace logging: every run emits a replayable JSONL trace + run manifest
  (config hash, model, seed, cost, latency, tokens)
- **Exit criteria:** pass@1 on HumanEval and MBPP reproduces published numbers
  for the chosen model within noise; two identical runs produce comparable
  results from config alone.
</details>

## M2 — Experiment engine ⬜

Turn one-off runs into experiments.

- Config-driven experiment definitions (YAML): model × capability flags × dataset
- Cost/latency/iteration accounting; per-run and aggregate reports
- Failure taxonomy: automatic classification of why a task failed
  (wrong plan, bad edit, test misunderstanding, timeout, API error)
- **Exit criteria:** a full ablation grid can be launched with one command and
  produces a table ready for a paper.

## M3 — Self-debugging repair loop ⬜

First research module. Execute → read failure → patch → re-run, k times.

- **RQ1:** How does repair success scale with iteration count k? Where is the
  knee of the cost/benefit curve?
- **RQ2:** Can the agent predict, before execution, whether its patch will fail?
  (calibration of self-reported confidence vs. outcome)
- **Exit criteria:** ablation k ∈ {0,1,2,4,8} on HumanEval+MBPP with cost curves.

## M4 — Repository understanding + SWE-bench Lite ⬜

Scale from function-level to repo-level tasks.

- Fault localization / code search (start with Agentless-style hierarchical
  localization; retrieval index only if measurably better)
- SWE-bench Lite harness via Docker under WSL2
- **RQ3:** How much does explicit retrieval buy over letting the agent grep,
  at matched budget?
- **Exit criteria:** SWE-bench Lite score for baseline agent within the range
  published for comparable open scaffolds with the same model.

## M5 — Experience memory ⬜

The first self-improvement ingredient: learn across tasks, not within one.

- Episodic store of (task, trajectory, outcome, distilled lesson) mined from
  our own M1–M4 traces; retrieval into the prompt for new tasks
- **RQ4:** Does cross-task memory improve repair success and reduce cost, vs.
  matched-budget baseline? How should SE experience be represented
  (raw trajectories vs. distilled lessons vs. skills)?
- **Exit criteria:** memory-on vs. memory-off ablation on held-out task split.

## M6 — Reflection ⬜

- Post-failure structured reflection (Reflexion-style) as a toggle
- **RQ5:** Does reflection help beyond simply re-running with the failure log
  in context? (This control is missing in much of the literature.)

## M7 — Multi-agent decomposition ⬜

- Planner/programmer/reviewer role split as a toggle over the same base agent
- **RQ6:** At matched token budget, does the role split beat the single agent?

## M8 — Self-improving scaffold loop ⬜

DGM-lite under realistic compute: the agent proposes bounded modifications to
its own prompts/tool configs (not arbitrary code at first), validated on a
benchmark subset, kept only if they win.

- **RQ7:** Which scaffold dimensions (prompt, tool set, iteration policy) yield
  self-improvement gains under a fixed validation budget?
- Safety rails: sandboxed, budget-capped, human-reviewed archive of variants.

## M9 — Paper 1 ⬜

Target: "What actually helps? A controlled ablation study of coding-agent
capabilities under matched budgets." Material accumulates in
[PAPERS/](PAPERS/) from M2 onward; this milestone is writing, not new systems.

## Deliberately deferred

Visualization dashboard (M2 reports suffice until there is data worth
dashboarding), LoRA/QLoRA training (only if a research question demands it;
6 GB VRAM limits us to ~7B QLoRA), APPS/CodeContests/LiveCodeBench (added when
they answer a question HumanEval/MBPP/SWE-bench cannot).
