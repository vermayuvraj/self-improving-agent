"""Self-debugging repair loop (M3) — the project's core experiment.

Placebo-controlled by construction. The three retry conditions decompose the
feedback packet the way arXiv:2606.31511 does, so that a positive result can
be attributed to feedback *content* rather than to simply getting more
attempts:

    resample  original prompt only            — controls for extra attempts
    placebo   + previous code + generic notice — controls for seeing your code
    feedback  + previous code + real failure   — the treatment

``resample → placebo`` isolates the value of re-reading your own attempt;
``placebo → feedback`` isolates the value of the execution facts.
"""

from sia.repair.conditions import CONDITIONS, build_retry_messages
from sia.repair.loop import RepairOutcome, repair_task

__all__ = ["CONDITIONS", "RepairOutcome", "build_retry_messages", "repair_task"]
