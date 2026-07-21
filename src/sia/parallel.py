"""Bounded parallel map over tasks, preserving input order.

Why this is safe for the experiments: concurrency changes *wall-clock* but not
token counts, and every budget in this project is denominated in tokens
(ADR-0005, and the EXP-001 lesson that a binding budget on one arm is a
confound). Per-call latency does inflate under batching, so latency is
reported as a throughput note, never as the matched-budget currency.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar

T = TypeVar("T")
R = TypeVar("R")


def default_workers() -> int:
    """Conservative default: enough to keep the server busy, not enough to
    thrash a 6 GB GPU. Override with ``SIA_WORKERS``."""
    env = os.environ.get("SIA_WORKERS")
    if env:
        return max(1, int(env))
    return 4


def parallel_map(
    fn: Callable[[T], R],
    items: Sequence[T],
    *,
    workers: int | None = None,
    on_result: Callable[[int, T, R], None] | None = None,
) -> list[R]:
    """Apply ``fn`` across ``items`` with a bounded pool, returning results in
    input order.

    ``on_result`` fires as each item completes (for progress reporting), so
    callers see liveness without the results themselves being reordered.
    Exceptions propagate — a failing task must not be silently dropped from an
    experiment.
    """
    n = len(items)
    if n == 0:
        return []
    count = workers if workers is not None else default_workers()
    if count <= 1 or n == 1:
        results = []
        for index, item in enumerate(items):
            value = fn(item)
            if on_result:
                on_result(index, item, value)
            results.append(value)
        return results

    results_by_index: dict[int, R] = {}
    with ThreadPoolExecutor(max_workers=min(count, n)) as pool:
        futures = {pool.submit(fn, item): (index, item) for index, item in enumerate(items)}
        for future in _as_completed(futures):
            index, item = futures[future]
            value = future.result()
            results_by_index[index] = value
            if on_result:
                on_result(index, item, value)
    return [results_by_index[i] for i in range(n)]


def _as_completed(futures: Iterable) -> Iterable:
    from concurrent.futures import as_completed

    return as_completed(futures)
