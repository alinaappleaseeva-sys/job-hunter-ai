# Implementation Plan: Job Aggregator & Ranking Improvements (Web3 Head of Ops / CoS)

**Date**: 2026-07-13  
**Owner**: Alina + Hermes Agent  
**Related**: `source-inventory.md`, `implementation-plan-sources.md`, personal CV profile work, evals/

---

## Problem

Current job search pipeline produces low-quality top results for the target profile (Alina Aseeva — Head of Operations with deep Web3/DAO/DeFi background):

- Top-ranked jobs are mostly irrelevant (virtual assistants, sales, generic "hr assistant", non-ops roles).
- Hardcoded `min_compensation=140000` is applied even to jobs that do not list salary. Many real postings do not publish compensation.
- Role fit signals for high-priority titles (**Head of Operations**, **Chief of Staff**, program/governance ops) are weak.
- Source coverage is too narrow. Only a small subset of implemented connectors (mainly RemoteOK + a few Telegram channels) are actually used in `fetch_all_wave1()`. High-volume real ATS connectors (Greenhouse, Lever, Ashby) exist but are not exercised for this profile.
- Resulting volume is too low to surface the expected "hundreds" of relevant senior/head web3 (and adjacent fintech/security/AI-web3) roles.
- Two slightly different profile definitions and several crude parsing heuristics make the system fragile and hard to tune.
- No explicit metrics or automated gates per phase; no robust automation/observability for repeated runs (important for Hermes-driven workflows).

The current output does not match the desired experience: **hundreds of open senior/head web3 roles visible, with strong role fit for Head of Ops / CoS ranked at the top**.

---

## Solution

Create a focused, evaluable improvement cycle for the aggregator + ranking layer:

1. Fix salary handling (no fabrication of 140k, lower threshold to 120k, treat undisclosed as neutral/soft signal).
2. Strengthen role fit and prioritization for **Head of Operations** and **Chief of Staff**.
3. Expand the sources actually called in the main pipeline (add Greenhouse/Lever/Ashby with curated web3-relevant boards + more Telegram channels) in a robust way.
4. Improve title/description parsing for role, market, and seniority (including embedding/LLM options where available).
5. Tune ranking weights (make configurable) and add explicit boosts for target titles.
6. Unblock full pipeline execution and add metrics + automation.
7. Deliver an updated HTML report and before/after comparisons so the user can see the difference.

All changes must preserve the repository principles (evals-first, measurable quality gates before increasing coverage).

---

## Plan

### Phase 0 — Foundations (unblock + metrics baseline)

- Fix `CanonicalJob` model (`url` field placement).
- Ensure `pipeline.py` consistently passes `url` and does not crash in `_to_canonical`.
- Fix timezone handling in ghosting.
- Unify profile definition (single source of truth in `get_alina_profile()`).
- **Success metrics / automated checks**:
  - `assert len(run_full_pipeline(...)) > 50` (or configurable threshold).
  - Smoke test that `demo/generate_html_report.py` produces valid HTML with at least N cards.
  - Log raw vs ranked counts + basic telemetry (see Automation section).
- Verify that `run_full_pipeline()` + HTML report now return >0 jobs.

### Phase 1 — Salary & Profile (address hypothesis 1) + Profile improvements

- Set `min_compensation=120000`.
- Change default `compensation_min=None` (do not fabricate 140k).
- Improve salary extraction (multiple payload fields + regex on description/content).
- Update salary scoring: undisclosed → neutral (0.60–0.65).
- Update profile from real CV:
  - Add `chief_of_staff` role family.
  - Expand `target_title_keywords` ("chief of staff", "head of operations", "chief of", etc.).
  - Add "fintech" to `preferred_markets`.
- **Profile management improvements**:
  - Make `get_alina_profile()` the single source of truth (already planned).
  - Add support for loading profile from YAML/JSON (future-proof for multiple candidates).
  - Add `target_companies` and/or `preferred_org_types` (e.g. ["DAO", "Web3 startup", "Protocol"]) for better market/role matching.
- Sync the same changes into `scripts/run_pipeline_on_cv.py` (or migrate callers to the main pipeline).
- **Success metrics**: Update gold examples for salary scenarios; assert no artificial 140k on undisclosed jobs in test data.

### Phase 2 — Role/Market Detection & Prioritization (address hypothesis 2) + Ranking enhancements

- Enhance `_to_canonical` (and consider light normalization mapper usage):
  - Scan title + description/content + tags.
  - Stronger signals for "Head of Operations", "Chief of Staff", governance, treasury, program management.
  - Improve market classification for web3 + adjacent (fintech, security, AI-web3 hybrids).
- **Ranking & Normalization improvements**:
  - Add ranking boosts for exact high-priority title phrases.
  - Add LLM-based booster (if available via delegate) **or** keyword + embedding similarity for "Chief of Staff" / "Head of Operations".
  - Ghost detection: Do **not** penalize fresh high-fit roles too aggressively (add recency + fit guard).
  - Make weights configurable (e.g. `config/ranking_weights.json`) and always log full score breakdown.
- Optionally adjust default weights (increase `role_fit`, decrease `salary_fit`).
- **Success metrics**: Add/update gold dataset in `evals/datasets/` (5–10 examples with Head of Ops / CoS titles) + rubric for `role_fit`. Target: improved precision on target titles.

### Phase 3 — Source Expansion (address hypothesis 3) — make robust

- Wire Greenhouse, Lever, and Ashby connectors into `fetch_all_wave1()` (or a dedicated `fetch_ats_wave()` helper).
- **Robust source management**:
  - Create `config/source_config.yaml` (or Python dict) with curated lists:
    - web3-relevant board tokens for Greenhouse/Lever/Ashby.
    - Priority Telegram channels.
  - Add rate-limiting, exponential backoff, and parallel fetch with concurrency control (e.g. using `concurrent.futures` or `asyncio` with limits).
  - Error recovery: retry on transient errors, skip bad sources, fallback to cached/stub data when needed.
- Expand active Telegram channels (use existing `TelegramConnector`).
- **Telegram improvement**: Support for an updatable list (config file) or simple automatic discovery of new high-signal channels.
- Strengthen dedup (in addition to existing): canonical_job_id + fuzzy title+company matching.
- Increase effective volume while keeping deduplication.
- Update `source-inventory.md` status.
- **Success metrics**: "relevant volume delta" — e.g. % of jobs with `role_family` in target list after expansion. Log raw fetched vs final ranked counts per source.

### Phase 4 — Ranking Tuning + Delivery Polish + Automation foundation

- Final weight adjustments, title priority logic, and configurable weights.
- Ensure ghost penalty does not suppress fresh high-fit roles.
- Update `demo/generate_html_report.py` / delivery to reliably show real clickable links and good explanations.
- Regenerate `job_results.html` with the improved profile.
- Start laying groundwork for automation (see dedicated section below).

### Phase 5 — Verification & Gates

- Manual review of top 15–20 results (relevance, salary handling, prioritization of Head of Ops / CoS).
- Confirm raw volume moved toward "hundreds" of candidate roles before ranking.
- Run existing tests + new smoke checks.
- **Automated eval**:
  - Run full eval suite + generate report.
  - Precision@10 (or similar) for target titles (Head of Ops, Chief of Staff, etc.).
- Update any affected evals/datasets if behavior changed measurably.
- Document lessons in `docs/decisions/`.
- Produce comparative "before/after" report per phase (raw volume, top-k relevance, score distributions).

---

## Automation & Observability (cross-cutting, critical for Hermes usage)

- Add `scripts/autonomous_cycle.py` (or similar) that can:
  - Run the full pipeline on the target profile.
  - Apply basic filters / ranking.
  - Generate HTML report + summary.
  - Log telemetry: total raw jobs, ranked count, top-5 scores + titles, per-source counts, errors.
- Telemetry output: simple JSON/CSV + optional GitHub issue comment or file in `reports/`.
- Error recovery built into fetchers (retry, skip, fallback).
- **CI-like gates** (add to future `.github/workflows`):
  - Before merging PRs that touch ranking/sources: run tests + evals + generate HTML report.
- Make it easy to run repeated cycles (aligns with Hermes agent / cron patterns).

---

## Post-merge Action Items

- [ ] Run the updated pipeline on the real CV and share the new `job_results.html` + top results summary + before/after comparison.
- [ ] Create `config/source_config.yaml` with initial curated web3 boards + Telegram list.
- [ ] Add rate-limiting + parallel fetch + error recovery in Phase 3.
- [ ] Curate and test 5–10 additional web3-relevant ATS board tokens (Greenhouse/Lever/Ashby).
- [ ] Expand Telegram channel list (config-driven) and measure relevant volume delta.
- [ ] Add gold dataset (5–10 Head of Ops/CoS examples) + rubric in `evals/` for role_fit.
- [ ] Implement `scripts/autonomous_cycle.py` + basic telemetry.
- [ ] Add `.github/workflows/ci.yml` (tests + eval + HTML smoke).
- [ ] Make weights configurable + profile loadable from YAML.
- [ ] Update `source-inventory.md`, architecture docs, and README with autonomous mode instructions.
- [ ] Decide on next cycle (more sources, better normalization, feedback loop, or integration with job-application pipeline).

---

## Success Criteria

- Top results are predominantly relevant senior/head web3 ops roles.
- 120k threshold respected; salary-less jobs are not artificially boosted.
- "Head of Operations" and "Chief of Staff" titles surface and rank high when present.
- Pipeline reliably returns hundreds of raw candidates from expanded sources.
- Explicit per-phase metrics + automated checks are in place and passing.
- All changes follow repo principles (evals, quality gates, explicit reasoning, observability).

**Branch**: `feat/plan-job-aggregator-ranking`  
**PR type**: Documentation + planning (foundational for subsequent implementation PRs)