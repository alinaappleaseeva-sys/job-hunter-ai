# Source Inventory

This file is the working inventory of job sources we may parse.

Purpose:
- keep one editable list of candidate sources;
- group sources by acquisition strategy;
- separate direct connectors from sources that need extra research;
- expand over time without losing the original coverage map.

Status values we will use later:
- `candidate`: source is known and worth considering
- `priority`: source is likely in early MVP scope
- `research-needed`: source exists, but parsing path or value still needs validation

## ATS Platforms

These are high-leverage sources because one connector can unlock many company career pages.

| Source | URL | Status | Notes |
|---|---|---|---|
| Greenhouse | <https://www.greenhouse.io/> | `priority` | High-value ATS family for early connector work. |
| Lever | <https://www.lever.co/> | `priority` | High-value ATS family for early connector work. |
| Ashby | <https://www.ashbyhq.com/> | `priority` | Important ATS for startup and growth-company hiring. |
| Workable | <https://www.workable.com/> | `candidate` | Broad ATS coverage, likely worth second wave. |
| Recruitee | <https://recruitee.com/> | `candidate` | Good ATS family for broader company coverage. |

## Job Boards

These are direct job discovery surfaces. Some will overlap with ATS-originated jobs and will need strong dedup logic.

| Source | URL | Status | Notes |
|---|---|---|---|
| LinkedIn Jobs | <https://www.linkedin.com/jobs/> | `priority` | Large coverage, but parsing and access path may need careful handling. |
| hh.ru | <https://hh.ru/> | `priority` | Core Russian-language board; important for local coverage. |
| Indeed | <https://www.indeed.com/> | `candidate` | Massive board, but likely noisy and dedup-heavy. |
| Remote OK | <https://remoteok.com/> | `priority` | Strong remote coverage. |
| We Work Remotely | <https://weworkremotely.com/> | `candidate` | Remote-first board with relevant overlap. |
| Wellfound | <https://wellfound.com/> | `priority` | Strong startup job surface. |
| Otta | <https://otta.com/> | `candidate` | Relevant startup/tech board; access details need validation. |
| Habr Career | <https://career.habr.com/> | `priority` | Important RU tech hiring surface. |
| Arc.dev | <https://arc.dev/> | `candidate` | Relevant for international remote/tech roles. |
| AngelList | <https://www.angellist.com/> | `research-needed` | Mentioned as the parent/mothership around CoinList context; we need to validate current job-surface value and access path. |
| Solana Jobs | <https://jobs.solana.com/companies> | `priority` | Important ecosystem-specific board for Solana-related hiring. |
| IDAgent companies | <https://www.idagent.pro/companies#consultation> | `research-needed` | Needs validation: whether this is a meaningful recurring hiring source or just a company listing surface. |

## Telegram Channels

Telegram is likely to give early or off-platform signals. It should be treated as a first-class source family, not a side channel.

| Channel | URL / Handle | Status | Notes |
|---|---|---|---|
| cryptohiring_1 | `@cryptohiring_1` | `priority` | MEXC-focused vacancies. |
| tonhunt | `@tonhunt` | `priority` | TON ecosystem roles: Wallet, TON, TOP, Ston.FI and others. |
| smerkisjobs | `@smerkisjobs` | `priority` | Mostly Blum hiring, with spillover from partners like Bybit and Pancake. |
| hrlunapark | `@hrlunapark` | `candidate` | Engineering-heavy roles. |
| rfoundersjobs | `@rfoundersjobs` | `candidate` | Needs later validation on consistency and uniqueness. |
| crypto_talents | `@crypto_talents` | `candidate` | Crypto-focused hiring surface; quality needs validation. |
| hiring_by_lukina | `@hiring_by_lukina` | `candidate` | Needs later validation on role mix and freshness. |
| zarubezhom_jobs | `@zarubezhom_jobs` | `candidate` | Potential international job flow; likely broad and noisy. |
| AFrucareer | `@AFrucareer` | `candidate` | Needs validation on fit for target roles and markets. |

## Company Career Pages

These are direct company surfaces. For now we treat them as explicit tracked pages or seeds for later company crawling.

| Company | URL | Status | Notes |
|---|---|---|---|
| Doist Careers | <https://doist.com/careers> | `candidate` | Useful as a direct career-page source and as an example company-page parser target. |

## Notes For Later Expansion

- We should eventually split this file into:
  - active MVP sources
  - watchlist sources
  - rejected or low-value sources
- For each source we will later want extra metadata:
  - parsing method
  - auth requirements
  - anti-bot risk
  - expected freshness
  - expected uniqueness versus other sources
  - eval coverage status

