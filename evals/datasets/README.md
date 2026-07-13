# Evaluation Datasets

Store curated examples here.

## Dataset groups

| Directory | Phase | Status |
|---|---|---|
| `ingestion/` | 2–3 / 8 | **active for smoke (Phase 8)** |
| **`normalization_gold/`** | **4** | **active — 16 labeled examples** |
| `dedup/` | 5 / 8 | **active — cross-family regression** |
| **`ranking_topk/`** | **6** | **active — 8 labeled examples** |
| **`ghosting_precision/`** | **7** | **active — 10 labeled examples** |

## Active datasets

### `ingestion/`
Source-specific smoke checks for new boards and Telegram (Phase 8).
See `ingestion/README.md`.

### `dedup_regression/`
Must-merge / must-not-merge including cross-family (ATS + boards + Telegram).
See `dedup_regression/README.md` and examples.

**Suite:** `evals/suites/dedup_regression.yaml` (to be added)

### `ghosting_precision/`
... (existing)

### `ranking_topk/`
... (existing)

### `normalization_gold/`
... (existing)

## Rules for dataset changes

1. **New connector** → extend gold set with ≥3 representative postings + ingestion smoke before rollout.
2. **Cross-family dedup** → add to dedup_regression.
3. **Ranking or ghost change after expansion** → re-run ranking_topk and ghosting_precision.
4. Never delete without changelog.
