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

---

# Scope decision (2026-07-21): focused path to one rigorous paper

Confirmed with the project owner. The ten-milestone platform is achievable but
risks being thin everywhere; **one defensible paper beats a broad unfinished
system**. Remaining scope is therefore **M2 → M3 → M5 → M6 → paper**
(~8–10 sessions). M4 (repo-level/SWE-bench), M7 (multi-agent) and M8
(self-improving scaffold) are deferred, not cancelled — they become paper two.

Two findings from M1 forced this shape:

1. **Headroom.** An 85.4% HumanEval baseline leaves 24 failing tasks — far too
   few to power a capability ablation. Fixed in M2 by adopting **EvalPlus**
   (HumanEval+/MBPP+), which is also what the small-model repair literature
   uses, making our numbers directly comparable.
2. **SWE-bench is not viable on this hardware.** A 4096-token context (6 GB
   VRAM ceiling) cannot hold a repo issue plus source files, so a local 7B
   model would score near zero — and a floor effect makes every downstream
   ablation unmeasurable. Repo-level work becomes an optional cloud-API
   extension serving RQ8 (transfer), not a local milestone.

## M2 — Experiment engine + measurable headroom ⬜ (next)

Turn one-off runs into experiments, and make effects measurable.

- **EvalPlus integration** (HumanEval+, MBPP+): 80×/35× more tests, expected
  10–20 point pass@1 drop → real headroom for ablations
- Config-driven experiment definitions (YAML): model × capability flags × dataset
- Grid launcher; aggregate reports with CIs and paired significance tests
- Promote the failure taxonomy from `scripts/` into `sia/analysis/`
- **Exit criteria:** one command launches a full ablation grid and emits a
  paper-ready table; EvalPlus baseline established with ≥100 failing tasks
  per benchmark to ablate against.

## M3 — Self-debugging repair loop ⬜ (the core contribution)

Execute → read failure → patch → re-run, k times. **Placebo-controlled**
(design borrowed from arXiv:2606.31511, cited).

Conditions, all at matched output-token budget:
| Condition | Feedback given on retry |
|---|---|
| `k=0` | none (single-shot baseline) |
| `resample` | none — just try again (controls for extra attempts) |
| `placebo` | content-free, shape-matched ("your solution failed, try again") |
| `feedback` | real execution output: failing assertion, input, expected value |

- **RQ1 (sharpened):** where is the cost/benefit knee in k, and does the
  *content* of execution feedback beat merely resampling at equal budget?
  The literature brackets this but leaves it open: feedback content helps
  0.5–1.5B models (+15 over placebo, arXiv:2606.31511), yet adds ~nothing for
  frontier agents on repo tasks (1.25 pp, n.s., arXiv:2606.26978). **The 7B
  function-level middle ground, and the shape of the k-curve, are unmeasured.**
- **RQ2:** can the agent predict failure before execution? (confidence calibration)
- **Exit criteria:** k ∈ {0,1,2,4,8} × 4 conditions on HumanEval+/MBPP+ with
  cost curves and paired significance tests.

## M5 — Experience memory ⬜

The first self-improvement ingredient: learn across tasks, not within one.

- Episodic store of (task, trajectory, outcome, distilled lesson) mined from
  our own M1–M3 traces; retrieval into the prompt for new tasks
- **RQ4:** Does cross-task memory improve repair success and reduce cost, vs.
  matched-budget baseline? How should SE experience be represented
  (raw trajectories vs. distilled lessons vs. skills)?
- **Exit criteria:** memory-on vs. memory-off ablation on a held-out task
  split, with the same placebo discipline as M3 (a content-free "memory" of
  matched length is the control).

## M6 — Reflection ⬜

- Post-failure structured reflection (Reflexion-style) as a toggle
- **RQ5:** Does reflection help beyond simply re-running with the failure log
  in context? This control is missing in much of the literature, and M3's
  `feedback` condition *is* that control — so M6 is cheap once M3 exists.

## M9 — Paper 1 ⬜

Target: **"What actually helps? Placebo-controlled ablations of coding-agent
capabilities under matched budgets."** Material accumulates in
[PAPERS/](PAPERS/) from M2 onward; this milestone is writing, not new systems.

Positioning: the small-model and frontier-model ends of the repair question
are each addressed in the literature; we measure the middle and, crucially,
the *shape* of the cost/benefit curve — with placebo controls carried
consistently across repair, memory, and reflection rather than applied to one
module in isolation.

---

## Deferred to paper two (not cancelled)

- **M4 Repository understanding + SWE-bench** — blocked on context length, not
  effort. Revisit with a cloud API budget (~$50–200) as an RQ8 transfer study.
- **M7 Multi-agent decomposition** — RQ6 (does a role split beat a single agent
  at matched budget?) stands, but it needs M3's harness to be meaningful.
- **M8 Self-improving scaffold loop** — RQ7. The DGM-lite design still holds:
  bounded self-modification of prompts/tool configs, validated on a benchmark
  subset, sandboxed and budget-capped.
- Visualization dashboard beyond the current one, LoRA/QLoRA training,
  APPS/CodeContests/LiveCodeBench.
