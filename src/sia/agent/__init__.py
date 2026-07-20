"""Agents. M1 ships the single-shot baseline (ADR-0005: capabilities are
added as toggles on top of a measured baseline; the tool-using loop arrives
with M3's repair module, where it is first needed)."""

from sia.agent.single_shot import SYSTEM_PROMPT, solve_single_shot

__all__ = ["SYSTEM_PROMPT", "solve_single_shot"]
