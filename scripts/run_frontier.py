"""EXP-008: the frontier-scale arm — does anchoring vanish?

Provider-agnostic: reads the endpoint from environment variables, so it works
against any OpenAI-compatible free tier (OpenRouter :free models, Gemini's
OpenAI endpoint, Groq, DeepSeek) with zero code change.

    SIA_FRONTIER_MODEL     e.g. "qwen/qwen3-coder:free"
    SIA_FRONTIER_BASE_URL  e.g. "https://openrouter.ai/api/v1"
    SIA_FRONTIER_KEY       your free API key
    SIA_FRONTIER_LIMIT     optional: first N tasks only (fast signal); default all 378
    SIA_WORKERS            keep low (2) for free rate limits; the client retries 429s

Runs baseline (greedy) then the three decisive repair conditions
(resample / feedback / reflect) on MBPP+, resumable via cells.json. Placebo is
dropped to conserve rate-limited budget; resample vs feedback is the contrast
that answers whether the anchoring penalty survives at scale, and reflect
tests whether reasoning helps where it did not below 7B.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from sia.bench import load_tasks
from sia.llm import LLMError, Message, OpenAICompatClient
from sia.repair.runner import run_repair
from sia.runner import run_benchmark

ROOT = Path(__file__).resolve().parent.parent
EXP_DIR = ROOT / "experiments" / "EXP-008"
CELLS = EXP_DIR / "cells.json"

BENCH = "mbpp+"
K_MAX = 8
SEED = 7
CONDITIONS = ("resample", "feedback", "reflect")


def _require_env() -> tuple[str, str, str, int]:
    model = os.environ.get("SIA_FRONTIER_MODEL")
    base_url = os.environ.get("SIA_FRONTIER_BASE_URL")
    key = os.environ.get("SIA_FRONTIER_KEY")
    limit = os.environ.get("SIA_FRONTIER_LIMIT")
    missing = [
        n
        for n, v in [
            ("SIA_FRONTIER_MODEL", model),
            ("SIA_FRONTIER_BASE_URL", base_url),
            ("SIA_FRONTIER_KEY", key),
        ]
        if not v
    ]
    if missing:
        print(f"error: set {', '.join(missing)} (see the module docstring)", file=sys.stderr)
        raise SystemExit(2)
    return model, base_url, key, int(limit) if limit else 0


def main() -> int:
    model, base_url, key, limit = _require_env()
    tasks = load_tasks(BENCH)
    if limit:
        tasks = tasks[:limit]
        print(f"NOTE: limited to first {limit} tasks (fast-signal mode)", flush=True)

    EXP_DIR.mkdir(parents=True, exist_ok=True)
    cells = json.loads(CELLS.read_text(encoding="utf-8")) if CELLS.exists() else {}

    def client() -> OpenAICompatClient:
        # Long timeout + patient retries: free tiers are slow and burst-limit
        # (HTTP 429) aggressively. 8 retries at a 4s base delay rides out the
        # per-10s window; the daily cap, if hit, surfaces as a terminal error
        # and the run resumes tomorrow from cells.json.
        return OpenAICompatClient(
            model,
            base_url=base_url,
            api_key=key,
            timeout_s=180.0,
            max_retries=8,
            retry_base_delay_s=4.0,
        )

    # Probe with a real 1-token completion rather than the /models listing:
    # third-party endpoints list models inconsistently, but a live call
    # unambiguously confirms the key works and the model responds — while
    # still failing fast on a typo or bad key (the EXP-001 guard's intent).
    print("probing endpoint...", flush=True)
    probe = client()
    try:
        probe.complete([Message("user", "print('ok')")], max_tokens=5, temperature=0.0)
    except LLMError as exc:
        print(f"error: endpoint probe failed: {exc}", file=sys.stderr)
        return 1
    finally:
        probe.close()
    print("  endpoint OK", flush=True)

    tag = model.replace("/", "_").replace(":", "_")

    # 1) Baseline (greedy single-shot) — the k=0 point and the repair seed.
    base_label = f"{tag}|{BENCH}|none|k=0"
    if base_label not in cells:
        print(f"\n=== baseline: {model} ===", flush=True)
        c = client()
        try:
            summary = run_benchmark(
                BENCH, c, tasks=tasks, seed=SEED, temperature=0.0, exec_timeout_s=60.0,
                extra_config={"exp": "EXP-008", "frontier": True},
                progress=lambda line: print(line, flush=True),
            )
        finally:
            c.close()
        cells[base_label] = summary.run_id
        CELLS.write_text(json.dumps(cells, indent=2), encoding="utf-8")
        p1 = summary.pass_rates["pass@1"]
        print(f"  baseline pass@1={p1:.3f} run={summary.run_id}", flush=True)

    baseline_run = cells[base_label]

    # 2) Repair conditions, seeded from the baseline run.
    for condition in CONDITIONS:
        label = f"{tag}|{BENCH}|{condition}|k={K_MAX}"
        if label in cells:
            print(f"skip (done): {label}", flush=True)
            continue
        print(f"\n=== {condition}: {model} ===", flush=True)
        c = client()
        try:
            summary = run_repair(
                BENCH, c, condition=condition, k_max=K_MAX, baseline_run_id=baseline_run,
                tasks=tasks, seed=SEED, exec_timeout_s=60.0,
                progress=lambda line: print(line, flush=True),
            )
        finally:
            c.close()
        cells[label] = summary.run_id
        CELLS.write_text(json.dumps(cells, indent=2), encoding="utf-8")
        curve = "  ".join(f"k={k}:{v:.3f}" for k, v in sorted(summary.pass_at_k.items()))
        print(f"  run={summary.run_id}\n  {curve}", flush=True)

    print("\n=== EXP-008 complete ===", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
