# Implementation Plan: Talent Titans — Scanning Top 100 Web3 Employers Career Pages

**Date**: 2026-07-29 (Finalized)  
**Owner**: Alina + Hermes Agent  
**Related**: `best web3 employers.pdf`, `sources/protocol_seeds.yaml`, `sources/prepare_talent_titans.py`, `sources/talent_titans_top100.yaml`, `config/source_config.yaml`, `src/job_hunter_ai/pipeline.py`, `evals/`, `docs/research/source-inventory.md`

**Goal**: Make the system systematically walk through the ~100 employers from the "best web3 employers.pdf", discover their career pages (preferring existing ATS boards), extract vacancies, normalize them, and surface only those that fit Alina’s profile (Head of Ops / CoS / DAO Ops / Governance / Treasury roles in Web3) using the existing ranking machinery.

## Key Principles (from repo + discussion)
- **Maximum leverage of existing ATS connectors** (Greenhouse, Ashby, Lever, Workable) — best possible data quality.
- **Do not duplicate** with `protocol_seeds.yaml`. Merge/overlap handling required.
- `talent_titans_top100.yaml` is human-curated **source of truth** for “what we want to cover”.
- Discovery results are **observations**, not source of truth.
- Evals-first, small diffs, vertical MVP first.
- “Fits me” logic lives only in `get_alina_profile()` + ranking + ghosting (no duplication).
- Politeness + robustness.

## Final Phase Structure

### Phase 000 — Data Preparation
- Extract structured list from PDF → `sources/talent_titans_top100.yaml`
- Semi-automatic enrichment of top ~30 (careers URLs, ATS type, priority, `ops_relevance`)
- Overlap detection and merge strategy with `protocol_seeds.yaml`
- Tooling: `prepare_talent_titans.py`

### Phase 1 — Career Page Discovery (clarified)
See detailed clarification below.

### Phase 2 — Integration & Leverage
- Add discovered ATS boards to `config/source_config.yaml`
- Wire custom career pages into improved `fetch_protocol_stubs.py` / new wave
- Add to `fetch_all_wave1()` or dedicated native wave

### Phase 3 — Filtering “if they fit me”
- Already covered by existing pipeline (profile + ranking + recency + ghosting)
- Add metrics for uplift from this source family

### Phase 4 — Evals & Quality Gates
- Smoke datasets for new sources
- Source health / precision on target roles
- Update `source-inventory.md`

### Phase 5 — Automation
- `scripts/run_talent_titans_wave.py` or extension of autonomous cycle
- Reports + optional Telegram digest for high-match roles only

## Detailed Clarification for Phase 1 (Career Page Discovery)

**Script**: `sources/discover_careers.py` (or enhancement of `prepare_talent_titans.py`)

### 1. Where to write results
**Only to a separate file.** Do **not** update `talent_titans_top100.yaml` or `protocol_seeds.yaml` directly from the discovery script.

Recommended layout:
```
sources/
├── talent_titans_top100.yaml                 ← Source of Truth (human-maintained)
├── protocol_seeds.yaml
└── discovery/
    └── talent_titans_discovery.yaml          ← Output of the script (can be overwritten)
```

**Rationale**:
- `talent_titans_top100.yaml` = intent (“what we decided to cover”)
- Discovery output = observation (“what we found today”)
- Later step (manual or small merge script) promotes high-confidence findings into configs / seeds

### 2. Depth of the script in Phase 1
Stay **light**:

**Do**:
- Try common career paths (`/careers`, `/jobs`, `/opportunities`, `/hiring`, `/about/careers`, etc.) with proper `urljoin` + redirects.
- Detect links to known ATS boards:
  - `boards.greenhouse.io/*`
  - `jobs.ashbyhq.com/*`
  - `jobs.lever.co/*`
  - `apply.workable.com/*`
- Light “has open roles” signal:
  - HTTP 200
  - At least 1–3 job-like signals (keywords: job, role, position, hiring, apply, opening, etc.) **OR** an ATS link was found

**Do NOT** (in Phase 1):
- Full job list parsing
- Extract title / description / salary / location
- Determine fit for Alina’s profile
- Deep crawl of the site

**Example output entry**:
```yaml
- name: Phantom
  website: https://phantom.com/
  careers_candidates:
    - url: https://jobs.ashbyhq.com/phantom
      type: ats
      ats: ashby
      board_slug: phantom
      status: 200
      has_job_signals: true
      confidence: high
    - url: https://phantom.com/careers
      type: careers_page
      status: 200
      has_job_signals: true
      confidence: medium
  best_guess:
    ats: ashby
    board_slug: phantom
    careers_url: https://jobs.ashbyhq.com/phantom
    confidence: high
```

High confidence should be reserved primarily for clean ATS detections.

## Recommended Small PR Sequence
1. `talent_titans_top100.yaml` + PDF extraction tooling (Phase 000)
2. `discover_careers.py` + first discovery run on top 20–30 + `discovery/` folder
3. Add discovered ATS boards to `source_config.yaml` (after review)
4. Integration of custom pages + wave into pipeline
5. Evals + metrics (gate)
6. Full run + report (only after previous gates)

## What Not to Do
- Do not write 100 custom scrapers.
- Do not scrape LinkedIn/Indeed.
- Do not enable all 100 sources without evals.
- Do not duplicate ranking/profile logic.

## Expected Outcome
Strong increase in high-quality native sources for the exact target segment, with heavy reuse of existing mature ATS connectors.

---

**Latest clarifying questions** (to be discussed in PR comments):

1. Куда писать результат discovery-скрипта?
   - Прямо обновлять `talent_titans_top100.yaml`?
   - Или писать в отдельный файл (`sources/discovery/talent_titans_discovery.yaml`), а потом вручную или отдельным скриптом мержить?

2. Насколько глубоко должен идти скрипт discovery на этапе Phase 1?
   - Только искать ссылки на ATS + пробовать простые пути?
   - Или добавлять лёгкий парсинг страницы, чтобы понять “есть ли там реально открытые роли” (чтобы отфильтровывать пустые `/careers` страницы)?

(Ответы из обсуждения: только в отдельный файл; лёгкий уровень + минимальный has_job_signals сигнал. Подробности выше в разделе Phase 1.)

## Next Immediate Steps (after plan approval)
- Run `prepare_talent_titans.py` to refresh the list
- Implement `discover_careers.py` per the clarified spec
- First discovery pass on high-priority slice
- Manual review of results + merge decisions for overlaps

This plan is considered approved once merged. All future work should reference this document.