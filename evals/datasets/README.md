# Evaluation Datasets

Store curated examples here.

## Dataset groups

| Directory | Phase | Status |
|---|---|---|
| `ingestion/` | 2–3 / 8 | active |
| `normalization_gold/` | 4 | active |
| `dedup_regression/` | 5 / 8 | active |
| `ranking_topk/` | 6 | active |
| `ghosting_precision/` | 7 | active |
| `feedback_actions/` | **9** | **new scaffold** |

## Active datasets

### `feedback_actions/` (Phase 9)
Labeled user actions on RankedJobs.
Must record full trace to score_breakdown, explanations, ghost_score.

**Suite:** `evals/suites/feedback_actions.yaml`
**Rubric:** `evals/rubrics/feedback_traceability.md`

### Other active (see previous)

- `ghosting_precision/`
- `ranking_topk/`
- etc.

## Rules for dataset changes
- **New delivery/feedback logic** → extend `feedback_actions` + re-run traceability gates before merge.
- Never delete labeled rows without changelog.
