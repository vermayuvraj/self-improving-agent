# TODO — current milestone: M1 (minimal baseline agent + fast eval loop)

Backend decided 2026-07-20: **local-only via Ollama** (ADR-0006).

## M1 tasks

- [ ] Install Ollama (winget) + pull candidate models — needs user approval
      (downloads: installer ~1 GB, models ~5 GB each)
- [ ] `uv init` project: pyproject, ruff, pytest, src layout (`sia/`)
- [ ] `sia/llm/`: `LLMClient` protocol + Anthropic adapter + OpenAI-compatible
      adapter; retries, token/cost accounting; unit tests with mocked APIs
- [ ] `sia/trace/`: event schema, JSONL writer, run manifest; tests
- [ ] `sia/sandbox/`: subprocess runner (timeout, cwd isolation, output caps);
      tests incl. infinite-loop and fork-bomb-lite cases
- [ ] `sia/bench/`: HumanEval + MBPP loaders (official datasets, cached),
      pass@k scoring per Chen et al. 2021; verify our scorer against
      published reference outputs
- [ ] `sia/agent/`: minimal loop — system prompt, shell + file-edit tools,
      step budget, stop conditions; every step traced
- [ ] CLI entrypoint: `sia run --bench humaneval --model X --config Y`
- [ ] EXP-001 (model selection): qwen3:8b vs qwen2.5-coder:7b, pass@1 on
      HumanEval + MBPP subset; sanity-check vs published numbers; pick the
      project's default model; record in EXPERIMENTS.md
- [ ] Docs pass: CHANGELOG, ROADMAP status, MEMORY lessons

## Backlog (later milestones — do not start)

- SWE-bench Lite via WSL2/Docker (M4) — verify Docker Desktop + WSL2 present
- Failure taxonomy design (M2)
