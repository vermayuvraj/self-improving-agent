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

## The three packages

Build all three with `scripts/build_submission.ps1`. Each zip is standalone —
`paper.tex`, `body.tex`, `references.bib`, `figures/` and the ICML style files.

| Zip | For | Author block | Extra sections |
|---|---|---|---|
| `icml2026-initial-submission.zip` | ICML review | **Anonymous** | — |
| `icml2026-camera-ready.zip` | after acceptance | Named + ORCID | Acknowledgements, code link |
| `arxiv-preprint.zip` | arXiv | Named + ORCID | Acknowledgements, code link |

All three share one `body.tex`, so the science can never drift between them;
only the preamble and the trailing sections differ.

**Anonymity is enforced at build time.** The script greps the anonymous
package for `Yuvraj`, `orcid`, `0009-0004` and `vermayuvraj`, and aborts the
build if any appear. A leak here would be a desk reject, so it is checked
mechanically rather than by eye.

### Live Overleaf projects

| Variant | Overleaf | Pages |
|---|---|---|
| Initial submission | [`6a631e92…`](https://www.overleaf.com/project/6a631e921fac79ee11d04552) | 6 |
| Camera-ready | [`6a631f7a…`](https://www.overleaf.com/project/6a631f7ae5812294b6cfb379) | 6 |

These hold an earlier revision; re-upload the current zips (Overleaf → project
→ Upload → overwrite) to refresh them.

## arXiv submission

`arxiv-preprint.zip` uses `\usepackage[preprint]{icml2026}`, which prints real
author names and a footer reading only *"Preprint. \<date\>."* — it makes no
claim of ICML acceptance.

**Policy, which matters here.** ICML permits arXiv preprints, but forbids
advertising a paper as an ICML submission at any time during review, and the
anonymous submission must not link to the preprint. Both constraints are
satisfied: nothing in the preprint mentions ICML, and the anonymous package
contains no repository or preprint link. Do not add "submitted to ICML" to the
arXiv comments field until decisions are announced.

**Steps.** Paste the title, authors, categories and plain-text abstract from
[`submission/ARXIV_METADATA.txt`](submission/ARXIV_METADATA.txt), then upload
`arxiv-preprint.zip`.

### Package layout

Built by `scripts\build_arxiv.ps1`, which **compiles the package locally with
MiKTeX before zipping it** — so what ships is known to build, not assumed to:

```
main.tex          single source file (body.tex inlined at build time)
main.bbl          pre-generated bibliography; arXiv uses it verbatim
refs.bib          retained for reference
figures/*.pdf     vector figures
icml2026.sty      required — see below
icml2026.bst
fancyhdr.sty, algorithm.sty, algorithmic.sty
```

The `.bbl` basename must match the main `.tex` basename, hence
`main.tex`/`main.bbl`. Shipping a pre-built `.bbl` removes any dependence on
arXiv's BibTeX run, the most common cause of arXiv build failures.

**The style files are not optional.** `icml2026.sty` is a 2026 conference
style and is not in TeX Live, which is all arXiv provides. Verified by
removing it and recompiling: `! LaTeX Error: File 'icml2026.sty' not found.`
followed by `! Emergency stop.` — no PDF. It must ship with the source.

**Other arXiv rules observed:** figures are PDF, since arXiv performs no
on-the-fly conversion in pdflatex mode; no `.aux`/`.log`/`.out`/`.blg`/`.pdf`
artifacts are included; and archive entries use forward slashes, because
Windows PowerShell's `Compress-Archive` writes backslashes that Linux
extraction can misread as literal filenames.

`submission/arxiv-preview.pdf` is the locally built PDF — check it before
uploading.

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
