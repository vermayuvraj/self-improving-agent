"""Experience memory (M5): learn across tasks, not within one.

EXP-004/005 showed that conditioning on the model's *own failed attempt*
costs accuracy via anchoring. This module tests the complementary question:
does experience from *other, solved* tasks help — and is any gain from the
relevance of what is retrieved, or merely from having worked examples at all?

The decomposition mirrors the repair conditions:

    none       original prompt                     — baseline
    random     + k solved exemplars, random        — value of any examples
    retrieved  + k solved exemplars, most similar  — value of relevance

``none → random`` isolates the few-shot effect; ``random → retrieved``
isolates the retrieval effect. Both arms carry identical structure and
comparable length, so a difference between them cannot be a prompt-length
artifact.
"""

from sia.memory.prompt import MEMORY_CONDITIONS, build_memory_messages
from sia.memory.retrieve import Retriever
from sia.memory.store import MemoryItem, MemoryStore, mine_from_runs

__all__ = [
    "MEMORY_CONDITIONS",
    "MemoryItem",
    "MemoryStore",
    "Retriever",
    "build_memory_messages",
    "mine_from_runs",
]
