from __future__ import annotations

from sia.agent import SYSTEM_PROMPT
from sia.bench import BenchTask
from sia.llm import Message
from sia.memory.store import MemoryItem

MEMORY_CONDITIONS = ("none", "random", "retrieved")

_PREAMBLE = "Here are solved problems from earlier work, for reference:"


def build_memory_messages(task: BenchTask, exemplars: list[MemoryItem]) -> list[Message]:
    """Prompt for one attempt, optionally preceded by worked exemplars.

    Exemplars come *before* the task so the instruction stays last and the
    model's final context is the problem it must solve — identical framing to
    the baseline prompt, which keeps the arms comparable.
    """
    if not exemplars:
        return [Message("system", SYSTEM_PROMPT), Message("user", task.instruction)]

    parts = [_PREAMBLE, ""]
    for exemplar in exemplars:
        parts += [exemplar.as_exemplar(), ""]
    parts += ["Now solve this problem:", "", task.instruction]
    return [Message("system", SYSTEM_PROMPT), Message("user", "\n".join(parts))]
