# Implementation Plan 2: Sources Expansion

**Goal**: Connect job sources in the optimal order to achieve **maximum useful coverage** for the target profile (Head of Operations / Program Management in Web3, DeFi, DAO, Crypto, Remote) with **minimum effort and maintenance cost**.

This is a dedicated sources plan that takes precedence over the old Tier lists in the original `implementation-plan.md`.

---

## 1. Prioritization Framework

We rank sources by this formula:

**Priority = (Coverage × Relevance) / (Effort + Maintenance Risk)**

### Scoring dimensions

| Dimension          | Low (1)                  | Medium (2)                  | High (3)                     |
|--------------------|--------------------------|-----------------------------|------------------------------|
| **Coverage**       | Niche / few roles        | Good volume                 | High volume or ATS multiplier |
| **Relevance**      | Generic tech             | Remote / ops / startup      | Web3/DAO/DeFi + remote ops   |
| **Effort**         | Public no-auth API       | Auth or pagination          | Scraping / heavy anti-bot    |
| **Maintenance**    | Stable API               | Occasional changes          | High (LinkedIn, hh.ru)       |
| **Data Quality**   | Noisy / unstructured     | Structured                  | Rich + compensation          |

**Hard rules**:
- ATS platforms get a big multiplier (one connector unlocks dozens/hundreds of companies).
- Telegram gets a big multiplier now that we have a **real** Telethon implementation.
- We do **not** start hard sources until easier high-value ones are working and evaluated.

---

## 2. Current State (as of July 2026)

**Real / Live connectors**
- Greenhouse (real)
- Ashby (real)
- Lever (real)
- RemoteOK (real)
- Telegram (real Telethon path + stub fallback)

**Stubs (sample data only)**
- Wellfound
- Solana Jobs
- Habr Career
- hh.ru

**Not implemented**
- We Work Remotely, Arc.dev, Otta
- Workable, Recruitee
- LinkedIn, Indeed
- Most company career pages
- Majority of Telegram channels from inventory

---

## 3. Recommended Sequence (Waves)

### Wave 1: Quick Wins — Maximum Coverage per Hour of Work (Recommended first)

| # | Source                  | Type     | Effort | Relevance to Profile | Why now? | Eval Required |
|---|-------------------------|----------|--------|----------------------|----------|---------------|
| 1 | **Expand Telegram channels** | Telegram | Very Low | Very High | Real client already exists. Adding channels = config + light parsing | telegram_noise suite |
| 2 | **We Work Remotely**    | Job Board | Low    | High (remote)        | Simple public feed, strong remote signal | ingestion_smoke + dedup |
| 3 | **Arc.dev**             | Job Board | Low    | High (remote tech)   | Remote-first international roles | ingestion_smoke |
| 4 | **Wellfound (real)**    | Job Board | Medium | High (startups + ops)| Currently stub. Startup jobs are very relevant for ops roles | ghosting + ranking |
| 5 | **Workable**            | ATS      | Low-Med| High                 | Another strong ATS family | full connector tests |

**Target for Wave 1**: Significantly increase signal for Web3 + remote ops roles with < 2 weeks of focused work.

### Wave 2: High-Leverage Expansion

| # | Source             | Type     | Effort | Relevance | Notes |
|---|--------------------|----------|--------|-----------|-------|
| 6 | Recruitee          | ATS      | Low    | Medium    | Good ATS coverage |
| 7 | Otta               | Job Board| Low-Med| Medium-High | Startup / tech board |
| 8 | Habr Career (real) | Job Board| Medium | High (RU) | Make real only if Russian market is important |
| 9 | Solana Jobs (real) | Job Board| Medium | Medium-High | If Getro API allows clean access |

### Wave 3: High Effort / High Reward (do later)

| Source          | Effort | Notes |
|-----------------|--------|-------|
| hh.ru           | High   | Strong anti-bot. Do only after easier sources are saturated |
| LinkedIn        | Very High | Access constraints. Consider 3rd-party enrichment or very careful approach last |
| Company career pages | Medium-High | Seed list + generic parser. High dedup cost |
| Indeed          | High   | Noisy, heavy dedup |

---

## 4. Detailed Wave 1 Plan (Actionable)

### 1.1 Telegram Expansion (Start here)

- Create `sources/telegram_channels.yaml` (or registry)
- Add top relevant channels from inventory:
  - `@cryptohiring_1`
  - `@tonhunt`
  - `@smerkisjobs`
  - Others with Web3/DAO hiring
- Implement channel-specific light filters (job vs noise)
- Add per-channel eval examples in `evals/datasets/telegram_quality/`
- Gate: noise rate ≤ 35% on new channels

**Effort**: 1-3 days

### 1.2 We Work Remotely + Arc.dev

- Both have relatively clean public listings.
- Implement as new connectors following the `RemoteOKConnector` pattern.
- Reuse existing normalization + dedup.

### 1.3 Wellfound (real implementation)

Current state: stub with `load_sample_wellfound_jobs`.

Options for real:
- Use Getro-like approach (many startup boards use it)
- Or lightweight scraping of public listings

Priority: High because startup job surface is excellent for "Head of Operations" type roles.

### 1.4 Workable

- Public job board API pattern is usually straightforward.
- Add as next ATS after the current three.

---

## 5. Cross-Cutting Requirements (Must Do Before/During Waves)

1. **Source Registry**
   - Centralized config for sources (name, type, enabled, fetch_interval, tags)
   - Easy to turn sources on/off

2. **Per-source Evaluation**
   - Every new source family gets:
     - `evals/datasets/ingestion/smoke_<source>.jsonl`
     - Smoke test in `tests/unit/test_ingestion_smoke.py`
     - Quality gates in `evals/suites/`

3. **Normalization Improvements**
   - Invest in better title/role/market normalization as we add noisy boards.

4. **Source Health & Triage**
   - Use/extend the Phase 10 `ops/source_health.py` and triage.

5. **Dedup Robustness**
   - New sources increase collision risk → strengthen dedup before Wave 2.

---

## 6. Decision Rules

- **Do not** start Wave 2 until Wave 1 sources deliver measurable improvement in ranking quality for the target profile (e.g. at least 2-3 strong matches per run on real data).
- Before adding any scraping-heavy source, prove that public-API sources are insufficient.
- For Russian sources (hh.ru, Habr): activate only if the candidate wants strong RU coverage.
- LinkedIn is **last resort**.

---

## 7. Risks & Mitigations

| Risk                        | Mitigation |
|----------------------------|------------|
| New sources are very noisy | Strong ghosting + per-source noise evals |
| Dedup explodes             | Improve dedup before adding high-volume boards |
| Anti-bot on easy sources   | Monitor health + have fallback strategies |
| Low relevance even after adding | Profile tuning + better market/role signals first |

---

## 8. Success Criteria for Sources Expansion

- At least 5-7 live sources (mix of ATS + boards + Telegram)
- ≥ 60% of top-10 ranked jobs for the target profile come from non-RemoteOK sources
- All active sources have smoke + quality evals passing
- Source health dashboard shows green/degraded status for each

---

## 9. Suggested Next Steps (Right Now)

1. Create `docs/architecture/implementation-plan-sources.md` (this doc)
2. Update `source-inventory.md` with actual implementation status column
3. Start with **Telegram channels expansion** (lowest effort, highest immediate value for Web3 profile)
4. Then We Work Remotely + Wellfound real
5. Parallel: add Workable as next ATS

---

**This plan replaces the old source prioritization section in the main implementation plan.**

Would you like me to:
- Also create the first concrete task list / GitHub issues style breakdown?
- Start implementing Wave 1 (Telegram expansion first)?
- Update `source-inventory.md` with real statuses right now?