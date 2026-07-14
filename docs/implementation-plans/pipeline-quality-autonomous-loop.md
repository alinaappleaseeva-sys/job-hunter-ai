# Implementation Plan: Pipeline Quality & Coverage — Autonomous Improvement Loop

**Version**: v1.1 (2026-07-14)  
**Owner**: Hermes Agent (autonomous) + Alina (steering & final review)  
**Status**: Active — Refining based on feedback  
**Current Phase**: Phase 0 (Sample Hygiene) + early Phase 1 (Role Family + Requirements)  
**Blockers**: None  
**Next Milestone**: First autonomous review after Phase 1 core quality PRs land  

**Related Documents** (cross-links):
- [CV Tailoring Pipeline Plan](../cv-tailoring-pipeline.md) (handover target once we have ≥15 good roles)
- [Phase 5 Verification Lessons](../../docs/decisions/phase-5-verification-lessons.md)
- [Main Job Aggregator & Ranking Plan](../../docs/architecture/implementation-plan.md)
- [Sources Expansion Plan](../../docs/architecture/implementation-plan-sources.md)
- This plan takes precedence for the quality-first loop

**Metrics Dashboard** (to be populated):
- `reports/telemetry_*.json` (per-source breakdown)
- `evals/runs/autonomous_review_*.md`
- Simple Markdown summary generated after each full run

---

## 1. North Star & Quantitative Goals

**Goal**: After a single clean pipeline run, reliably surface **≥15 truly good roles** that pass a strict rubric (see below). The top of the list must be mostly signal, not noise.

**Quantitative Success Criteria (overall)**
- ≥15 roles pass the full "Truly Good Role" rubric in one run.
- Top-10 average role_fit ≥ 0.80 (or configured threshold).
- Target source contribution in the good set ≥ 40% from non-Stripe/Coinbase sources (after first batches).
- False positive rate in top-20 ≤ 20% (agent review).
- No sample/fake data in top-30 of production-style runs.

---

## 2. "Truly Good Role" Rubric (Explicit & Measurable)

A role is **truly good** only if it passes **all** Must-Have criteria. Nice-to-have items increase confidence but are not required for the count.

### Must-Have (all required)
| Criterion                    | Definition / Threshold                                                                 | How Measured                          | Example Pass                          | Example Fail                          |
|------------------------------|----------------------------------------------------------------------------------------|---------------------------------------|---------------------------------------|---------------------------------------|
| **Title / Role Family**     | Senior/Head/Lead/Program Manager level in target family (Head of Ops, Chief of Staff, DAO Ops, DAO Program Manager, Governance Ops, Treasury Ops, etc.) | `infer_role_family` + title keywords | "Head of Operations", "DAO Program Manager", "Chief of Staff - Web3" | "Accounting Manager, GL Operations", "Junior Ops Associate" |
| **No Hard Credential Mismatch** | Does not require CPA, Big 4, public accounting, SOX 404, U.S. GAAP as hard requirement | `requirements.py` extraction + penalty | No mention or "nice to have" only    | "CPA with 6+ years... Big 4 preferred... SOX 404" |
| **Market / Domain Bias**    | Web3, crypto, blockchain, DAO, or strong fintech/ops-adjacent where user's background applies | Market tags + company + description  | "DAO Treasury Ops at Protocol X"     | Traditional bank accounting ops       |
| **Recency**                 | Posted within hard cutoff (default 40 days)                                           | Recency filter in pipeline           | 12 days ago                          | 47 days ago                           |
| **Role Fit Score**          | role_fit ≥ 0.70 (or configured threshold) + clear explanation in breakdown            | Ranking breakdown                    | role_fit=0.92 with "title + family + priority boost" | role_fit=0.45 "weak role signal"     |
| **Seniority / Scope**       | Senior+ scope (leading ops, building processes, cross-functional, 0→1 work)          | Seniority field + description parse  | "Lead operations for DAO contributor program" | Pure executional "ops coordinator"   |

### Nice-to-Have (boost confidence)
- Compensation signal present and reasonable.
- Equity mentioned (web3 typical).
- Remote / location-independent.
- Explicit mention of governance, treasury, contributor programs, working groups.
- Company in user's preferred list or strong web3 signal.

**Autonomous Review Rule**: Agent must log 1-2 sentence rationale for every borderline role. Conservative default — when in doubt, mark as not-good.

---

## 3. Phased Execution with Quantitative Exit Criteria

### Phase 0: Sample Hygiene (Quantitative Exit)
- **Action**: Audit + neutralize every `load_sample_*` across all connectors.
- **Exit Criteria**:
  - 0 target-like roles ("Head of Operations", "DAO Operations", "Program Manager - Crypto") in any sample file.
  - Post-clean pipeline run: 0 sample-origin jobs in top-30.
  - All samples have clear comment: `# FALLBACK ONLY — Phase 0 hygiene`.

**Status**: In progress (Wellfound, WeWorkRemotely, ArcDev, Workable cleaned in first PRs).

### Phase 1: Core Quality — Role Family + Hard Requirements (Quantitative Exit)
- **Actions**:
  - Negative rules + precision in `infer_role_family` (finance_ops for accounting roles).
  - Hard requirements extraction module.
  - Mismatch penalty in ranking (tunable weight).
- **Exit Criteria**:
  - "Accounting Manager, GL Operations" (or equivalent) returns `role_family="finance_ops"` and triggers requirements penalty ≤ 0.3.
  - Role_fit for the exact Coinbase example drops below 0.5.
  - New component visible in score breakdowns.

### Phase 2: Ranking Controls & Observability (Quantitative Exit)
- Feature flags / config toggles for: `role_family`, `hard_requirements`, `recency_soft_downrank`, `penalty_*`.
- Tunable recency (hard_max + soft downrank 30-40d).
- Per-source telemetry in every run.
- **Exit Criteria**:
  - Can toggle any component via config without code change.
  - Every run produces `per_source` breakdown in telemetry (volume, target_ratio, error_rate, top-k good count).

### Phase 3+: Source Batches (max 4 per batch)
- Before adding any batch: compute **Source Health Score**.
- **Source Health Score** (0-1): `ingestion_success_rate * target_hit_rate * (1 - error_rate)`.
- Add only if health score ≥ 0.6 (or document exception).
- After adding batch + run: autonomous review.
- **Exit per batch**: At least 2-3 new good roles from the new sources, or clear documentation why not.

**Overall Loop Exit**:
- One clean run produces ≥15 roles that pass the full rubric.
- Agent confidence high (documented in review log).
- Handover criteria to CV tailoring met (see Post-Merge).

---

## 4. Autonomous Review Protocol (LLM-as-Judge + Human Spot-Check)

**Process** (agent executes after every meaningful run):

1. Run pipeline (or use latest telemetry + full job data).
2. Take top 25-40 roles.
3. For each role, score against the explicit rubric (LLM-as-judge using the table above).
4. Produce structured output:
   - Count of truly good roles.
   - List of good roles with short justification.
   - Near-misses + failing criterion.
   - Per-source contribution.
5. **Human spot-check**: Random sample 10-20% of the reviewed set (or top-10) is flagged for Alina review.
6. Log to `evals/runs/autonomous_review_YYYYMMDD_HHMM.md` (or append to telemetry).
7. Decision:
   - ≥15 good → Surface summary + list to user.
   - 8-14 good → One more quality pass or next source batch.
   - <8 → Prioritize quality, do not add volume.

**LLM-as-Judge Prompt Skeleton** (to be versioned):
"Using the following rubric [paste table], evaluate this job for Alina (Head of Ops Web3/DAO). Must pass all Must-Have. Output: pass/fail + 1 sentence reason per criterion + overall verdict."

---

## 5. Pipeline & Automation Improvements

### Configurability (to be implemented)
- `source_config.yaml`:
  ```yaml
  rate_limits:
    wellfound: {requests_per_min: 10, backoff: 2}
    greenhouse: {requests_per_min: 30}
    telegram: {requests_per_min: 5}
  recency:
    hard_max_age_days: 40
    soft_downrank_start_days: 30
    soft_downrank_factor: 0.7
  ranking_toggles:
    use_hard_requirements: true
    use_role_family_negatives: true
    recency_soft: true
  ```
- Feature flags / config-driven toggles for all major ranking components (easy A/B and rollback).

### Telemetry
- Every run must emit per-source breakdown:
  - volume, target_ratio, error_rate, top_k_good_count, avg_role_fit
- Generate simple Markdown summary (`reports/summary_*.md`) or basic HTML dashboard.
- Deduplication metrics: track false negative merges (jobs that should have been deduped but weren't).

### Recency
- Hard filter (already implemented) + soft downrank for 30-40 days window (configurable).

### CI / Quality Gates
- Add ruff + black + pre-commit (as previously planned).
- Smoke test: `python scripts/run_pipeline_on_cv.py --limit_per_source 3 --max_jobs 20`.
- Run smoke after every PR that touches ingestion or ranking.

---

## 6. Development Process

- Rebase workflow (no merge commits on feature branches).
- Small, reviewable PRs (one logical change).
- Standard PR template: Problem / Solution / Plan / Post-merge action items.
- Before adding a new source batch: calculate and document Source Health Score.
- Use feature flags / config toggles for ranking components.

**ADR Recommendation** (to be created):
- `docs/decisions/adr-001-rebase-small-prs.md` — Why we use rebase + small PRs for this loop (traceability, easy rollback, fast feedback).

---

## 7. Risks & Edge Cases (Expanded)

- **Ghost jobs / fake postings**: Maintain dedicated eval family. Flag jobs with suspicious patterns (very generic text, no company site link, posted date anomalies).
- **Salary handling**: Never fabricate. Undisclosed = neutral. Log when salary is missing.
- **Seasonal / location bias**: Track in per-source telemetry.
- **LLM drift in role_family / requirements**: Periodic gold set re-evaluation (small labeled set of 20-30 jobs). Re-run gold set after major inference changes.
- **Scaling (>1000 raw jobs)**: Add caching, better pagination limits, incremental processing.
- **Over-filtering**: Track "near-miss" roles. If good roles start disappearing, relax specific rules with data.
- **Source health regression**: If a previously good source drops below health threshold, pause it and investigate.

---

## 8. Post-Merge & Handover

- When ≥15 truly good roles achieved in a clean run:
  - Produce final autonomous review log.
  - Update status in this plan.
  - Seamless handover to CV Tailoring Pipeline (use the existing vertical spike work as starting point).
  - Master CV version + golden evals from tailoring plan become the next focus.

- **Monitoring**:
  - After significant runs: commit `reports/summary_*.md` + telemetry.
  - Consider lightweight daily/weekly autonomous summary job (cron or script) that appends to a running log.

---

## 9. Immediate Next Steps (Agent Will Execute Autonomously)

1. Finish Phase 0 sample hygiene (remaining connectors if any) → PR.
2. Land Phase 1 core (role_family negatives + requirements) → PRs already opened.
3. Add basic feature flags / config toggles for ranking components.
4. Implement per-source telemetry + simple Markdown summary.
5. Run full pipeline + first autonomous review (LLM-as-judge + spot-check).
6. Compute Source Health Score for first 4 sources from sources plan.
7. Add first batch of 4 sources only if health is acceptable.
8. Repeat review loop.

All changes via PR. Agent will document decisions in review logs.

---

**This revised plan is now significantly more actionable and measurable.**  
Every phase has quantitative exit criteria. The rubric is explicit. Review protocol includes LLM-as-judge + human spot-check. Traceability, feature flags, source health, and risks are covered.

Ready for your review or for the agent to continue execution on the next micro-step.