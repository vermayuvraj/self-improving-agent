"""Command-line entry point: ``sia run --bench humaneval --model qwen2.5-coder:7b``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sia.llm import LLMError, OpenAICompatClient
from sia.llm.openai_compat import OLLAMA_BASE_URL
from sia.runner import run_benchmark


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sia", description="SIA benchmark runner")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run a benchmark")
    run.add_argument("--bench", required=True, choices=["humaneval", "mbpp"])
    run.add_argument("--model", required=True, help="model name as served by the endpoint")
    run.add_argument("--base-url", default=OLLAMA_BASE_URL)
    run.add_argument("--api-key", default=None)
    run.add_argument("--limit", type=int, default=None, help="first N tasks only")
    run.add_argument("--samples", type=int, default=1, help="samples per task")
    run.add_argument("--temperature", type=float, default=0.0)
    run.add_argument("--seed", type=int, default=None)
    run.add_argument("--max-tokens", type=int, default=2048)
    run.add_argument("--exec-timeout", type=float, default=10.0, help="seconds per program")
    run.add_argument("--runs-dir", type=Path, default=Path("runs"))
    run.add_argument("--data-dir", type=Path, default=Path("data"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command != "run":  # pragma: no cover - argparse enforces this
        return 2

    llm = OpenAICompatClient(args.model, base_url=args.base_url, api_key=args.api_key)
    try:
        llm.check_available()
    except LLMError as exc:
        llm.close()
        print(f"error: {exc}", file=sys.stderr)
        return 1
    try:
        summary = run_benchmark(
            args.bench,
            llm,
            limit=args.limit,
            samples=args.samples,
            temperature=args.temperature,
            seed=args.seed,
            max_tokens=args.max_tokens,
            exec_timeout_s=args.exec_timeout,
            runs_dir=args.runs_dir,
            data_dir=args.data_dir,
            progress=lambda line: print(line, flush=True),
        )
    finally:
        llm.close()

    print()
    print(f"run_id     : {summary.run_id}")
    print(f"bench      : {summary.bench} ({summary.n_tasks} tasks x {summary.samples} samples)")
    print(f"model      : {summary.model}")
    for name, value in summary.pass_rates.items():
        print(f"{name:<11}: {value:.3f}")
    if summary.ci95:
        print(f"95% CI     : [{summary.ci95[0]:.3f}, {summary.ci95[1]:.3f}]")
    totals = summary.totals
    print(
        f"tokens     : {totals['prompt_tokens']:.0f} in / {totals['completion_tokens']:.0f} out"
        f" | llm errors: {totals['llm_errors']:.0f}"
        f" | wall: {totals['wall_s']:.0f}s"
    )
    print(f"artifacts  : {summary.run_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
