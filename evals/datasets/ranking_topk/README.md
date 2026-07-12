# ranking_topk

Labeled examples for **Phase 6** ranking evaluation (`implementation-plan.md` §Phase 6).

## Purpose

Grade whether `CandidateProfile` + list[CanonicalJob] → ranked order surfaces relevant jobs in top-k positions.  
Used to compute top-k precision and to block ranking changes that degrade feed quality.

## Contents

| File | Description |
|---|---|
| `examples.jsonl` | 8 labeled (profile, jobs batch) examples with relevance judgments |

## Sampling method

- Synthetic but realistic profiles and jobs derived from ATS-style normalized data (Greenhouse/Lever/Ashby patterns).
- Covers good matches, seniority mismatches, location/remote preference breaks, salary gaps, role-family drift, market mismatch.
- One negative control with poor profile definition.

## Label definitions

Each example has:
- `profile`: minimal CandidateProfile-like dict (target fields, prefs)
- `jobs`: list of job dicts with key fields from CanonicalJob / Normalized + `relevance_label`
- `relevance_label` per job: one of `highly_relevant | relevant | neutral | irrelevant`
- `notes`: why this judgment

Relevance rules (see rubric):
- `highly_relevant`: strong role + seniority + remote/location + market match, salary in/above band
- `relevant`: good on 2-3 dimensions, acceptable on others
- `neutral`: partial match, usable but not exciting for this profile
- `irrelevant`: clear mismatch on role or hard constraint (e.g. onsite only when profile wants remote)

## Grading

See `evals/rubrics/ranking_topk.md`

Primary metric: precision@k (fraction of top-k that are `relevant` or `highly_relevant`).

## Known biases

- Synthetic: no live user feedback yet.
- English/US-centric.
- Limited salary data (most early examples have null comp; salary-fit weak until more data).
- Profiles are single-tenant for MVP.

## Refresh cadence

- Add new examples when real candidate profiles + labeled outcomes available.
- Re-label after major ranking heuristic changes.
- Target: ≥5 examples per major dimension (role, seniority, geo, salary).

## Running

```bash
pytest tests/unit/test_ranking.py -q -k "topk or gold"
# later: python -m evals.harness.ranking --suite evals/suites/ranking_topk.yaml
```

## Exit gate (Phase 6)

Per `evals/suites/ranking_topk.yaml`:
- precision@3 ≥ 0.60 on the gold set (or documented baseline)
- No regression vs simple chrono baseline on the labeled set
- All explanations contain at least one non-empty reason string for scored components
