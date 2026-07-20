# TODO — current milestone: M1 (minimal baseline agent + fast eval loop)

Backend decided 2026-07-20: **local-only via Ollama** (ADR-0006).

## M1 tasks

- [x] Install Ollama (approved 2026-07-20; model pulls in progress)
- [x] `uv init` project: pyproject, ruff, pytest, src layout (`sia/`)
- [x] `sia/llm/`: `LLMClient` protocol + OpenAI-compatible adapter (covers
      Ollama; Anthropic adapter deferred — no cloud backend per ADR-0006);
      retries, token accounting; unit tests with mocked transport
- [x] `sia/trace/`: event schema, JSONL writer, run manifest; tests
- [x] `sia/sandbox/`: subprocess runner (timeout, cwd isolation, output caps);
      tests incl. infinite-loop and output-flood cases
- [x] `sia/bench/`: HumanEval + MBPP loaders (official datasets, cached),
      pass@k per Chen et al. 2021; harness self-check: canonical solutions
      pass end-to-end (network-marked test)
- [x] `sia/agent/`: single-shot baseline, fully traced. (Tool-using loop
      deliberately deferred to M3 where it is first needed — the M1 baseline
      is one call per task, per ADR-0005 build-only-what's-measured.)
- [x] CLI entrypoint: `sia run --bench {humaneval,mbpp} --model X ...`
- [ ] EXP-001 (model selection): qwen3:8b vs qwen2.5-coder:7b, pass@1 on
      HumanEval + MBPP; pre-registered in EXPERIMENTS.md; blocked on model
      downloads
- [ ] Docs pass: CHANGELOG, ROADMAP status, MEMORY lessons

## Backlog (later milestones — do not start)

- SWE-bench Lite via WSL2/Docker (M4) — verify Docker Desktop + WSL2 present
- Failure taxonomy design (M2)
