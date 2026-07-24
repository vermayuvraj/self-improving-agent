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

## Compiled Overleaf projects (live)

Both variants are built, uploaded and compiling cleanly (0 errors):

| Variant | Overleaf | Pages | Notes |
|---|---|---|---|
| Initial submission | [`6a631e92…`](https://www.overleaf.com/project/6a631e921fac79ee11d04552) | 6 | Anonymized ("Anonymous Authors"); no acknowledgements or repo link, per ICML double-blind rules |
| Camera-ready | [`6a631f7a…`](https://www.overleaf.com/project/6a631f7ae5812294b6cfb379) | 6 | De-anonymized; Impact Statement, Acknowledgements (incl. AI-assistance disclosure), code link |

Rebuild the zips from source with `scripts/build_submission.ps1`; the built
`submission/*.zip` are committed so they can be re-imported directly.

**Known benign warning.** hyperref reports "Token not allowed in a PDF string"
for the `\\` line break in the title; this affects only the PDF metadata
string, not the rendered paper, and is common in ICML submissions.

## ICML 2026 compliance notes

- **Page limits.** 8 pages of body for the initial submission, 9 for
  camera-ready; references, acknowledgements, impact statement and appendices
  are excluded. Both builds are well inside the limit.
- **Anonymity.** The `icml2026` package suppresses the author block unless
  `[accepted]` is passed, so the initial project is anonymous by construction.
  Acknowledgements and the repository URL appear only in the camera-ready.
- **Generative-AI policy.** ICML permits LLM assistance in writing and
  research but holds authors fully responsible for all content, forbids
  listing an LLM as an author, and prohibits plagiarism and prompt injection.
  There is no numeric "AI-detection" threshold. The camera-ready includes an
  explicit disclosure of AI assistance; the author retains responsibility.
- **Originality.** All prose is written from this project's own experiments;
  related work is summarized rather than quoted, and every number derives from
  a recorded run manifest and replayable trace.

## Compiling elsewhere

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
