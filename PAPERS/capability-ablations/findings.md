# Paper 1 — accumulated findings

Working title: **"Try Again, Don't Look Back: Blind Resampling Outperforms
Self-Repair in Small Code Models."**

## The claim

At 1.5B–7B on MBPP+, conditioning a retry on the model's own failed attempt —
with or without execution feedback — is **worse** than simply resampling the
original prompt, at roughly half the token cost. The mechanism is anchoring.

## Result 1 — the placebo control reverses the expected conclusion (EXP-004)

pass@1 at k=8, MBPP+ (n=378), Holm-corrected paired contrasts:

| Contrast | 1.5B | 3B | 7B |
|---|---|---|---|
| feedback − placebo | +0.000 (p=1.00) | +0.026 (p=0.49) | +0.008 (p=1.00) |
| placebo − resample | **−0.061** (p=0.003) | **−0.069** (p=0.0006) | −0.019 (p=0.99) |
| feedback − resample | **−0.061** (p=0.004) | **−0.042** (p=0.042) | −0.011 (p=1.00) |

Token cost at 1.5B: resample 63k, placebo 90k, feedback 129k. The winning arm
is the cheapest — no trade-off to navigate.

**Why this matters methodologically.** A study comparing *feedback vs
no-repair* sees +12.2 pp at 1.5B and concludes repair works. The
blind-resampling control shows all of that gain, and more, is available from
retrying alone.

## Result 2 — anchoring is the mechanism (EXP-005)

Mean similarity between consecutive attempts (1.0 = identical):

| Model | resample | placebo | feedback |
|---|---|---|---|
| 1.5B | 0.509 | 0.828 | 0.862 |
| 3B | 0.418 | 0.756 | 0.795 |
| 7B | 0.607 | 0.911 | 0.914 |

Shown its own code, the model regenerates a near-identical solution 33–68% of
the time, versus 2–14% blind.

**The scale story.** Anchoring strength is ~constant across scale
(+0.30–0.38); its *cost* falls with scale because a larger model's failed
first attempt is a better thing to anchor on. The shrinking penalty at 7B is
not feedback becoming useful — it is anchoring becoming cheap.

## Result 3 — the knee is early (EXP-004, H4)

46–53% of all attainable gain arrives by k=2 at every scale; marginal gain
decays to ≈0 by k=7. Practical implication: iteration budgets beyond ~2–3 buy
little regardless of condition.

## Position in the literature

- arXiv:2606.31511 (0.5–1.5B, placebo-controlled) reports feedback content
  beating generic placebos. We find that contrast **indistinguishable from
  zero** at 1.5B–7B, and add the blind-resampling comparison that reverses
  the practical conclusion.
- arXiv:2606.26978 (frontier, repo-level) reports execution worth 1.25 pp
  (n.s.). Our 7B row is consistent (−1.1 pp, n.s.); our small-model rows show
  it is actively *harmful* below that scale — a regime that paper does not
  cover.

## Figures to produce

1. k-curves, 3×3 panel (model × condition) — data in `experiments/EXP-004/`
2. Forest plot of the nine Holm-corrected contrasts with CIs
3. Similarity distributions per condition (anchoring)
4. Pass rate vs cumulative tokens — shows resample dominating on both axes

## Threats already checked

- Budget exhaustion: 0.0% across all 8,082 responses.
- Unequal token spend: favours the losing arms, so cannot explain the result.
- Test leakage via feedback: would inflate feedback, which lost.
- Greedy-decoding artifact: caught pre-run; all retries sample at T=0.8.

## Open

- Does the result hold on HumanEval+ (secondary, underpowered here)?
- Does it hold at frontier scale, where anchoring should be nearly free?
- Does *other-task* retrieved experience (M5) escape the anchoring trap that
  own-attempt context falls into? That is now the sharpest remaining question.
