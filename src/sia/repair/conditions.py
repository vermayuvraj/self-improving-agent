from __future__ import annotations

from sia.agent import SYSTEM_PROMPT
from sia.bench import BenchTask
from sia.llm import Message

CONDITIONS = ("resample", "placebo", "feedback")

# Shape-matched to the feedback message: same framing, same call to action,
# comparable length — but carrying no information about *what* went wrong.
# If placebo matches feedback, the gain was never in the execution facts.
_PLACEBO_NOTICE = (
    "Your previous solution was incorrect. Review it and write a corrected "
    "version. Respond with the complete solution in a single ```python code "
    "block. No explanations."
)

_FEEDBACK_NOTICE = (
    "Your previous solution was incorrect. The failing test output is shown "
    "below. Review it and write a corrected version. Respond with the "
    "complete solution in a single ```python code block. No explanations."
)

MAX_FEEDBACK_CHARS = 1500


def summarize_failure(stdout: str, stderr: str, *, timed_out: bool) -> str:
    """Condense execution output into the facts a repair attempt can use.

    Truncates from the *front* of long tracebacks: the final frames and the
    assertion carry the diagnosis, and on a 4096-token context an untruncated
    dump would crowd out the code itself.
    """
    if timed_out:
        return "The solution timed out (likely an infinite loop or non-terminating recursion)."
    combined = "\n".join(part.strip() for part in (stdout, stderr) if part.strip())
    if not combined:
        return "The solution failed with no output."
    if len(combined) > MAX_FEEDBACK_CHARS:
        combined = "...[earlier output truncated]\n" + combined[-MAX_FEEDBACK_CHARS:]
    return combined


def build_retry_messages(
    task: BenchTask,
    condition: str,
    *,
    previous_code: str,
    failure: str,
) -> list[Message]:
    """Messages for one retry attempt under ``condition``.

    All conditions receive the original task instruction, so the model is
    never handicapped relative to the baseline — the arms differ only in what
    is added after it.
    """
    if condition not in CONDITIONS:
        raise ValueError(f"unknown repair condition: {condition!r}")

    if condition == "resample":
        # Identical to the first attempt. Any gain here is the value of
        # another draw, not of feedback.
        return [Message("system", SYSTEM_PROMPT), Message("user", task.instruction)]

    notice = _PLACEBO_NOTICE if condition == "placebo" else _FEEDBACK_NOTICE
    parts = [
        task.instruction,
        "",
        "Your previous attempt:",
        "",
        "```python",
        previous_code,
        "```",
        "",
    ]
    if condition == "feedback":
        parts += ["Test output:", "", "```", failure, "```", ""]
    parts.append(notice)
    return [Message("system", SYSTEM_PROMPT), Message("user", "\n".join(parts))]
