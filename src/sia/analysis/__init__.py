"""Analysis over run artifacts: failure taxonomy and aggregate statistics.

Everything here reads traces and manifests (ADR-0003) — never live state —
so any completed run can be re-analysed without re-running it.
"""

from sia.analysis.stats import mcnemar_exact, paired_bootstrap_diff
from sia.analysis.taxonomy import FailureReport, analyze_run, classify

__all__ = [
    "FailureReport",
    "analyze_run",
    "classify",
    "mcnemar_exact",
    "paired_bootstrap_diff",
]
