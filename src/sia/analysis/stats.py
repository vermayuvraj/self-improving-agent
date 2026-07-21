"""Paired significance tests for matched-budget comparisons.

Ablation arms run over the *same* task set, so comparisons are paired and
unpaired tests would be wrong (and anti-conservative). McNemar's exact test
is the standard choice for paired binary outcomes; the bootstrap gives a CI
on the difference for reporting effect size alongside significance.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence


def mcnemar_exact(a: Sequence[bool], b: Sequence[bool]) -> tuple[int, int, float]:
    """Exact McNemar test on paired binary outcomes.

    Returns ``(n01, n10, p_two_sided)`` where ``n01`` counts tasks that only
    ``b`` solved and ``n10`` counts tasks that only ``a`` solved. Concordant
    pairs carry no information about the difference and are excluded by
    construction — that is the point of the test.
    """
    if len(a) != len(b):
        raise ValueError("paired samples must have equal length")
    n01 = sum(1 for x, y in zip(a, b, strict=True) if not x and y)
    n10 = sum(1 for x, y in zip(a, b, strict=True) if x and not y)
    n = n01 + n10
    if n == 0:
        return 0, 0, 1.0
    # Two-sided exact binomial test against p=0.5 on discordant pairs.
    k = min(n01, n10)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return n01, n10, min(1.0, 2 * tail)


def paired_bootstrap_diff(
    a: Sequence[bool],
    b: Sequence[bool],
    *,
    iterations: int = 10_000,
    seed: int = 0,
    confidence: float = 0.95,
) -> tuple[float, float, float]:
    """Bootstrap CI for ``mean(b) - mean(a)``, resampling tasks (not outcomes).

    Returns ``(observed_diff, lo, hi)``.
    """
    if len(a) != len(b):
        raise ValueError("paired samples must have equal length")
    n = len(a)
    if n == 0:
        raise ValueError("empty samples")
    observed = sum(b) / n - sum(a) / n
    rng = random.Random(seed)
    diffs = []
    for _ in range(iterations):
        idx = [rng.randrange(n) for _ in range(n)]
        diffs.append(sum(b[i] for i in idx) / n - sum(a[i] for i in idx) / n)
    diffs.sort()
    alpha = (1 - confidence) / 2
    return observed, diffs[int(alpha * iterations)], diffs[int((1 - alpha) * iterations) - 1]
