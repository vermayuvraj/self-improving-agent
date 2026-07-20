# TODO — current milestone: M1 (minimal baseline agent + fast eval loop)

Blocked on: LLM backend decision (API key vs. local model) — asked 2026-07-20.

## M1 tasks

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
- [ ] EXP-001: baseline pass@1 on HumanEval + MBPP; sanity-check vs published
      numbers for chosen model; record in EXPERIMENTS.md
- [ ] Docs pass: CHANGELOG, ROADMAP status, MEMORY lessons

## Backlog (later milestones — do not start)

- SWE-bench Lite via WSL2/Docker (M4) — verify Docker Desktop + WSL2 present
- Failure taxonomy design (M2)
