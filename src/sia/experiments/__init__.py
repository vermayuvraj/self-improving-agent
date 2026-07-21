"""Config-driven experiments: a YAML grid in, a paper-ready table out.

An experiment is a cartesian product over declared axes (model × benchmark ×
capability flags), each cell a run. The spec is the unit of reproducibility —
re-running the same spec re-runs the same grid, and cells whose runs already
exist are skipped so a grid can be resumed after an interruption.
"""

from sia.experiments.report import build_report, format_markdown
from sia.experiments.spec import ExperimentSpec, GridCell, load_spec

__all__ = ["ExperimentSpec", "GridCell", "build_report", "format_markdown", "load_spec"]
