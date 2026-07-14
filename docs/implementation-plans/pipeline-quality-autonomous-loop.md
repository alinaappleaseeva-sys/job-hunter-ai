# Implementation Plan: Pipeline Quality & Coverage — Autonomous Improvement Loop

**Date**: 2026-07-14  
**Owner**: Hermes Agent (autonomous) + Alina (final review)  
**Goal**: Reach a state where a single pipeline run on Alina's profile reliably surfaces **≥15 truly good roles** (high relevance, low noise) for Head of Operations / DAO Operations / Program Manager in Web3/DAO/crypto/fintech.  
**Status**: Planning → Execution (autonomous mode)

## 1. North Star & Success Criteria

### Primary Success
After a clean pipeline run + autonomous validation, at least **15 roles** are marked as "truly good" by the agent using the explicit rubric below.

### Definition of "Truly Good Role" (Autonomous Rubric)
A role is **truly good** only if it passes **all** of the following (agent must be strict):

1. **Role fit** — Title + role_family clearly aligns with target (Head of Operations, DAO Ops, Program Manager / governance / cross-functional ops in web3/dao/crypto). Pure accounting/finance/GL ops, sales, HR, or generic "ops" in non-relevant industries = fail.
2. **No hard credential mismatch** — Does not require CPA, Big 4, specific licenses, or heavy public accounting/SOX experience that the candidate does not have.
3. **Market & context relevance** — Company or ecosystem is web3, DAO, crypto, blockchain, or very close fintech/ops-adjacent where the candidate's background (governance, treasury, building from 0-1, cross-functional leadership) is directly applicable.
4. **Seniority & scope** — Senior/Lead/Head/Manager level ops/program work, not junior or purely executional.
5. **Data quality** — Real job (not obvious stub/sample), recent enough (per recency filter), reasonable compensation signal.
6. **Agent gut check** — "If this was the only job I saw today, would I be excited to tailor a CV for it?" — honest no = fail.

**Note**: Agent must document the pass/fail + 1-2 sentence rationale for borderline cases.

### Secondary Metrics (tracked per run)
- % of top-20 that pass the rubric
- Number of "near-miss" roles (fail only on one criterion)
- Source diversity in the good set
- Presence of clear DAO/governance/treasury/cross-functional ops examples

## 2. Overall Approach — Autonomous Quality → Coverage Loop

**Core Principle**: Never add volume (new sources) until quality controls are strong enough that the new volume does not flood the top with мусор.

**Loop Structure** (agent runs this with minimal user intervention):

1. **Quality Round** (mandatory before new sources)
   - Clean samples
   - Improve role_family + requirements extraction + penalties
   - Run full pipeline on CV
   - Autonomous review of top jobs using rubric
   - If < 15 truly good → stay in Quality mode (or small targeted fixes)

2. **Coverage Step** (add in small batches)
   - Add up to **4 sources** at a time from `docs/architecture/implementation-plan-sources.md`
   - Make them produce real (or clearly marked) data
   - Re-run pipeline
   - Autonomous review

3. **Decision Gate** (agent decides)
   - ≥15 truly good in one run → Surface results + summary to user + stop or ask for next goal
   - Still noisy → Another Quality round + possibly another small batch of sources
   - Stuck (3+ loops with no meaningful lift) → Surface diagnosis + blocked items to user

The agent will:
- Work in small, reviewable PRs
- Run the pipeline after every meaningful change that affects ranking
- Log autonomous reviews (in a run log or comments)
- Only promote "good" sets to the user when they pass the rubric

## 3. Phase 0 — Sample Hygiene (First Action)

**Problem**: Many connectors fall back to `load_sample_*` that contain misleading high-relevance fakes (e.g. "Head of Operations @ Axine Labs" that was actually Business Development in mineral mapping).

**Agent Actions**:
- Audit every `load_sample_*` function across connectors:
  - `wellfound.py`
  - `weworkremotely.py`
  - `arcdev.py`
  - `solana.py`
  - `habr_career.py`
  - `workable.py`
  - Telegram channel samples
  - Any others
- For each sample:
  - Remove or heavily neuter any that claim target roles (Head of Ops, DAO Ops, Program Manager in web3) unless they are verifiably real recent examples.
  - Prefer conservative/neutral samples or empty lists when live fetch fails.
  - Add clear comments: `# FALLBACK ONLY — not used for ranking decisions`.
- Update any code that treats samples as realistic data for ranking/telemetry.
- Add a simple guard: if a job comes from a known sample source in production runs, log a warning.

**Exit criteria**: No sample data in the top-30 of a normal CV run contains obviously fake high-fit roles for the target profile.

## 4. Phase 1 — Core Quality Improvements

### 4.1 Improve `infer_role_family` (negative rules + precision)

Current logic is too crude (`\boperations|ops\b` → "operations").

**Planned changes** (in `src/job_hunter_ai/normalization/fields/enrichment.py`):
- Add strong negative patterns that force "other" or a new "finance_ops" / "accounting_ops" family:
  - accounting, "gl operations", "general ledger", tax, audit, "sox", "cpa", "big 4", "public accounting", "financial reporting", "intercompany", "close process", reconciliation, etc.
- Add positive but more precise patterns for target families:
  - "dao", "governance", "working group", "contributor", "treasury ops", "program manager.*(dao|web3|crypto|ops)", "head of ops", "chief of staff", "ops lead.*web3", etc.
- Consider sub-families or tags if simple string rules become messy (keep simple first).
- Update `resolve_role_family` and callers if needed.
- Add unit tests for new rules (especially negative cases).

**Goal**: "Accounting Manager, GL Operations" no longer gets `role_family=operations` for our profile.

### 4.2 Hard Requirements Extraction + Scoring

Currently ranking has almost no signal from actual JD requirements.

**New component**:
- Create or extend `src/job_hunter_ai/normalization/fields/requirements.py`
- Extract hard credentials from raw description / "requirements" section:
  - CPA, CFA, "Big 4", "public accounting", "SOX 404", "U.S. GAAP", specific licenses, "must have X years in Y", "Bachelor's in Accounting/Finance" when combined with heavy accounting language.
- Store in `CanonicalJob` (new fields: `hard_requirements: list[str]`, `requires_cpa: bool`, etc.).
- In ranking:
  - New score component: `requirements_fit` (or penalty).
  - If job requires CPA/Big4 + profile does not claim it → strong negative score (e.g. 0.0–0.3 on that component).
  - General mismatch on "specific experience" language that is clearly not in master CV → penalty.
- Make the penalty tunable via weights.

**MVP scope for first iteration**:
- Simple regex + keyword list for credentials.
- Basic "requires_accounting_credential" flag.
- Penalty only for the most obvious cases (CPA/Big4/SOX when clearly required).

### 4.3 Strengthen Overall Mismatch Penalties in Ranking

- Review `compute_score_breakdown` and `_score_role_fit`.
- Add or increase negative signals when role_family is finance/accounting heavy but profile target is general/dao ops.
- Consider a small "profile_hard_filters" step before full scoring (e.g. drop or heavily downrank jobs that explicitly require credentials the candidate lacks).
- Ensure recency + other filters still apply.

## 5. Autonomous Validation Protocol (How the Agent Reviews)

When the agent reviews a run:

1. Run the pipeline (or use latest telemetry + full job data).
2. Take top 25–40 roles.
3. For each, answer the rubric questions above.
4. Count truly good roles.
5. Log in a structured way (e.g. `evals/runs/autonomous_review_YYYYMMDD.md` or similar):
   - Run ID / timestamp
   - Sources active
   - Number of truly good
   - List of good ones with short justification
   - List of near-misses + why they failed
   - Decision: "Continue quality", "Add next batch of sources", or "Ready for user review"
6. Only surface a set to the user when ≥15 truly good in one run, or when the agent believes the current state is the best we can get without major new work.

The agent treats itself as a strict, slightly skeptical reviewer on behalf of the user.

## 6. Source Addition Strategy

Sources will be added in **batches of up to 4** from the prioritized list in `docs/architecture/implementation-plan-sources.md` (Wave 1 first):

Recommended first batches (agent will pick based on current gaps):
- Batch A: We Work Remotely + Arc.dev (easy remote tech)
- Batch B: More Telegram channels (high relevance for web3)
- Batch C: Wellfound real implementation (or better fallback)
- Batch D: Workable or next clean ATS

For each source added:
- Make it return real (or clearly conservative) data.
- Add minimal smoke/eval coverage.
- Re-run full pipeline + autonomous review before considering the next batch.

Do **not** add more than 4 at a time without a review gate.

## 7. Branching, PR & Execution Rules

- Work on feature branches off `main` (or current stable).
- **Rebase** before opening or updating PRs (no merge commits in feature branches).
- Keep PRs small and reviewable. Prefer one logical change per PR (e.g. "quality: add negative rules to infer_role_family", "ranking: add requirements mismatch penalty").
- PR description template (use this structure):
  ```
  ## Problem
  ...

  ## Solution
  ...

  ## Plan
  - Step 1
  - Step 2

  ## Post-merge action items
  - Run full pipeline
  - Autonomous review
  - ...
  ```
- After any change that affects ranking or ingestion:
  - Run `python scripts/run_pipeline_on_cv.py` (or equivalent)
  - Generate report if available
  - Perform autonomous review
- Regular PR cadence: aim for a PR after each meaningful atomic improvement or after completing a small batch of source additions + review.
- Tag PRs with labels if the repo uses them (quality, sources, ranking, etc.).

## 8. Run Commands & Artifacts

- Main run: `python scripts/run_pipeline_on_cv.py`
- There is also `scripts/autonomous_cycle.py` — evaluate if useful for scripted loops.
- After significant changes: update telemetry, job_results.html, and autonomous review notes.
- Store autonomous review logs under `evals/runs/` or `docs/runs/`.

## 9. Decision Framework for the Agent (Autonomous)

- After each full run + review:
  - If ≥15 truly good → Prepare summary + list for user. Ask if they want to continue for more volume or move to tailoring.
  - If 8–14 truly good → One more focused quality pass or one small source batch.
  - If <8 → Prioritize quality fixes. Do not add new noisy sources yet.
- If 3 consecutive loops show no lift in good count → Surface "plateau" diagnosis to user with data.
- Always prefer quality improvements over volume when the top is still polluted.

## 10. Risks & Safeguards

- Over-filtering (killing good roles) → Keep "near-miss" tracking. Agent will note roles that are interesting but blocked by new rules.
- Sample pollution returning → Phase 0 is non-negotiable.
- New sources being very noisy → Strict autonomous review before accepting them into "good" count.
- Agent hallucinating relevance → Use the explicit rubric + write short justifications. Be conservative.

## 11. Exit Criteria for the Whole Effort

- One clean run produces ≥15 roles that pass the full "truly good" rubric.
- The agent has high confidence (documented) that the top of the list is mostly signal, not noise.
- User confirms the set looks useful and we can move (or not) to CV tailoring work.

## 12. Immediate Next Steps (Agent Will Execute)

1. Create this plan + open PR for review (documentation).
2. Start Phase 0: Audit and clean all `load_sample_*` functions (PR per connector or grouped).
3. Implement first version of `infer_role_family` negative rules + tests.
4. Add basic hard requirements extraction + penalty.
5. Run pipeline + autonomous review.
6. Decide on next micro-step or first batch of 4 sources.

---

**This plan is designed for autonomous execution with regular PRs and clear gates.**  
The agent will follow the loop, document reviews, and only surface results to the user when they meet the bar or when stuck.

User can interrupt at any time with "СТоп", "давай другой приоритет", or specific instructions. Otherwise the agent will keep cycling through quality → small coverage → review.