# Architecture

## Principles

1. **Baseline-first.** The core agent stays minimal (mini-swe-agent showed a
   ~100-line loop reaches 74% on SWE-bench Verified). Every additional
   capability is a module that can be switched off, so its contribution is
   always measurable.
2. **Trace-first.** Every agent step is an event in an append-only JSONL trace.
   Traces are the substrate for evaluation, failure analysis, experience
   memory (M5), and self-improvement (M8). If it isn't in the trace, it
   didn't happen.
3. **Reproducible by construction.** A run is fully determined by
   (config, model, dataset, seed) up to LLM nondeterminism. Run manifests
   record all four plus cost, tokens, latency, and git commit.
4. **Hardware-realistic.** Single workstation, 6 GB VRAM, 16 GB RAM. CPU
   parallelism for evaluation; API or small local models for inference.

## Target module map

Modules land in milestone order (see ROADMAP.md); nothing below is built
before its milestone.

```
sia/
  llm/          M1  provider-agnostic client (Anthropic, OpenAI-compatible)
  agent/        M1  core loop, tools (shell, file edit), step budget
  sandbox/      M1  local subprocess sandbox → M4: Docker/WSL2 sandbox
  trace/        M1  JSONL event log, run manifests, replay
  bench/        M1  HumanEval, MBPP → M4: SWE-bench Lite
  experiments/  M2  config grid, launcher, reports, failure taxonomy
  repair/       M3  execute-diagnose-patch loop
  repo/         M4  localization / code search
  memory/       M5  episodic experience store + retrieval
  reflect/      M6  post-failure reflection
  roles/        M7  planner / programmer / reviewer decomposition
  evolve/       M8  scaffold self-modification loop
```

## Architecture Decision Records

### ADR-0001: Python 3.11 + uv
Python is the lingua franca of every benchmark and baseline we compare
against (SWE-bench harnesses are Python; HumanEval/MBPP are Python tasks).
`uv` for env + lockfile reproducibility. Full typing, `ruff` for lint/format,
`pytest` for tests.

### ADR-0002: Thin in-house LLM client, not LiteLLM/LangChain
We need exactly two API shapes: Anthropic Messages and OpenAI-compatible chat
completions (which covers OpenAI, Ollama, llama.cpp server, vLLM, OpenRouter —
hence local models too). A ~200-line adapter with a common `LLMClient`
protocol gives us full control of retries, token accounting, and trace
capture. Framework dependencies churn fast, hide costs, and add abstraction
we would have to fight in experiments. Revisit only if we need >2 API shapes.

### ADR-0003: Traces as the single source of truth
One event schema (`step`, `llm_call`, `tool_call`, `tool_result`, `verdict`)
in JSONL per run, plus a manifest JSON. Evaluation reads traces, the failure
taxonomy reads traces, M5 memory is mined from traces, M8 self-improvement is
validated against traces. This is what makes the later research modules cheap:
they consume a format that exists from M1.

### ADR-0004: Sandboxing strategy — staged
M1: `subprocess` with timeout + working-dir isolation is sufficient and fast
for HumanEval/MBPP (we execute only code the agent itself wrote against known
tests). M4: SWE-bench requires the official Docker images — these run under
WSL2; the Windows-side harness talks to the Docker daemon. We do not build a
custom container layer; we use the official `swebench` evaluation harness for
scoring to keep numbers comparable with the literature.

### ADR-0005: Benchmarks before capabilities
No capability module is merged without an experiment entry showing its effect
on at least one benchmark at matched budget. "Matched budget" means equal
token/cost ceilings, not equal iteration counts — otherwise added machinery
smuggles in extra compute and the comparison is void.
