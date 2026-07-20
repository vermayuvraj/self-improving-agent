from __future__ import annotations

import re

_FENCE_RE = re.compile(r"```(\w*)[ \t]*\n(.*?)```", re.DOTALL)


def _clean(code: str) -> str:
    """Trim blank lines and trailing whitespace, preserving indentation.

    A plain ``.strip()`` would delete the leading indent of completion-style
    bodies (e.g. ``    return a + b``), producing invalid Python downstream.
    """
    return code.strip("\r\n").rstrip()


def extract_code(text: str) -> str:
    """Extract the most plausible code payload from model output.

    Preference order: largest ```python fence containing a ``def``, largest
    ```python fence, largest fence of any language, raw text. Small local
    models are inconsistent about fencing, so this must be forgiving.
    """
    blocks = [
        (lang.lower(), _clean(body)) for lang, body in _FENCE_RE.findall(text) if body.strip()
    ]
    python_blocks = [body for lang, body in blocks if lang in ("python", "py", "")]
    with_def = [b for b in python_blocks if "def " in b]
    for candidates in (with_def, python_blocks, [body for _, body in blocks]):
        if candidates:
            return max(candidates, key=len)
    return _clean(text)
