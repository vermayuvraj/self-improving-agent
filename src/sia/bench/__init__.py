"""Benchmarks: task loading, program assembly, and scoring.

M1 ships HumanEval and MBPP (fast, local, no containers). Scoring follows
Chen et al. 2021 pass@k. SWE-bench arrives in M4 (ADR-0004).
"""

from sia.bench.base import BenchTask, assemble_program, build_execution, load_tasks
from sia.bench.extract import extract_code
from sia.bench.passk import pass_at_k, wilson_ci

BENCHMARKS = ("humaneval", "mbpp", "humaneval+", "mbpp+")

__all__ = [
    "BENCHMARKS",
    "BenchTask",
    "assemble_program",
    "build_execution",
    "extract_code",
    "load_tasks",
    "pass_at_k",
    "wilson_ci",
]
