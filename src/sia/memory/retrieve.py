"""BM25 lexical retrieval over the experience store.

Lexical rather than embedding-based, deliberately: BM25 needs no model, no
GPU (which the benchmark run is already saturating), and is deterministic and
auditable — every retrieval can be explained by the terms that matched. The
NER literature reports TF-IDF retrieval performing best among retrievers in
comparable few-shot settings, so this is a reasonable first instrument rather
than a compromise. If retrieval shows an effect, embeddings become a
worthwhile follow-up; if it shows none, a stronger retriever is the obvious
next thing to rule out.
"""

from __future__ import annotations

import math
import random
import re
from collections import Counter

from sia.memory.store import MemoryItem, MemoryStore

_TOKEN_RE = re.compile(r"[a-z0-9_]+")

# Terms that appear in nearly every benchmark instruction carry no signal
# about which task this is, and would otherwise dominate short queries.
_BOILERPLATE = frozenset(
    [
        "write",
        "a",
        "python",
        "function",
        "to",
        "the",
        "of",
        "and",
        "in",
        "for",
        "that",
        "with",
        "your",
        "solution",
        "must",
        "satisfy",
        "respond",
        "complete",
        "single",
        "code",
        "block",
        "no",
        "explanations",
        "given",
        "return",
        "program",
    ]
)

K1 = 1.5
B = 0.75


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _BOILERPLATE and len(t) > 1]


class Retriever:
    """BM25 over memory-item instructions."""

    def __init__(self, store: MemoryStore) -> None:
        self.items: list[MemoryItem] = store.items
        self._docs = [tokenize(i.instruction) for i in self.items]
        self._lens = [len(d) for d in self._docs]
        self._avg_len = (sum(self._lens) / len(self._lens)) if self._lens else 0.0
        self._tf = [Counter(d) for d in self._docs]
        df: Counter[str] = Counter()
        for doc in self._docs:
            df.update(set(doc))
        n = len(self._docs)
        self._idf = {
            term: math.log(1 + (n - count + 0.5) / (count + 0.5)) for term, count in df.items()
        }

    def score(self, query_tokens: list[str], index: int) -> float:
        tf = self._tf[index]
        length = self._lens[index] or 1
        total = 0.0
        for term in query_tokens:
            freq = tf.get(term, 0)
            if not freq:
                continue
            idf = self._idf.get(term, 0.0)
            denom = freq + K1 * (1 - B + B * length / (self._avg_len or 1))
            total += idf * (freq * (K1 + 1)) / denom
        return total

    def retrieve(
        self, query: str, *, k: int = 2, exclude_task_ids: set[str] | None = None
    ) -> list[MemoryItem]:
        """Top-``k`` most similar solved tasks.

        ``exclude_task_ids`` must always contain the query task: retrieving a
        task's own solution is leakage, not memory.
        """
        excluded = exclude_task_ids or set()
        query_tokens = tokenize(query)
        scored = [
            (self.score(query_tokens, i), i)
            for i, item in enumerate(self.items)
            if item.task_id not in excluded
        ]
        scored.sort(key=lambda si: (-si[0], self.items[si[1]].task_id))
        return [self.items[i] for score, i in scored[:k] if score > 0]

    def random_items(
        self, *, k: int = 2, exclude_task_ids: set[str] | None = None, seed: int = 0
    ) -> list[MemoryItem]:
        """``k`` arbitrary solved tasks — the relevance control.

        Same count, same format, same kind of content as ``retrieve``; only
        the relevance differs, so the contrast isolates retrieval quality
        rather than the presence of examples.
        """
        excluded = exclude_task_ids or set()
        pool = [i for i in self.items if i.task_id not in excluded]
        if not pool:
            return []
        rng = random.Random(seed)
        return rng.sample(pool, min(k, len(pool)))
