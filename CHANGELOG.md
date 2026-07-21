# Changelog

## 2026-07-21 — M1 complete: baseline agent + evaluation harness

- `sia.llm` (provider-agnostic client, Ollama-backed), `sia.trace`
  (JSONL events + run manifests), `sia.sandbox`, `sia.bench`
  (HumanEval + MBPP, Chen et al. pass@k, Wilson CIs), single-shot agent,
  `sia run` CLI. 33 tests + a network self-check running canonical
  solutions end-to-end.
- **EXP-001 closed:** `qwen2.5-coder:7b` selected as default
  (85.4% HumanEval, 74.8% MBPP; 25× faster than qwen3:8b).
- Three measurement bugs caught before they reached a results table:
  indentation-stripping extraction, scored artifacts from broken runs, and
  a token budget that bound on one arm only. All three now have permanent
  guards; see `MEMORY/lessons.md`.
- Research dashboard built and deployed (auto-deploys on push).

## 2026-07-20 — M0: Foundation

- Repository initialized; management docs created (README, ROADMAP,
  ARCHITECTURE, RESEARCH, EXPERIMENTS, TODO, MEMORY/, PAPERS/)
- Literature landscape surveyed (scaffold minimalism, self-evolving agents);
  positioning fixed: capability-ablation platform on single-workstation compute
- ADR-0001..0005 recorded (stack, thin LLM client, trace-first, staged
  sandboxing, benchmarks-before-capabilities)
