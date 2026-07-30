# Implementation Plan: Talent Titans — Scanning Top 100 Web3 Employers Career Pages

**Date**: 2026-07-29 (Updated with final decisions)  
**Owner**: Alina + Hermes Agent  
**Related**: `best web3 employers.pdf`, `sources/protocol_seeds.yaml`, `sources/prepare_talent_titans.py`, `sources/talent_titans_top100.yaml`, `config/source_config.yaml`, `src/job_hunter_ai/pipeline.py`, `evals/`

**Goal**: Make the system walk through the employers from "best web3 employers.pdf", discover career pages (preferring existing ATS boards), extract vacancies, and surface only those that fit Alina’s profile using existing ranking.

## Core Principles
- Maximum reuse of existing ATS connectors (Greenhouse, Ashby, Lever, Workable).
- `sources/talent_titans_top100.yaml` = human-curated Source of Truth (list from PDF).
- Discovery results = observations only (written to separate file).
- Merge into `protocol_seeds.yaml` / `source_config.yaml` = conscious separate step.
- Evals-first. Small, reviewable changes.
- “Fits me” logic stays only in `get_alina_profile()` + ranking + ghosting.
- One-shot run for data + discovery is safe. Full pipeline execution only after review.

## Final Phase Structure (Approved)

### Phase 000 — Data Preparation
- Extract structured list from PDF → `sources/talent_titans_top100.yaml` (~100 records).
- Semi-automatic enrichment of top-30 (careers URLs, ATS type, `priority`, `ops_relevance`).
- Overlap detection with `protocol_seeds.yaml`.
- Tooling: `prepare_talent_titans.py`.

### Phase 1 — Career Page Discovery
See detailed decisions below.

### Phase 2 — Safe Integration
- One-shot: add only high-confidence ATS boards to `source_config.yaml` (with clear marking).
- Do **not** enable full fetching/ranking in production path yet.

### Phase 3 — Filtering (“if they fit me”)
- Reuse existing `get_alina_profile()`, ranking, ghosting, recency.
- Add uplift metrics for this source family.

### Phase 4 — Evals & Quality
- Smoke datasets.
- Source health metrics.
- Update `source-inventory.md`.

### Phase 5 — Automation & Reporting
- One-shot scripts + reports.
- Full runs only after review.

## Phase 1 — Career Page Discovery (Final Decisions)

**Script**: `sources/discover_careers.py`

### Confirmed Rules

**Q1. Where to write results**
- **Only separate file**.
- Source of Truth: `sources/talent_titans_top100.yaml`
- Discovery results: `sources/discovery/talent_titans_discovery.yaml`
- Merge into `protocol_seeds.yaml` or `source_config.yaml` — **separate conscious step**.
  - One-shot may safely add only high-confidence ATS boards to config (with clear marking).

**Q2. Depth of the script**
- Light level + “not empty” signal.
- Common paths + `follow_redirects`.
- ATS URL detection + extraction of `board_slug` / org / site.
- HTTP 200 + ≥2 job-like signals (links or words: job, role, position, hiring, apply, opening, etc.).
- **Explicitly do NOT**:
  - Parse full list of vacancies
  - Extract title / description / salary / location
  - Evaluate fit for Alina

**Q3. Items already in protocol_seeds.yaml**
- During discovery: mark `already_in_protocol_seeds: true`.
- On merge: **do not duplicate**.
  - Only supplement `careers[]` or `ats` fields if they are empty in the protocol seed.

### Recommended Output Structure (per employer)

```yaml
- name: "Phantom"
  website: "https://phantom.com/"
  careers_candidates:
    - url: "https://jobs.ashbyhq.com/phantom"
      type: "ats"
      ats: "ashby"
      board_slug: "phantom"
      status: 200
      has_job_signals: true
      confidence: "high"
    - url: "https://phantom.com/careers"
      type: "careers_page"
      status: 200
      has_job_signals: true
      confidence: "medium"
  best_guess:
    ats: "ashby"
    board_slug: "phantom"
    careers_url: "https://jobs.ashbyhq.com/phantom"
    confidence: "high"
  already_in_protocol_seeds: false
```

**Confidence levels**:
- `high` — clean ATS detection + 200
- `medium` — good careers page with job signals
- `low` / empty — 404, 403, no signals, or very thin page

### Success Criteria for Phase 1 (Q5)
Task considered complete when:

- `sources/talent_titans_top100.yaml` exists with ≈100 records
- `sources/discovery/talent_titans_discovery.yaml` exists
- Report (stdout or `sources/discovery/REPORT.md`) contains:
  - N employers processed
  - N with ATS (greenhouse / ashby / lever / workable)
  - N empty / low confidence
  - N already_in_protocol_seeds
- `pytest tests/ -q` is green (or at minimum connector unit tests pass)
- No changes to ranking weights, profile definition, or ghosting logic

## One-Shot vs Full Pipeline (Q4)

- **One-shot mode** (recommended for initial work):
  - Data preparation
  - Discovery
  - Optional safe addition of high-confidence ATS boards to `source_config.yaml` (marked)
- **Full fetch + rank** — separate explicit run **after review**.

## Merge Strategy with protocol_seeds.yaml (Q3)

- Mark overlaps during discovery.
- Never duplicate entries.
- Only enrich `careers` or `ats` fields when they are missing.

## Recommended PR Sequence (small & safe)

1. `talent_titans_top100.yaml` + extraction tooling
2. `discover_careers.py` + first run + `discovery/` folder + REPORT
3. Safe enrichment of `source_config.yaml` (high-confidence ATS only)
4. Pipeline integration (after review)
5. Evals + metrics (mandatory gate)
6. Full run + HTML report

## What Not to Do
- Do not write 100 custom scrapers.
- Do not do full job parsing in discovery phase.
- Do not enable everything in pipeline without review.
- Do not touch ranking/profile/ghosting unless necessary.

---

## Latest Clarifying Questions — Final Answers (Approved)

**Q1.** Обновлять `talent_titans_top100.yaml` напрямую или писать в отдельный файл?  
**Answer**: Только отдельный файл.  
Source of truth = `sources/talent_titans_top100.yaml`  
Discovery results = `sources/discovery/talent_titans_discovery.yaml`  
Merge → conscious separate step.

**Q2.** Глубина скрипта  
**Answer**: Лёгкий уровень + сигнал «не пусто».  
Common paths + follow redirects + ATS detection + board_slug + HTTP 200 + ≥2 job-like signals.  
**Do not** parse job list, titles, salary, or fit.

**Q3.** Что делать с уже существующими в `protocol_seeds.yaml`?  
**Answer**: Помечать `already_in_protocol_seeds: true`.  
На мердже — не дублировать. Только дополнять, если поля пустые.

**Q4.** Нужно ли сразу включать всё в pipeline?  
**Answer**: Нет.  
One-shot = data + discovery + (опционально) safe ATS boards в config.  
Полный fetch/rank — отдельный прогон после review.

**Q5.** Success criteria для Гермеса  
**Answer**:
- `talent_titans_top100.yaml` (~100 записей)
- `sources/discovery/talent_titans_discovery.yaml`
- Отчёт со статистикой (N processed, N ATS, N empty/low, N already in seeds)
- Тесты зелёные
- Без изменений в ranking / profile / ghosting без необходимости

---

**This plan is now considered approved with the answers above.**  
All future implementation work must follow these decisions.