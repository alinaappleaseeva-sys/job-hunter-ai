# Source Inventory — Web3 / DAO / Operations Focus (Jul 2026)

**Purpose**:
- Track all candidate sources with emphasis on the confirmed target segment: **Head/Senior Operations + DAO/Governance/Treasury/Contributor Coordination/Program Management in Web3/DeFi/Protocols (and crypto infra)**.
- Not only "pure DAO" — deliberately broader: DeFi protocols, L1/L2, treasury/gov in projects, contributor ops, infra DAOs.
- Show real implementation status.
- Support prioritization by **Coverage × Relevance / (Effort + Risk)**.
- Enable quick feasibility checks and expansion.

See `docs/research/target-segment.md` for the exact segment definition (this takes precedence).

## Status Legend

| Status     | Meaning |
|------------|---------|
| **real**   | Live connector fetching real data |
| **stub**   | Sample/fixture only |
| **none**   | Not implemented |
| **partial**| Real path exists but limited scope (e.g. few channels) |

**New columns for this day**:
- **Approx. Real Roles (examples)**: Concrete titles observed or typical for the source (10–20+ collected).
- **Feasibility**: RSS / API / scraping / login / Discord / other.
- **Risk**: ghost jobs, update speed, anti-bot, noise, maintenance.

## Example Real Roles (collected for segment validation)

From web3.career, cryptojobslist, findweb3, DAO boards, protocol postings, Telegram, and related (Jul 2026 context):
1. DAO-Ops Manager (karpatkey / Lido)
2. Governance Specialist (Lido, StableLab)
3. DAO Finance & Ops Strategist (karpatkey)
4. Treasury Operations Manager / Treasury Manager (various DeFi, BCB Group, Ripple)
5. Head of OpCo (Arbitrum)
6. Operations Coordinator — Governance Team (Arbitrum Foundation)
7. On-Chain Operations Manager
8. DAO Growth Analyst - DeFi (karpatkey)
9. Voting Power Distribution Lead (karpatkey)
10. Junior Chief of Staff / Operations Manager (Gitcoin)
11. Strategic Project Manager Operations (Lido)
12. Head of Operations and Governance (DAO / Key to Web3 etc.)
13. DAO Coordinator
14. Governance Team roles / Proposal & Voting Ops
15. Business Operations Manager (Web3 protocols)
16. Contributor Coordination / Program roles in collectives
17. Treasury & FinOps Analyst / Settlement roles
18. Operations Associate (DeFi / multi-asset)
19. Head of Governance (Arbitrum Foundation / protocols)
20. Protocol / DAO Operations roles in L2s and infra (Optimism, Arbitrum, Safe, dYdX, Aragon, etc.)

These confirm strong signal on the target segment across dedicated boards and protocol surfaces.

## Prioritization Framework (for this segment)

**Priority = (Coverage × Relevance) / (Effort + Maintenance Risk)**

From current view (screenshot + validation):
- **Highest**: Pure Web3 boards + DAO-specific + Protocol/DAO pages + targeted Telegram (high relevance + good ops/DAO volume).
- **Medium+**: Web3/remote aggregators.
- **Lower for now**: Broad generic tech boards (Otta, Arc, We Work Remotely, etc.) — use only after core coverage.

## Web3 / DAO / Ops Focused Boards

| Source                  | URL / Type                          | Approx. Real Roles (examples) | Feasibility                  | Risk (ghost, speed, anti-bot, noise) | Status      | Notes / Priority |
|-------------------------|-------------------------------------|-------------------------------|------------------------------|--------------------------------------|-------------|------------------|
| web3.career            | https://web3.career (esp. /operations-jobs, /dao-jobs, /treasury-jobs, filters) | DAO-Ops, Governance Specialist, Treasury Ops, Operations Associate, Head of Ops/Gov | HTML pages (public, filterable); possible API (partner/docs exist) | Low-medium ghost; good speed (many "New"); low anti-bot on listings | High priority (real needed) | "Operations Jobs in Web3 - Jul 2026 (11-12 New)". Excellent coverage for segment. Scrape or API first. |
| Cryptocurrency Jobs / Blockchain Jobs | https://cryptojobslist.com/ (incl. DAO ops) | Wide Web3 ops, treasury, governance, protocol ops | RSS exists (structure confirmed); HTML | Medium ghost risk on boards; high update speed (200+ new claimed); low anti-bot | High priority | RSS parse attractive for quick wins. "203-214 new" scale. |
| DAO Jobs boards        | https://findweb3.com/jobs/dao ; aworker.io/dao-jobs | DAO-Ops Manager, Governance Specialist, DAO Finance & Ops, Voting Power Lead, DAO Coordinator | HTML scrape (public listings) | Medium volume per source; good relevance; low-moderate maintenance | High (DAO-specific) | Very high relevance. Low effort entry. |
| cryptocurrencyjobs.co  | https://cryptocurrencyjobs.co/     | Operations, Treasury, Governance in crypto | Likely RSS/HTML (similar boards) | Similar to cryptojobslist | High | Complementary volume. |
| Remote3.co + BuiltIn Web3 | Remote3.co, BuiltIn Web3 aggregators | Remote Web3 ops, program, contributor roles | HTML / possible RSS | Medium coverage for segment | Medium+ | Good remote signal. |

## Telegram (High-Leverage for Web3 Signals)

Existing Telethon infrastructure gives big multiplier.

| Channel / Handle     | URL / Handle          | Approx. Real Roles                  | Feasibility | Risk                          | Status     | Notes |
|----------------------|-----------------------|-------------------------------------|-------------|-------------------------------|------------|-------|
| web3hiring          | @web3hiring          | Broad Web3 (eng + non-tech ops/gov) | Telethon (real client) + parsing | Noise (need filters); low ghost if curated; daily updates | High priority (expand) | 60k+ subs. Daily global feed. |
| DeJob_Global        | @DeJob_Global        | DAO jobs & decentralized teams     | Same       | Good for DAO focus; salary tags often present | High      | Explicit DAO focus. |
| cryptojobslist / others | @cryptojobslist, @DeJob etc. | Various Web3 ops/DAO               | Same       | Noise varies                    | High (add) | Expand list. |
| Older Web3 TG (crypto_talents etc.) | Various            | Mix                                 | Same       | Quality validation needed      | Candidate | Re-evaluate against segment. |

**Action**: Expand `sources/telegram_channels.yaml` or registry with Web3/DAO-relevant ones. Add light per-channel filters. Target noise ≤35% on new channels.

## Protocol / DAO Career Pages + Governance / Contributors Surfaces

These give **maximum relevance** (direct from target organizations) but lower per-source volume. Many use existing ATS (Greenhouse/Lever/Ashby = already real).

**How they typically publish**:
- Dedicated `/careers`, `/jobs`, `/join`, "Open roles".
- Governance forums (Snapshot, Discourse, gov.optimism.io, research.lido.fi).
- Discord (announcements, #jobs, #hiring, contributor channels).
- X / Telegram posts.
- Contributor programs, grants, bounties, or "working groups" calls.
- Sometimes on third-party (jobs.theblockchainassociation.org, aworker, findweb3).

**Specific examples (start here for seeding + targeted fetch)**:
- Lido (Lido DAO): Governance forum (research.lido.fi), DAO Ops requests, Snapshot (lido-snapshot.eth). Careers often via partners or direct.
- Optimism Collective: gov.optimism.io (governance), jobs via blockchainassociation or OP Labs postings.
- Arbitrum: jobs.arbitrum.io (or Foundation board), forum.arbitrum.foundation, Snapshot, Discord.
- Gitcoin: Site + Discord + grants/contributor paths.
- karpatkey: Frequently appears in DAO jobs boards; direct or via partners.
- Safe, dYdX, Aragon, StableLab, Gitcoin, others (L2s/infra): Mix of own pages, Greenhouse/Ashby, Discord governance/ops channels, X.
- Additional: The Blockchain Association job board, individual protocol sites (e.g. Morpho, Ripple crypto roles, etc.).

**Feasibility**: High for ATS-using ones (already wired). Medium for custom pages (scrape or RSS if available). Discord: alerts or public channel monitoring (more work). Governance forums: often RSS or scrape + manual seed list.

**Risk**: Low volume per page → need many seeds + good dedup. High relevance offsets this. Ghost jobs rare on official pages.

**Status**: Mostly **none** for direct non-ATS pages. Start with seed list + generic or per-protocol fetchers after core boards.

## Other / Lower for Segment (for completeness)

- Broad remote/tech: Remote OK (still strong for remote ops signal — keep real), We Work Remotely, Arc.dev, Otta, Wellfound (startup ops relevance), Solana Jobs.
- ATS (still valuable multiplier): Greenhouse, Ashby, Lever (real) — many protocols use them. Workable/Recruitee next.
- High-effort: LinkedIn, hh.ru, Indeed (deprioritize or last).

## Quick Feasibility Checks — Top 6–8 (as of this day)

1. **cryptojobslist RSS** — Feed structure confirmed (valid XML with channel). Items fetchable in principle (some fetches return limited; handle pagination or full endpoint). High feasibility for quick real connector.
2. **web3.career operations/dao pages** — Public HTML, filterable URLs (e.g. /operations-jobs shows "Jul 2026 (X New)"). Scrape straightforward (title, company, location, salary, tags, apply). API exists per their docs (volume limits unknown). Quick real data possible.
3. **@web3hiring / @DeJob_Global** — Existing Telethon path. Adding channels = config + parsing. Lowest effort, immediate value.
4. **findweb3.com/jobs/dao** — Public listings, clear roles like DAO-Ops Manager etc. HTML scrape feasible.
5. **Protocol pages (Lido/Arbitrum/Optimism)** — Mix: some ATS (already covered), others forum/Discord/HTML. Start with 5–10 seed pages + existing normalizers.
6. **Remote3.co** — Aggregator; public listings, likely scrape or RSS. Medium feasibility.
7. **cryptocurrencyjobs.co** — Board style, similar to cryptojobslist. RSS/HTML check recommended next.
8. **Discord channels** (protocol gov/ops) — Feasible via alerts or bot for public channels; higher effort than RSS/scrape.

**Overall**: Top Web3 boards + Telegram can be made "real" quickly with existing infra patterns (RemoteOK/Telegram connectors as reference). Protocol surfaces next for relevance boost.

## Summary (Post This Day)

- **Strong after expansion**: web3.career (filtered), cryptojobslist + crypto jobs boards, key Telegram (@web3hiring, @DeJob_Global), DAO-specific boards, existing ATS for protocols that use them.
- **Next wave**: Targeted protocol career/governance pages + Discord signals + more Telegram.
- **Deprioritize initially**: Generic broad tech boards unless they deliver clear ops/DAO volume.
- **Cross-cutting**: Strong dedup + ghosting + per-source noise evals required. Source registry/config for easy on/off.

See `docs/architecture/implementation-plan-sources.md` for updated waves, sequence, and monitoring plan.

**Next actions** (from this inventory day):
- Implement quick connectors for high-priority Web3 boards + expand Telegram.
- Build seed list of 10–20 protocol career/gov surfaces.
- Add evals for new sources.
- Monitoring/alerts setup (see plan doc).
