# Phase 10 Operational Hardening datasets

These datasets support source health, Telegram quality/noise, eval regression, and data freshness.

## Datasets

- `source_health.jsonl` — examples of healthy vs degraded sources (fetch success rate, parse quality, freshness)
- `telegram_quality.jsonl` — labeled Telegram messages for noise vs signal (job relevance, duplication, staleness)
- `eval_regression.jsonl` — cases where a code change would regress precision@K or ghost detection

See `evals/suites/phase10_operational.yaml` and rubrics.

Rules:
- New operational logic must be accompanied by updates here.
- Material changes to ranking/ghosting/ingestion require post-change eval summary.