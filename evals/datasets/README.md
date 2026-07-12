# Evaluation Datasets

Store curated examples here.

## Dataset groups

| Directory | Phase | Status |
|---|---|---|
| `ingestion/` | 2–3 | planned (connector smoke) |
| **`normalization_gold/`** | **4** | **active — 16 labeled examples** |
| `dedup/` | 5 | planned (`dedup_regression`) |
| **`ranking_topk/`** | **6** | **active — 8 labeled examples** |
| `ghosting/` | 7 | planned |

## Active datasets

### `ranking_topk/`

Labeled (profile + jobs batch) examples for **Phase 6** ranking v1.  
Top-k precision and relevance judgments for one candidate profile.  
See `ranking_topk/README.md` for sampling, biases, and refresh policy.

**Suite:** `evals/suites/ranking_topk.yaml`  
**Rubric:** `evals/rubrics/ranking_topk.md`

### `normalization_gold/`

Field-level gold labels for ATS normalization (Greenhouse, Lever, Ashby).  
See `normalization_gold/README.md` for sampling, biases, and refresh policy.

**Suite:** `evals/suites/normalization_v1.yaml`  
**Rubric:** `evals/rubrics/normalization_field_checks.md`

## Each dataset should document

- source and sampling method
- label definitions
- known biases
- refresh cadence

## Rules for dataset changes

1. **Normalization mapper change** → update `normalization_gold` labels or add examples in the same PR.
2. **New connector** → extend gold set with ≥3 representative postings before rollout.
3. **Dedup rule change** → update `dedup_regression` must-merge / must-not-merge pairs (Phase 5).
4. **Ranking heuristic or profile model change** → extend or relabel `ranking_topk` examples; PR must show precision@3 / baseline comparison before merge.
5. Never delete labeled rows without recording reason in dataset README changelog.
