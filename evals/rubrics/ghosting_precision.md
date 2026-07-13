# Ghosting precision rubric (Phase 7 v1)

Grading for `ghosting_precision` dataset and suite.

## Goals
- Penalize clearly stale or ghost-like jobs.
- Avoid hiding too many `active-good` jobs.
- Every decision must be explainable (list of active signals + reasons).

## Categories (ground truth)

| Label | Meaning | Expected action |
|-------|---------|-----------------|
| active-good | Real, currently open role from trustworthy source | show or normal rank |
| stale | Expired, broken apply, no recent activity | hide or strong downrank |
| suspicious_evergreen | Reposted identical content for long time with no confirmation | downrank + flag |
| unclear | Mixed signals | downrank only, never hide |

## Signals catalog (v1)

Explicit signals we detect and log (see spec):
- `apply_link_missing`
- `apply_link_broken`
- `apply_link_redirects_to_non_job_page`
- `secondary_source_only`
- `no_confirmed_primary_source`
- `stale_secondary_listing`
- `freshness_mismatch_between_sources`
- `old_posting_age` (> 90 days)
- `repost_pattern`

**Rule for scoring (v1 heuristic):**
ghost_score = min(1.0, sum(weight for active_signal))

Base weights (from spec, slightly simplified):
- apply_link_broken: 0.35
- apply_link_missing / redirects_to_non_job: 0.25-0.30
- secondary_source_only + no_confirmed_primary: 0.25
- stale_secondary_listing: 0.20
- old_posting_age: 0.15
- repost_pattern: 0.15
- freshness_mismatch: 0.10

## Decision policy (MVP)

- ghost_score < 0.3 → normal (show)
- 0.3 ≤ ghost_score < 0.6 → downrank (reduce ranking score by 30-50%)
- ghost_score ≥ 0.6 → hide (or require manual review)

**Critical gate**: If false-positive rate on `active-good` exceeds 15%, fall back to **downrank only** (never hide good jobs).

## Metrics

- FP rate on active-good = (active-good jobs with ghost_score ≥ 0.3) / total active-good
- Catch rate on ghosts = (stale + suspicious_evergreen with ghost_score ≥ 0.5) / total ghosts
- Explanation coverage: 100% of non-zero scores must have ≥1 reason string

## Regression policy

- Block if FP rate on active-good > 0.15 when using hide
- Warn if catch rate on clear ghosts drops >10% vs previous run
- Any change to signals or weights must add or update at least 2 gold examples
