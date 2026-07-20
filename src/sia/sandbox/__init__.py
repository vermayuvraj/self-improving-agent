"""Code execution sandboxes (ADR-0004).

M1: local subprocess with timeout and output caps — sufficient for
HumanEval/MBPP where we execute agent-written code against known tests.
M4 adds a Docker-backed sandbox for SWE-bench.
"""

from sia.sandbox.local import ExecResult, run_python

__all__ = ["ExecResult", "run_python"]
