# Implementation Plan: Job Aggregator & Ranking Improvements (Web3 Head of Ops / CoS)

**Date**: 2026-07-13  
**Owner**: Alina + Hermes Agent  
**Related**: `source-inventory.md`, `implementation-plan-sources.md`, personal CV profile work

---

## Problem

Current job search pipeline produces low-quality top results for the target profile (Alina Aseeva — Head of Operations with deep Web3/DAO/DeFi background):

- Top-ranked jobs are mostly irrelevant (virtual assistants, sales, generic "hr assistant", non-ops roles).
- Hardcoded `min_compensation=140000` is applied even to jobs that do not list salary. Many real postings do not publish compensation.
- Role fit signals for high-priority titles (**Head of Operations**, **Chief of Staff**, program/governance ops) are weak.
- Source coverage is too narrow. Only a small subset of implemented connectors (mainly RemoteOK + a few Telegram channels) are actually used in `fetch_all_wave1()`. High-volume real ATS connectors (Greenhouse, Lever, Ashby) exist but are not exercised for this profile.
- Resulting volume is too low to surface the expected "hundreds" of relevant senior/head web3 (and adjacent fintech/security/AI-web3) roles.
- Two slightly different profile definitions and several crude parsing heuristics make the system fragile and hard to tune.

The current output does not match the desired experience: **hundreds of open senior/head web3 roles visible, with strong role fit for Head of Ops / CoS ranked at the top**.

---

## Solution

Create a focused, evaluable improvement cycle for the aggregator + ranking layer:

1. Fix salary handling (no fabrication of 140k, lower threshold to 120k, treat undisclosed as neutral/soft signal).
2. Strengthen role fit and prioritization for **Head of Operations** and **Chief of Staff**.
3. Expand the sources actually called in the main pipeline (add Greenhouse/Lever/Ashby with curated web3-relevant boards + more Telegram channels).
4. Improve title/description parsing for role, market, and seniority.
5. Tune ranking weights and add explicit boosts for target titles.
6. Unblock full pipeline execution (model + runtime bugs discovered during diagnosis).
7. Deliver an updated HTML report so the user can see the difference.

All changes must preserve the repository principles (evals-first, measurable quality gates before increasing coverage).

---

## Plan

### Phase 0 — Foundations (unblock)
- Fix `CanonicalJob` model (`url` field placement).
- Ensure `pipeline.py` consistently passes `url` and does not crash in `_to_canonical`.
- Fix timezone handling in ghosting.
- Unify profile definition (single source of truth in `get_alina_profile()`).
- Verify that `run_full_pipeline()` + HTML report now return >0 jobs.

### Phase 1 — Salary & Profile (address hypothesis 1)
- Set `min_compensation=120000`.
- Change default `compensation_min=None` (do not fabricate 140k).
- Improve salary extraction (multiple payload fields + regex on description/content).
- Update salary scoring: undisclosed → neutral (0.60–0.65).
- Update profile from real CV:
  - Add `chief_of_staff` role family.
  - Expand `target_title_keywords` ("chief of staff", "head of operations", "chief of", etc.).
  - Add "fintech" to `preferred_markets`.
- Sync the same changes into `scripts/run_pipeline_on_cv.py` (or migrate callers to the main pipeline).

### Phase 2 — Role/Market Detection & Prioritization (address hypothesis 2)
- Enhance `_to_canonical` (and consider light normalization mapper usage):
  - Scan title + description/content + tags.
  - Stronger signals for "Head of Operations", "Chief of Staff", governance, treasury, program management.
  - Improve market classification for web3 + adjacent (fintech, security, AI-web3 hybrids).
- Add ranking boosts for exact high-priority title phrases.
- Optionally adjust weights (increase `role_fit`, decrease `salary_fit`).

### Phase 3 — Source Expansion (address hypothesis 3)
- Wire Greenhouse, Lever, and Ashby connectors into `fetch_all_wave1()` (or a dedicated `fetch_ats_wave()` helper).
- Maintain a small curated list of web3/fintech/ops-relevant board tokens (start with working examples like "stripe" + targets from synthetic data and real Web3 companies).
- Expand active Telegram channels using the existing `TelegramConnector`.
- Increase effective volume while keeping deduplication.
- Update `source-inventory.md` status as we promote connectors from "not used" to "active for this profile".

### Phase 4 — Ranking Tuning + Delivery Polish
- Final weight adjustments and title priority logic.
- Ensure ghost penalty does not suppress fresh high-fit roles.
- Update `demo/generate_html_report.py` / delivery to reliably show real clickable links and good explanations.
- Regenerate `job_results.html` with the improved profile.

### Phase 5 — Verification & Gates
- Manual review of top 15–20 results (relevance, salary handling, prioritization of Head of Ops / CoS).
- Confirm raw volume moved toward "hundreds" of candidate roles before ranking.
- Run existing tests + new smoke checks.
- Update any affected evals/datasets if behavior changed measurably.
- Document lessons in `docs/decisions/`.

---

## Post-merge Action Items

- [ ] Run the updated pipeline on the real CV and share the new `job_results.html` + top results summary.
- [ ] Curate and test 5–10 additional web3-relevant ATS board tokens (Greenhouse/Lever/Ashby).
- [ ] Expand Telegram channel list and measure delta in relevant volume.
- [ ] Add at least one small gold example or rubric update in `evals/` for the new ranking behavior (Head of Ops / CoS priority).
- [ ] Update `source-inventory.md` and any architecture docs.
- [ ] Decide on next cycle (more sources, better normalization, feedback loop, or personal application pipeline integration).

---

**Success Criteria**
- Top results are predominantly relevant senior/head web3 ops roles.
- 120k threshold respected; salary-less jobs are not artificially boosted.
- "Head of Operations" and "Chief of Staff" titles surface and rank high when present.
- Pipeline reliably returns hundreds of raw candidates from expanded sources.
- All changes follow repo principles (evals, quality gates, explicit reasoning).

**Branch**: `feat/plan-job-aggregator-ranking`  
**PR type**: Documentation + planning (no production code changes in this PR)