# normalization_gold

Labeled examples for **Phase 4** normalization evals (`implementation-plan.md` §Phase 4).

## Purpose

Grade whether `RawSourceRecord` → `NormalizedJobPosting` extraction is correct at the field level before we trust ranking or dedup downstream.

## Contents

| File | Description |
|---|---|
| `examples.jsonl` | 16 labeled examples (15 from live fixtures + 1 synthetic negative) |

## Sampling method

- **Greenhouse** (5): `tests/fixtures/greenhouse/greenhouse_job_board.json` — Stripe board, indices 0, 1, 3, 4, 13
- **Lever** (5): `tests/fixtures/lever/leverdemo.json` — indices 0–4 (includes hybrid, missing location, remote)
- **Ashby** (5): `tests/fixtures/ashby/ashby_job_board.json` — indices 0–3, 10
- **Synthetic** (1): `norm-syn-001` — malformed payload injected inline (no fixture)

Examples reference fixtures by `fixture_ref` + `fixture_index` so payloads are not duplicated in the dataset.

## Label definitions

Each example has a `labels` object with expected normalized fields per `docs/specs/canonical-job-schema.md`:

| Field | Label meaning |
|---|---|
| `title_normalized` | Lowercased, trimmed title after cleanup |
| `company_name` | Display company (board slug when ATS omits company) |
| `company_domain` | Best-effort domain from `source_url` or known provider |
| `location_*` | Structured location when inferable; `null` when not |
| `remote_mode` | `remote`, `hybrid`, `onsite`, `unknown` |
| `employment_type` | `full-time`, `contract`, etc.; `null` when source omits |
| `seniority` | `junior`, `mid`, `senior`, `lead`, `head`, `unknown`, or `null` |
| `role_family` | `product`, `engineering`, `design`, `sales`, etc. |
| `market` | `saas`, `fintech`, etc. when inferable |
| `compensation_*` | Parsed salary; `null` when absent (most fixture rows) |
| `posted_at` | ISO-8601 when source provides a trustworthy timestamp |
| `parse_status` | `parsed`, `partial`, or `failed` |
| `parse_warnings` | Expected warning tokens (e.g. `employment_type_missing`) |

## Grading modes (`grading` per field)

See `evals/rubrics/normalization_field_checks.md` for full definitions:

- `exact` — string equality (case-sensitive unless noted)
- `enum` — value in allowed set
- `absent` — field must be `null`
- `present` — field must be non-null
- `contains` — substring match (multi-location strings)

## Known biases

1. **English-heavy titles** — fixtures are US/EU-centric ATS boards.
2. **Compensation** — most examples label `compensation_*` as `null` even when Ashby exposes tiers; salary parsing is a later sub-task.
3. **Greenhouse employment_type** — always missing on Board API; labeled `partial` + warning.
4. **Company name** — Lever uses site slug (`leverdemo`) as company proxy.
5. **Enrichment heuristics** — `seniority`, `role_family`, `market` labels reflect v1 keyword rules; may change.

## Refresh cadence

- Re-record fixtures when a connector changes or source schema drifts.
- Re-label affected `example_id` rows after mapper changes.
- Target: review dataset after every normalization PR that touches field extractors.

## Running (once harness exists — Step 4.5)

```bash
pytest tests/unit/test_normalization_gold.py -q
# or: python -m evals.harness.normalization --suite evals/suites/normalization_v1.yaml
```

## Exit gate (Phase 4)

Per `evals/suites/normalization_v1.yaml`:

- `title_normalized` accuracy ≥ 90%
- `company_name` accuracy ≥ 90%
- `location_raw` accuracy ≥ 85%
- `remote_mode` accuracy ≥ 80%
- `parse_status` accuracy ≥ 95%
- No regression on synthetic negative (`norm-syn-001` must stay `failed`)