# Implementation Plan: CV Tailoring Pipeline for Top Matches

**Project**: job-hunter-ai  
**Stage**: Tailored CV Generator (Good → Excellent)  
**Date**: 2026-07-14 (revised)  
**Owner**: Alina + AI Agent  
**Related PR**: #48 (CV update + recency filter)  
**Inspiration**: https://github.com/varunr89/resume-tailoring-skill (batch gap analysis + library approach)

## 1. North Star / Goals

**Primary Goal**  
For each high-potential job in the user's Top-15 (e.g. `head of operations @ Axine Labs`, `program manager, dao operations @ Friss Labs`, `program manager - crypto @ Web3 Co`, institutional roles at Coinbase, etc.), automatically generate a **tailored version** of the master CV that:

- Maximizes ATS keyword and structure match
- Reads as "excellent" (not just "good") to a human recruiter/hiring manager
- Stays 100% truthful to the user's actual experience

**Success Criteria (measurable)**
- Every tailored CV passes manual "would I send this?" review by the user
- No fabricated dates, titles, companies, or achievements
- Clear, auditable mapping from master CV bullets → tailored bullets
- Batch processing of 10–15 jobs completes in < 15–20 minutes of user time (mostly confirmation)
- User can maintain one master CV; all tailoring derives from it + confirmed enrichments

## 2. Scope

### In Scope
- Master CV as single source of truth (currently `docs/Alina_Aseeva_CV_14.07.2026.md`)
- Automated extraction of requirements from job descriptions (JD)
- Gap analysis across multiple jobs at once (deduplicated)
- Interactive "discovery session" where the agent flags potential gaps and asks the user for confirmation/additional facts
- Tailoring engine that:
  - Rephrases bullets using synonyms and stronger language
  - Reorders bullets for relevance
  - Front-loads the most matching achievements
  - Applies light keyword optimization (role-specific terms)
  - Uses bold/emphasis on key outcomes (inspired by the provided example images)
- Storage of user-confirmed "enrichments" / clarifications (without polluting the master CV)
- Batch mode for Top-N jobs (default 10–15)
- Generation of tailored Markdown (and later DOCX/PDF)
- Versioning / traceability (which master version + which JD produced this tailored CV)
- Quality gates that prevent degradation

### Out of Scope (for this stage)
- Moving or faking dates
- Inventing roles, companies, or achievements
- Full ATS simulator / automated submission
- Resume design/layout work (keep Markdown-first; visual polish later)
- Cold outreach email generation (separate future track)

## 3. Constraints & Guardrails (Non-Negotiable)

- **Source of truth rule**: All facts must come from the master CV or explicit user answers during discovery.
- **"Good → Excellent" only**: We are not allowed to make the CV worse. Any change must be a clear improvement in relevance or clarity.
- **No date manipulation**.
- **User confirmation required** for any new framing or additional context that is not explicitly in the master CV.
- Tailored output must remain professional and conservative (B2B/Web3 ops style).

## 4. Current State (as of 2026-07-14)

- Master CV lives in repo (strong operations + Web3 + DAO + CEO + consulting background).
- Pipeline already finds good Top matches (after recency filter in PR #48).
- No CV tailoring exists yet.
- User has clear preferences from previous work:
  - Exactly 3 bullets per experience (in many cases)
  - No trailing periods on bullets (in some versions)
  - Bold lead-ins or key metrics
  - Conservative claims only

## 5. High-Level Architecture (Inspired by varunr89/resume-tailoring-skill)

1. **One-time Library Build**
   - Parse master CV into structured experiences, achievements, skills, education.
   - Create a "fact library" (normalized bullets + metadata).

2. **Batch Job Analysis**
   - For N jobs from current Top list:
     - Fetch/parse JD (title, company, requirements, responsibilities, keywords).
     - Extract required skills/experience signals.
     - Run cross-job gap analysis (what is commonly missing across the batch?).

3. **Single Discovery Session**
   - Agent presents consolidated gaps.
   - Asks targeted questions once (e.g., "For DAO governance roles, do you have any experience with token treasury oversight or voting mechanics that isn't listed?").
   - User answers → facts are stored as **enrichments** (linked to specific master CV version).

4. **Per-Job Tailoring**
   - Score each master bullet against the specific JD.
   - Select + reorder + lightly rephrase the best 3 bullets per role.
   - Rewrite summary to emphasize the most relevant themes.
   - Apply emphasis (bold) on numbers and role-aligned phrases.
   - Output tailored Markdown.

5. **Review & Approval**
   - Present all tailored versions side-by-side or in a clean review format.
   - User can accept / request tweaks / add more facts.

## 6. Versioning, Storage & Evaluation (Important Additions)

### Master CV Versioning
- Every run must record an explicit `master_cv_version`:
  - Format: `YYYY-MM-DD-<short-hash>` (e.g. `2026-07-14-a3f2b1`)
  - Include full content hash (sha256 of the markdown) for strong traceability.
- All enrichments and tailored CVs **must** reference this version.

### Enrichments Storage (Start Simple)
- Recommended initial approach: `enrichments/YYYY-MM-DD_HHMMSS_<job-cluster>.json`
- Each file contains:
  - `master_cv_version`
  - `discovered_gaps`
  - `questions_and_answers`
  - `added_facts` (with source = "user_confirmed")
- Later evolution options: git-tracked YAML, SQLite, or a small local DB if volume grows.

### Evaluation / Golden Set
- Create `evals/cv_tailoring/` directory.
- Include 2–3 real job descriptions + corresponding master bullets + expected tailored versions (with rationale).
- Evaluation rubric (at minimum):
  - **Truthfulness** (0–5): No fabrication, dates, or invented achievements.
  - **Relevance lift** (0–5): Clear improvement in alignment with JD.
  - **Readability** (0–5): Professional tone, good flow.
  - **No degradation**: Tailored version must not be worse than a lightly reordered master.
- Add simple automated checks + manual review notes.

### Quantifiable Success Metrics
- % of bullets changed (vs master)
- Keyword overlap lift (TF-IDF or embedding similarity between tailored bullets and JD)
- User approval rate on first 10–15 tailored CVs
- Average time spent in discovery session per batch

## 7. Recommended Approach: Vertical MVP Spike First

**Strong recommendation (revised priority)**

Instead of building horizontal foundations first (Phase 0 → 1 → 2), **start with a vertical end-to-end spike on 1–2 real jobs**.

**Why this is better**:
- You will immediately see real problems: quality of rephrasing, how diffs look, usefulness of enrichments, where the LLM hallucinates or breaks.
- Faster feedback loop from you as the user.
- Avoid over-engineering foundations that may need to be redone after seeing reality.

**Suggested flow**:
1. Pick 1–2 current top jobs (e.g. Axine Labs Head of Operations + Friss Labs Program Manager, DAO Ops).
2. Manually + with LLM help go through the full flow for these 1–2 jobs.
3. Build only the minimal pieces needed to complete the spike.
4. Capture learnings → then design proper foundations.

After the spike, you can safely build the reusable components.

## 8. Phased Implementation (Adjusted for Vertical-First)

### Spike 0: Vertical MVP on 1–2 Real Jobs (Start Here)
**Goal**: End-to-end on real data as fast as possible.

- Parse current master CV (simple structured extraction, even if hacky at first).
- Take 1–2 real JDs from recent top results.
- Manual + LLM-assisted gap identification.
- First attempt at rephrasing + reordering (with heavy user review).
- Produce tailored Markdown + side-by-side diff (even if manual or basic HTML).
- Document all problems encountered.

**Deliverables**:
- 1–2 tailored CVs you are happy to send.
- A short "lessons learned" document.
- List of must-have components for the real implementation.

### Phase 1: Foundations (informed by the spike)
- Pydantic v2 models with strict validation for MasterCV, JDRequirements, Enrichment, TailoredCV.
- Master CV parser + versioning (date + content hash).
- JD parser (LLM extraction + regex for structured fields: must-have / nice-to-have / keywords).
- Basic fact library.

### Phase 2: Gap Analysis + Interactive Discovery
- Cross-job gap detector (deduplicated across the batch).
- CLI/chat discovery session.
- Simple JSON storage for enrichments (per run, with `master_cv_version`).
- Ability to re-run when master CV or Top list changes.

**Key Rule**: Every enrichment must be traceable to a user answer.

### Phase 3: Tailoring Engine + Review UX
- Bullet scoring: 
  - Embedding similarity (sentence-transformers / Voyage / OpenAI embeddings)
  - + keyword boost
  - + recency/impact boost
- Rephraser with explicit rules:
  - Allowed action verbs list (expand from user examples)
  - Forbidden patterns (e.g. unnecessary passive→active voice changes)
  - Always produce a "vanilla" baseline (master CV, only reordered)
- Summary rewriter + emphasis applicator.
- **Diff / Review UX**: Generate an HTML report with side-by-side comparison (use `difflib` or `markdown2` + simple CSS). This is high priority for usability.
- Batch generation for Top-N.

### Phase 4: Quality Gates & Evaluation
- Automated checks (no date changes, no invented facts, bullet count preferences).
- LLM-as-judge with explicit rubric.
- `evals/cv_tailoring/` golden set + rubric (Truthfulness, Relevance lift, Readability, No degradation).
- Human approval gate.

### Phase 5: Integration & Hardening
- Hook into existing pipeline.
- Command like `python scripts/tailor_cvs_for_top.py --limit 10`
- Metrics dashboard (even simple).
- Export options (Markdown primary, DOCX later).
- Edge case handling:
  - Partial employment / consulting gigs
  - Overlapping roles
  - Non-standard experience formats

## 9. Rephrasing Rules & Technical Details (Expanded)

**Rephrasing guidelines** (to be encoded):
- Use stronger, more precise action verbs where they better match the JD.
- Add role-relevant context only when backed by master CV or user confirmation.
- Prefer active voice when it improves clarity (but do not force changes that sound unnatural).
- Always keep original metrics and facts.

**Technical recommendations**:
- Use **Pydantic v2** with `model_config = {"extra": "forbid"}` and strict mode where possible.
- JD parsing: Hybrid approach — LLM for overall understanding + regex/rules for extracting "must have" vs "nice to have".
- Bullet scoring: Hybrid (embeddings + keyword matching + impact signals).
- Always generate two versions per job:
  1. Tailored (optimized)
  2. Vanilla baseline (for comparison)

## 10. Edge Cases to Handle

- Consulting / fractional roles
- Overlapping or concurrent experience
- Research / academic experience being mapped to industry roles
- Very short or very long tenures
- Roles with heavy "ownership" language vs pure execution

## 11. Data Model (Proposed)

```yaml
# master_cv_version: 2026-07-14-a3f2b1
# enrichments/2026-07-14_143022_axine-friss.json
```

Core structures (Pydantic):
- `MasterCV` (version, experiences, skills, education, hash)
- `JDRequirements`
- `Enrichment` (master_version, questions, answers, added_facts)
- `TailoredBullet` (original_id, tailored_text, rationale, emphasis)
- `TailoredCV` (job, master_version, tailored_sections, vanilla_baseline, metrics)

## 12. User Experience Flow (Target)

1. User runs pipeline → gets fresh Top-N.
2. `tailor top` or explicit command.
3. System builds fact library + analyzes JDs.
4. Runs one discovery session (clustered questions).
5. Generates tailored + vanilla versions for each job.
6. Produces HTML review report with side-by-side diffs.
7. User reviews, approves, or requests adjustments.
8. Approved versions are ready.

## 13. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| User feels the tailored version is "worse" | Always provide vanilla baseline + strong quality gates + easy revert |
| Over-aggressive rephrasing | Strict rules engine + traceability + user confirmation on new framing |
| LLM breaks on edge cases | Start with vertical spike to discover them early |
| Discovery session asks too many questions | Deduplicate across batch + make questions optional |
| Enrichments become messy | Start with timestamped JSON files + clear versioning |

## 14. Milestones (Vertical-First Order)

1. **Spike 0 (Vertical MVP)**: End-to-end on 1–2 real jobs + lessons learned.
2. **M1 (Foundations)**: Pydantic models, versioning, master parser, basic JD extraction.
3. **M2 (Discovery)**: Gap analysis + interactive session with JSON storage.
4. **M3 (Tailoring + UX)**: Scoring (with embeddings), rephrasing engine, HTML side-by-side review.
5. **M4 (Evaluation & Gates)**: Golden set + rubric + automated checks.
6. **M5 (Integration)**: Pipeline hook + CLI + metrics.
7. **M6 (Hardening)**: Edge cases, batch polish, export.

## 15. Next Immediate Steps

- [ ] Confirm revised plan (vertical spike first).
- [ ] Choose first 1–2 target jobs for the spike (recommend current top ones: Axine Labs and/or Friss Labs).
- [ ] Decide on simple initial tech (Pydantic + basic LLM calls + difflib for diffs).
- [ ] Set up `evals/cv_tailoring/` skeleton early.
- [ ] Run the first vertical spike.

---

**Ready when you are.**  
We will start with a real vertical spike on actual top vacancies so we learn fast and only build what is truly needed.

Reply with "Let's start the spike" (and which jobs to use first) or any further adjustments.