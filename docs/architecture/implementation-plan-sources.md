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

---

## 2026-07-15 Update: "День по выбору sources" — Web3/DAO/Ops Prioritization

**Confirmed Segment** (see `docs/research/target-segment.md` for full text):
Head / Senior Operations + DAO / Governance / Treasury / Contributor Coordination / Program Management в Web3/DeFi/Protocols (и crypto infra).
Explicitly broader than pure DAO: DeFi protocols, L1/L2, treasury/gov in projects, contributor ops, infra DAOs.

### Updated Prioritization (Coverage × Relevance / Effort)
From screenshot analysis + validation:
- **Highest**: Pure Web3 boards (web3.career ops/dao filters), DAO-specific (findweb3, aworker), Protocol/DAO career + governance pages + Discords, targeted Telegram (@web3hiring, @DeJob_Global).
- **Medium+**: Web3/remote aggregators (Remote3.co etc.).
- **Lower now**: Broad generic tech (Otta, Arc, We Work Remotely) — only after core coverage.

**Quick Feasibility Checks (Top 6–8, "can we pull real data quickly?")**:
1. cryptojobslist.com — RSS feed structure confirmed and valid. Feasible for quick RSS connector (some fetches limited; handle gracefully). High speed.
2. web3.career (/operations-jobs etc.) — Public HTML with clear filters and "Jul 2026 (X New)" counts. Scrape very feasible. API exists per their docs. Excellent segment coverage.
3. @web3hiring / @DeJob_Global — Existing real Telethon path. Adding = config + parsing. Lowest effort.
4. findweb3.com/jobs/dao — Public DAO listings with highly relevant titles. HTML scrape straightforward.
5. Protocol/DAO surfaces (Lido, Arbitrum, Optimism, karpatkey, Gitcoin, Safe, etc.) — Mix of existing ATS (already real) + custom pages/forums/Discord. Start with seeds.
6. Remote3.co — Public aggregator; scrape/RSS likely feasible.
7. cryptocurrencyjobs.co — Board similar to cryptojobslist; RSS/HTML check next.
8. Discord (protocol gov/ops channels) — Medium (public alerts or future bot); higher than pure RSS.

**Risk notes**: Ghost jobs (mitigate with strong existing ghosting + per-source evals); noise on Telegram (per-channel filters needed); anti-bot low on these sources vs hh.ru/LinkedIn.

### New Recommended Waves (Web3/DAO/Ops focus)
**Wave 1 (Quick Wins — do first)**:
- Expand Telegram with @web3hiring, @DeJob_Global + relevant others (config + filters).
- web3.career filtered views (operations, dao, treasury, non-tech Web3).
- cryptojobslist (RSS first, then full).
- DAO-specific: findweb3.com/jobs/dao and similar.

**Wave 2 (High Relevance)**:
- Real implementation for key protocol/DAO career pages + governance forums (seed list of 10–20).
- More Telegram channels.
- cryptocurrencyjobs.co + Remote3.co style aggregators.
- Workable (next ATS) if it surfaces relevant.

**Wave 3 (Later / High Effort)**:
- Broader remote/tech only if needed for volume.
- Discord deeper integration.
- LinkedIn / high-anti-bot as last resort.

Target after Wave 1: Significant lift in relevant ops/DAO/governance/treasury signals for the profile.

### Protocol Career Pages + How They Publish (List)
Specific starting seeds (Jul 2026):
- **Lido**: Governance forum (research.lido.fi), Snapshot (lido-snapshot.eth), DAO Ops requests via forum; careers often via partners or direct announcements.
- **Optimism Collective**: gov.optimism.io (governance + Seasons), jobs via The Blockchain Association or OP Labs; Discord + X.
- **Arbitrum**: jobs.arbitrum.io / Foundation board, forum.arbitrum.foundation, Snapshot, Discord.
- **Gitcoin**: Site + Discord + grants/contributor programs.
- **karpatkey**: Frequently on DAO boards; direct or partner postings.
- Others: Safe, dYdX, Aragon, StableLab, Morpho, etc. — own /careers or "Join the team", governance forums, Discord #hiring/ops, X posts, Snapshot proposals.
- Cross: jobs.theblockchainassociation.org, aworker.io, findweb3.com.

**Typical publication patterns**: Dedicated careers page; governance forum posts; Discord announcements; contributor/grant calls; X/Telegram; third-party boards; occasional Snapshot for hires.

**Action**: Build `sources/protocol_seeds.yaml` or equivalent with URLs + expected format (careers / forum / Discord).

### Monitoring Plan (X + Discord + Telegram Alerts)
- **Telegram**: Expand existing Telethon connector + per-channel job filters + noise evals. Daily/near-real-time.
- **RSS/Boards**: Poll cryptojobslist RSS, web3.career pages (or API if accessible), other boards on schedule (e.g. every few hours or via cron).
- **X (Twitter)**: Targeted searches ("DAO hiring ops" OR "operations" OR "treasury" OR "governance" "Web3" OR "DeFi" from relevant accounts) + xurl / existing tools. Alerts for high-signal posts.
- **Discord**: Monitor public protocol gov/ops/contributor channels (webhooks, bot, or periodic scrape of announcements). Start with top protocols.
- **Governance forums**: RSS where available (Optimism, Lido research, Arbitrum) or scrape new proposals that mention hiring/contributors/ops.
- **Source Health**: Extend Phase 10 ops/source_health.py + per-source dashboards. Track freshness, ghost rate, noise rate, volume for target segment.
- **Alerts / Pipeline**: Surface high-relevance matches (via existing ranking + new segment tags) in daily runs or dedicated alerts. Track "new" counts as in web3.career style.
- **Eval & Feedback**: Add ingestion smoke + noise rubrics for new sources. Use loyal-user style "Aha" checks on real relevant jobs.
- **Cron / Automation**: Leverage existing cron patterns for polling + notification (see .hermes or pipeline schedules).

**Success Criteria (this sources phase)**:
- ≥5–7 live high-relevance sources for the segment (mix boards + TG + protocols).
- Measurable increase in top-ranked jobs matching Head/Senior Ops + DAO/Gov/Treasury/Contributor profile.
- All active sources have smoke tests + quality gates.
- Clear monitoring + health visibility.

### Career Pages & Monitoring Next Steps
1. Finalize protocol seed list (10–20) with fetch method per entry.
2. Implement Wave 1 connectors (Telegram expand + web3.career + cryptojobslist RSS).
3. Add monitoring hooks (RSS pollers, X searches, basic Discord notes).
4. Update evals and source health for new sources.
5. Re-run ranking on real data and measure lift for target profile.

---

**References**:
- `docs/research/source-inventory.md` (full table with roles, feasibility, risk)
- `docs/research/target-segment.md`
- Old waves preserved above for context; new waves take precedence for Web3/DAO/Ops work.

This day focused on fixation + inventory + feasibility + prioritization. Implementation follows in subsequent work.