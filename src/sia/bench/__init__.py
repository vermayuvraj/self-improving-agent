"""Benchmarks: task loading, program assembly, and scoring.

M1 ships HumanEval and MBPP (fast, local, no containers). Scoring follows
Chen et al. 2021 pass@k. SWE-bench arrives in M4 (ADR-0004).
"""

from sia.bench.base import BenchTask, assemble_program, load_tasks
from sia.bench.extract import extract_code
from sia.bench.passk import pass_at_k, wilson_ci

__all__ = ["BenchTask", "assemble_program", "extract_code", "load_tasks", "pass_at_k", "wilson_ci"]
