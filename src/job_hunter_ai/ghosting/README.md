# Ghosting

Ghost-job detection v1 is rule-based and fully explainable.

## Public functions
- `compute_ghost_score(job) -> (score, reasons)`
- `decide_visibility(score, reasons) -> (action, reason)`
- `apply_ghost_penalty(ranked_jobs)` — adjusts RankedJob.total_score and attaches ghost_score + explanation

## Signals (v1)
See `evals/rubrics/ghosting_precision.md` and `docs/specs/source-validation-and-ghost-signals.md`.

Policy prefers downrank over hide when uncertainty exists.

## Integration
Call after ranking or before delivery. The penalty is multiplicative on total_score.