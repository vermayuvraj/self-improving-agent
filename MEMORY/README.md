# Project memory

Persistent, deduplicated knowledge that is not derivable from code or git
history. One topic per file; update in place rather than appending duplicates;
delete what turns out to be wrong.

| File | Contents |
|---|---|
| `lessons.md` | Lessons learned (engineering + research), each with date and context |
| `failed-approaches.md` | What we tried that didn't work, and why — saves re-derivation |
| `research-ideas.md` | Unscheduled ideas and RQ candidates not yet in RESEARCH.md |
| `bottlenecks.md` | Known performance/cost bottlenecks and their measurements |
| `bugs.md` | Recurring bug patterns and their root causes |

Architecture decisions live in ARCHITECTURE.md (ADRs), not here. Experiment
results live in EXPERIMENTS.md. Files above are created when the first entry
exists — no empty placeholder files.
