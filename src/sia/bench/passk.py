from __future__ import annotations

import math


def pass_at_k(n: int, c: int, k: int) -> float:
    """Unbiased pass@k estimator from Chen et al. 2021 (HumanEval paper).

    ``n`` samples drawn, ``c`` of them correct, estimate probability that at
    least one of ``k`` drawn samples is correct.
    """
    if n <= 0 or k <= 0:
        raise ValueError("n and k must be positive")
    if c < 0 or c > n:
        raise ValueError("c must be in [0, n]")
    if n - c < k:
        return 1.0
    return 1.0 - math.prod(1.0 - k / i for i in range(n - c + 1, n + 1))


def wilson_ci(passed: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion."""
    if total <= 0:
        raise ValueError("total must be positive")
    p = passed / total
    denom = 1 + z**2 / total
    center = (p + z**2 / (2 * total)) / denom
    margin = (z / denom) * math.sqrt(p * (1 - p) / total + z**2 / (4 * total**2))
    return (max(0.0, center - margin), min(1.0, center + margin))
