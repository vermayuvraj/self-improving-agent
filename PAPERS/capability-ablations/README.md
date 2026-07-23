# Paper: "Try Again, Don't Look Back"

Placebo-controlled ablation of self-repair in small code models. The headline:
blind resampling beats self-repair at every scale below 7B, because
conditioning on a failed attempt *anchors* the model to a wrong approach.

## Files

| File | What it is |
|---|---|
| `paper.tex` | Full ICML-style draft (all 10 sections, LaTeX math, tables, figure refs) |
| `references.bib` | Bibliography |
| `figures/` | 6 figures, generated from run data — PDF (LaTeX) + PNG (web) |
| `findings.md` | Plain-text results digest with every number |
| `draft.md` | Earlier Markdown scaffold (superseded by `paper.tex`) |

## Compiling

No LaTeX is needed locally. Fastest path is **Overleaf** (free):

1. New Project → Upload Project → drag in `paper.tex`, `references.bib`, and the
   `figures/` folder.
2. For true ICML formatting, add `icml2025.sty` and `icml2025.bst` from the
   official ICML author kit and uncomment the `\usepackage{icml2025}` line.
   As written it compiles with the `article` class so the draft is portable.

Or locally, if you install a TeX distribution (MiKTeX/TeX Live):

```bash
pdflatex paper && bibtex paper && pdflatex paper && pdflatex paper
```

## Regenerating the figures

Figures are computed from `runs/` so they can never disagree with the numbers:

```bash
uv sync --group paper
uv run --group paper python scripts/make_figures.py
```

## The missing arm: frontier model, for $0

The paper's sharpest open question is whether anchoring vanishes at frontier
scale. The harness already speaks the OpenAI-compatible protocol, so this needs
no code — only an endpoint. Two genuinely free options in 2026:

- **Google Gemini** free tier (permanent, no card): 1,500 req/day on
  Gemini Flash. Point the client at Google's OpenAI-compatible endpoint.
- **OpenRouter** free models (IDs ending `:free`, e.g. a large Qwen3-Coder or
  DeepSeek): $0/token, ~20 req/min.

Example (OpenRouter, once `OPENROUTER_API_KEY` is set):

```bash
uv run sia run --bench mbpp+ \
  --model "deepseek/deepseek-r1:free" \
  --base-url "https://openrouter.ai/api/v1" \
  --api-key "$OPENROUTER_API_KEY"
```

Then use that run as the baseline for a repair sweep (`scripts/run_exp004.py`,
swapping in the new baseline id). The free rate limits make an 8-iteration
sweep slow but feasible overnight; MBPP+ is 378 tasks.
