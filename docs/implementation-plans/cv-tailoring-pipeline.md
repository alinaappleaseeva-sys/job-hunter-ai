# Implementation Plan: CV Tailoring Pipeline for Top Matches

**Project**: job-hunter-ai  
**Stage**: Tailored CV Generator (Good → Excellent)  
**Date**: 2026-07-14  
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
   - User answers → facts are stored as **enrichments** (linked to master CV version).

4. **Per-Job Tailoring**
   - Score each master bullet against the specific JD.
   - Select + reorder + lightly rephrase the best 3 bullets per role.
   - Rewrite summary to emphasize the most relevant themes.
   - Apply emphasis (bold) on numbers and role-aligned phrases.
   - Output tailored Markdown.

5. **Review & Approval**
   - Present all tailored versions side-by-side or in a clean review format.
   - User can accept / request tweaks / add more facts.

## 6. Recommended Phased Implementation

### Phase 0: Foundations (1–2 sessions)
- Structured parser for current master CV (YAML/JSON intermediate or Pydantic models).
- JD fetcher + requirement extractor (reuse existing connectors + LLM extraction).
- Basic "fact library" from master CV.
- Simple similarity scoring between bullets and JD requirements.

**Deliverable**: `src/cv_tailor/models.py` + `parse_master_cv()` + basic JD parser.

### Phase 1: Gap Analysis + Interactive Discovery (Core Value)
- Cross-job gap detector.
- CLI / chat flow for discovery session:
  - "Comparing your master CV against these 12 jobs, the most common gaps I see are..."
  - Specific questions per gap cluster.
- Storage of user answers as durable enrichments (e.g., `enrichments/alina-aseeva-2026-07-14.json` or in repo under a dedicated folder).
- Ability to re-run discovery when master CV or Top list changes.

**Key Rule**: Every enrichment must be traceable back to a user answer.

### Phase 2: Tailoring Engine (Good → Excellent)
- Bullet scorer + selector (pick top 3 per experience section).
- Rephraser with strict rules:
  - Synonym substitution only.
  - Stronger action verbs from allowed list.
  - Front-load outcomes.
  - Add light context bridges when user-confirmed.
- Summary rewriter (target-role version of the master summary).
- Emphasis applicator (bold metrics and role keywords).
- Strict "no fabrication" validator (can be simple + LLM-as-judge with user review).

**Example rules** (from provided images):
- Turn generic bullets into "enabled X for Y merchants, generating $Z".
- Highlight "commercial bank in Australia", "MENA and Asia", specific tech (QR codes, etc.).
- Keep the original achievement but make the relevance obvious.

### Phase 3: Batch Mode + Review Surface
- Process Top-N jobs in one run.
- Generate one tailored CV per job (named clearly: `Alina_Aseeva_Tailored_Axine_Labs_Head_of_Ops_2026-07-14.md`).
- Side-by-side diff view (master vs tailored) or clean review deck.
- Batch approval workflow (accept all / review individually / request changes).

### Phase 4: Quality Gates & Guardrails
- Automated checks:
  - No dates changed.
  - No new companies/roles invented.
  - Bullet count guard (configurable, default respect user's 3-bullet preference where it exists).
  - Readability / professionalism heuristics.
- LLM-as-judge pass ("Is this version clearly better for this JD while remaining truthful?").
- Human review required before any use.

### Phase 5: Integration & Polish
- Hook into existing pipeline (`run_pipeline_on_cv.py` or autonomous cycle).
- After finding Top matches → offer "Tailor CVs for these jobs?"
- Store tailored versions alongside `job_results.html` / reports.
- Command: `python scripts/tailor_cvs_for_top.py --limit 10`
- Later: export to DOCX / clean PDF.

## 7. Data Model (Proposed)

```yaml
# master_cv_version: 2026-07-14
# enrichments/
#   2026-07-14-axine-labs-gaps.json
```

Core structures:
- `MasterExperience` (company, title, dates, bullets[], tags)
- `JDRequirements` (must-have skills, preferred signals, keywords, level)
- `Enrichment` (gap_id, question, user_answer, added_facts[], approved_at)
- `TailoredBullet` (original_bullet_id, new_text, rationale, emphasis_ranges)
- `TailoredCV` (job_id, tailored_summary, per_experience_sections, generated_at, master_version)

## 8. User Experience Flow (Target)

1. User runs pipeline → gets fresh Top-12.
2. `tailor top` (or automatic after pipeline).
3. System:
   - Builds fact library from master.
   - Analyzes all 12 JDs.
   - Runs one discovery session (10–15 smart questions).
4. User answers questions (chat or form).
5. System generates 12 tailored Markdown files.
6. User reviews in a nice diff/review UI (Markdown or HTML).
7. User approves or asks for adjustments on specific jobs.
8. Approved tailored CVs are ready to send.

## 9. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| User feels the tailored version is "worse" | Strong quality gates + side-by-side review + "revert to master" option |
| Over-aggressive rephrasing invents things | Strict rules + traceability + user confirmation on any new framing |
| Too many questions in discovery | Deduplicate gaps across batch; cluster questions; make optional |
| Master CV becomes out of date | Clear workflow: always update master first, then re-run discovery |
| Hallucinated skills in LLM rephrasing | Rule-based rephraser first + LLM only for suggestions + validation step |

## 10. Milestones & Suggested Order

1. **M1 (Foundation)**: Master CV parser + JD requirement extractor + basic scoring.
2. **M2 (Discovery MVP)**: Gap analysis + interactive Q&A that stores enrichments.
3. **M3 (Tailoring MVP)**: Generate one high-quality tailored CV for a single job (e.g. Axine Labs).
4. **M4 (Batch + Review)**: Process 8–12 jobs + clean review surface.
5. **M5 (Integration)**: Hook into existing job-hunter pipeline + CLI command.
6. **M6 (Hardening)**: Quality gates, traceability, export options, tests.

## 11. Next Immediate Steps (After Plan Approval)

- [ ] Confirm this plan or adjust priorities.
- [ ] Decide on first target job for M3 (recommend one of the current Top: Axine Labs or Friss Labs).
- [ ] Choose storage for enrichments (repo folder vs separate vault).
- [ ] Decide on output format priority (Markdown first is recommended).
- [ ] Set up the first small spike: parse current master CV into structured data.

---

**Ready when you are.**  
Reply with "Let's start" + any adjustments (e.g. "make discovery session lighter", "focus on batch first", "add DOCX early", etc.), and I'll begin Phase 0 implementation.

We will treat your current master CV as excellent raw material and only make it more precisely targeted — never less good.