# ghosting_precision

Labeled examples for **Phase 7** ghost-job detector v1 (`implementation-plan.md` §Phase 7).

## Purpose

Evaluate rule-based ghost scoring for identifying stale, evergreen, or suspicious listings without excessive false positives on good active jobs.

## Contents

| File | Description |
|---|---|
| `examples.jsonl` | 10 labeled examples with explicit signals and ground-truth category |

## Sampling method

Synthetic but realistic examples derived from ATS + aggregator patterns seen in Greenhouse/Lever/Ashby fixtures and real job data.
Covers:
- Primary ATS active jobs (should score low)
- Old secondary reposts without primary confirmation (high ghost)
- Stale postings (old posted_at, no updates)
- Suspicious evergreen (same text reposted for months)
- Borderline cases

## Label definitions

- `active-good`: Legitimate current opening from primary or well-confirmed source. Should not be penalized.
- `stale`: Posting clearly expired (old date + no activity, broken apply).
- `suspicious_evergreen`: Repeatedly reposted identical text over long period, typical of low-quality boards or ghost farms.
- `unclear`: Mixed signals; system should downrank rather than hide.

Each example includes:
- `signals`: list of observed ghost signals (from spec)
- `ghost_label`: one of the 4 categories
- `notes`

## Ghost signals (v1 catalog)

From `docs/specs/source-validation-and-ghost-signals.md`:
- `apply_link_missing`
- `apply_link_broken`
- `secondary_source_only`
- `no_confirmed_primary_source`
- `stale_secondary_listing`
- `freshness_mismatch`
- `old_posting_age`
- `repost_pattern`

## Grading

See `evals/rubrics/ghosting_precision.md`

Primary metrics:
- False positive rate on `active-good` jobs (critical)
- Catch rate on `stale` + `suspicious_evergreen`
- Policy: default to downrank if FP rate on good jobs > 10%

## Running

```bash
pytest tests/unit/test_ghosting.py -q
```

## Exit gate (Phase 7)

Per `evals/suites/ghosting_precision.yaml`:
- FP rate on active-good ≤ 0.15 (with downrank policy)
- Catch rate on clear ghosts ≥ 0.60
- All ghost decisions produce explicit reason lists
