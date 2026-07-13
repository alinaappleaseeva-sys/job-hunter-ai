# Source Inventory

This file is the working inventory of job sources.

**Purpose**:
- Track candidate sources
- Show **actual implementation status** (not just desire)
- Support prioritization for Implementation Plan 2 - Sources

## Implementation Status Legend

| Status          | Meaning |
|-----------------|---------|
| **real**        | Live connector that fetches real data |
| **stub**        | Only returns sample/fixture data |
| **none**        | Not implemented |
| **partial**     | Some functionality exists (e.g. real Telegram but limited channels) |

---

## ATS Platforms

High-leverage because one connector unlocks many companies.

| Source      | URL                          | Inventory Status | **Implementation** | Notes |
|-------------|------------------------------|------------------|--------------------|-------|
| Greenhouse  | https://www.greenhouse.io/   | priority         | **real**           | Full public job board API |
| Lever       | https://www.lever.co/        | priority         | **real**           | Good pagination support |
| Ashby       | https://www.ashbyhq.com/     | priority         | **real**           | Rate-limited public API |
| Workable    | https://www.workable.com/    | candidate        | **none**           | Good candidate for Wave 1-2 |
| Recruitee   | https://recruitee.com/       | candidate        | **none**           | Worth adding in Wave 2 |

---

## Job Boards

| Source            | URL                              | Inventory Status | **Implementation** | Notes |
|-------------------|----------------------------------|------------------|--------------------|-------|
| Remote OK         | https://remoteok.com/            | priority         | **real**           | Currently one of the strongest live sources |
| We Work Remotely  | https://weworkremotely.com/      | candidate        | **none**           | High priority for Wave 1 (remote) |
| Arc.dev           | https://arc.dev/                 | candidate        | **none**           | Remote tech roles |
| Wellfound         | https://wellfound.com/           | priority         | **stub**           | High relevance for startup ops roles |
| Otta              | https://otta.com/                | candidate        | **none**           | Startup/tech |
| Habr Career       | https://career.habr.com/         | priority         | **stub**           | RU tech |
| hh.ru             | https://hh.ru/                   | priority         | **stub**           | High anti-bot difficulty |
| LinkedIn Jobs     | https://www.linkedin.com/jobs/   | priority         | **none**           | Very high effort |
| Indeed            | https://www.indeed.com/          | candidate        | **none**           | Noisy, high dedup cost |
| Solana Jobs       | https://jobs.solana.com/         | priority         | **stub**           | Ecosystem specific |

---

## Telegram Channels

Telegram is now high-value because we have a **real** Telethon implementation.

| Channel            | Handle             | Inventory Status | **Implementation** | Notes |
|--------------------|--------------------|------------------|--------------------|-------|
| cryptohiring_1     | @cryptohiring_1    | priority         | **partial**        | High relevance (Web3) |
| tonhunt            | @tonhunt           | priority         | **partial**        | TON ecosystem |
| smerkisjobs        | @smerkisjobs       | priority         | **partial**        | Blum + partners |
| hrlunapark         | @hrlunapark        | candidate        | **none**           | Engineering heavy |
| rfoundersjobs      | @rfoundersjobs     | candidate        | **none**           | - |
| crypto_talents     | @crypto_talents    | candidate        | **none**           | - |
| hiring_by_lukina   | @hiring_by_lukina  | candidate        | **none**           | - |
| zarubezhom_jobs    | @zarubezhom_jobs   | candidate        | **none**           | - |

**Action**: Expand active channels using real TelegramConnector (see `implementation-plan-sources.md` Wave 1).

---

## Company Career Pages & Other

| Type                    | Status | Notes |
|-------------------------|--------|-------|
| Direct company pages    | **none** | Potential future seed-based crawler |
| IDAgent companies       | research-needed | Low priority |

---

## Summary (Current Real Coverage)

- **Strong**: Greenhouse, Ashby, Lever, RemoteOK, Telegram (infrastructure)
- **Medium**: Wellfound, Solana, Habr, hh.ru (stubs only)
- **Weak / Missing**: We Work Remotely, Arc.dev, Otta, Workable, Recruitee, LinkedIn, most Telegram channels

See `docs/architecture/implementation-plan-sources.md` for the recommended connection order.