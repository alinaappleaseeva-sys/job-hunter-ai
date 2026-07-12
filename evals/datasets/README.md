# Evaluation Datasets

Store curated examples here.

## Dataset groups

| Directory | Phase | Status |
|---|---|---|
| `ingestion/` | 2–3 | planned (connector smoke) |
| **`normalization_gold/`** | **4** | **active — 16 labeled examples** |
| `dedup/` | 5 | planned (`dedup_regression`) |
| `ranking/` | 6 | planned |
| `ghosting/` | 7 | planned |

## Active datasets

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
4. Never delete labeled rows without recording reason in dataset README changelog.