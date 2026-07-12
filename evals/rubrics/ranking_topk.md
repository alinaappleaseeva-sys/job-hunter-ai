# Ranking top-k rubric

Grading criteria for the `ranking_topk` dataset and `ranking_topk` suite.

Aligned with:
- `implementation-plan.md` §Phase 6
- Explainable heuristics before models
- top-k precision over subjective feel

## 1. What we grade

For each gold example we run:

```python
ranked = rank_jobs(profile, jobs)  # returns list sorted by score desc + explanations
top_k = ranked[:k]
```

Then measure:

- precision@k = (number of jobs in top_k whose relevance_label in {"highly_relevant", "relevant"}) / k
- Has explanations: every scored component in breakdown must have at least one human-readable reason

Primary gates use k=3 (top of feed matters most for MVP inbox/digest).

## 2. Relevance labels (ground truth)

| Label | Definition for this profile | Example signals |
|-------|-----------------------------|-----------------|
| highly_relevant | Strong match across role family, seniority band, remote/location pref, and salary band (if specified) | exact title keywords + seniority + remote + salary >= min |
| relevant | Good on core dimensions (role or seniority) but weak on 1 hard constraint (e.g. salary low, hybrid instead of remote) | role match but seniority off by 1 band or geo slight mismatch |
| neutral | Partial / tangential match; usable but not prioritized | right family but wrong sub-role or low salary + wrong geo |
| irrelevant | Clear mismatch on role family or hard filter violation | sales for eng profile; onsite only when remote required; junior for senior target |

Labels are per (profile, job) pair. The same job can be highly_relevant for one profile and irrelevant for another.

## 3. Scoring components (v1 heuristics)

Ranking v1 produces breakdown + explanations for:

- role_fit (title keywords, role_family overlap)
- seniority_fit
- location_remote_fit
- salary_fit (if compensation present in job and profile has min)
- market_fit (optional)

Each component 0.0–1.0 ; total_score = weighted sum or simple average for v1.

**Explainability requirement:** 
- If a component contributes, explanation list must contain a non-empty string describing the signal used (e.g. "title matches 'backend engineer' keyword; role_family=engineering in target list")
- Empty explanations or "no reason" count as eval failure for that example.

## 4. Gates (see suite yaml)

- precision@3 ≥ 0.60 (baseline target for first impl; will tighten)
- At least 80% of top-3 jobs across examples have non-empty explanations
- Compare vs naive baseline (e.g. posted_at desc or no-op sort) and show improvement or no regression on the labeled set

## 5. Baseline comparison

Every ranking PR must report (via test output or report):

- precision@3 on gold for new ranker
- precision@3 for chrono baseline (sort by canonical_posted_at desc, tiebreak by id)
- delta

If new logic drops below baseline on the gold set, gate fails unless justified with new labels.

## 6. Acceptable fallbacks

- Unknown seniority in job or profile → treat as neutral (0.5)
- Missing compensation → salary_fit = 0.7 (neutral, do not penalize hard)
- "any" remote pref in profile → location_remote_fit always high (0.9+)
- Empty keywords in profile → role_fit falls back to role_family match only; log warning

## 7. Regression policy

- **Block merge** if precision@3 gate in suite fails or explanations missing.
- **Warn** if any component accuracy (by label correlation) drops >10% vs previous run.
- Changes to weights or heuristics require at least one new gold example demonstrating the intended effect.

## 8. Future

Later versions will add:
- graded relevance (0-3 score instead of 4 buckets)
- human feedback labels from delivery layer
- multi-profile AB tests
- learned weights (only after strong heuristic baseline + evals prove value)
