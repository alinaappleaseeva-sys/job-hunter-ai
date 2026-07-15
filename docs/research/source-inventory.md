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
| web3.career            | https://web3.career | ... | HTML | ... | high | 0.20 (general board) |  (esp. /operations-jobs, /dao-jobs, /treasury-jobs, filters) | DAO-Ops, Governance Specialist, Treasury Ops, Operations Associate, Head of Ops/Gov | HTML pages (public, filterable); possible API (partner/docs exist) | Low-medium ghost; good speed (many "New"); low anti-bot on listings | High priority (real needed) | "Operations Jobs in Web3 - Jul 2026
**Update (this iteration)**: web3.career HTML scraper implemented (operations-jobs + dao-jobs). findweb3.com/jobs/dao and remote3.co connectors added. All three now poll key pages and emit RawSourceRecord with segment_relevant flag. (11-12 New)". Excellent coverage for segment. Scrape or API first. |
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

**Action**: Expand `telegram_channels.py` registry with Web3/DAO-relevant ones. Added improved `is_telegram_job_signal` + segment keywords + negative patterns (2026-07-15). Target noise ≤35%.

**Current Wave 1 status (tuned - 2026-07-15)**:
- 7 channels: cryptohiring_1, tonhunt, smerkisjobs, web3hiring, dejob_global, **cryptojobslist**, **web3jobs**
- Filter tuned: stronger positives (Head of Ops, Senior Operations, DAO Ops, Treasury Ops, Governance Lead, etc.), more negatives, score boosts seniority + domain + remote.
- Eval (37 messages): **67.6% passed**, **59.5% high score (>0.7)**, **70% segment keywords**, still only 1 false positive.
- cryptojobslist: RSS connector MVP ready (0 items typical).
- Protocol seeds: loader + minimal fetch stubs (Lido/Optimism/Arbitrum/karpatkey) implemented.

## Protocol / DAO Career Pages + Governance / Contributors Surfaces (Expanded July 2026)

**Native sources are now the highest priority.** General boards have low precision for the target segment.

| Protocol / Org | ops_relevance | typical_roles | careers | governance | Discord/Snapshot | last_checked | notes |
|----------------|---------------|---------------|---------|------------|------------------|--------------|-------|
| Lido | high | dao, treasury, governance, staking | https://lido.fi/careers | https://research.lido.fi/, https://snapshot.box/#/s:lido-snapshot.eth | https://discord.gg/lido / https://snapshot.box/#/s:lido-snapshot.eth | 2026-07-15 | Often posts ops, treasury, governance roles. |
| Optimism | high | l2, governance, collective, ops | https://jobs.theblockchainassociation.org/companies/optimism-foundation-2 | https://gov.optimism.io/, https://docs.optimism.io/governance | https://discord.gg/optimism / - | 2026-07-15 | Foundation roles often include ops/governance. |
| Arbitrum | high | l2, dao, governance, ops | https://jobs.arbitrum.io/ | https://forum.arbitrum.foundation/, https://snapshot.box/#/s:arbitrum.eth | https://discord.gg/arbitrum / https://snapshot.box/#/s:arbitrum.eth | 2026-07-15 | Foundation and DAO-related ops roles. |
| Gitcoin | high | dao, grants, public-goods, ops | https://gitcoin.co/careers | https://gov.gitcoin.co/ | https://discord.gg/gitcoin / - | 2026-07-15 | High signal for DAO/Ops roles |
| karpatkey | high | defi, dao-ops, treasury, governance | https://www.karpatkey.com/careers | https://snapshot.box/#/s:karpatkey.eth | https://discord.gg/karpatkey / https://snapshot.box/#/s:karpatkey.eth | 2026-07-15 | Frequently posts DAO-Ops, Finance & Ops, Governance roles. |
| Safe | medium | wallet, infra, governance, ops | https://safe.global/careers | https://snapshot.box/#/s:safe.eth | https://discord.gg/safe / https://snapshot.box/#/s:safe.eth | 2026-07-15 | High signal for DAO/Ops roles |
| dYdX | medium | defi, dao, governance | https://dydx.exchange/careers | https://dydx.forum/ | - / - | 2026-07-15 | High signal for DAO/Ops roles |
| Aragon | medium | dao, governance, tooling | https://aragon.org/careers | https://forum.aragon.org/ | - / - | 2026-07-15 | High signal for DAO/Ops roles |
| StableLab | medium | dao, governance, ops | - | https://snapshot.box/#/s:stablelab.eth | - / https://snapshot.box/#/s:stablelab.eth | 2026-07-15 | High signal for DAO/Ops roles |
| Gitcoin (additional contributor surfaces) | medium | ops, governance, treasury | - | - | - / - | 2026-07-15 | High signal for DAO/Ops roles |
| Aave | high | defi, lending, governance, dao-ops | https://aave.com/careers | https://governance.aave.com/, https://snapshot.box/#/s:aave.eth | https://discord.gg/aave / https://snapshot.box/#/s:aave.eth | 2026-07-15 | DeFi protocol ops, governance, treasury roles. |
| Uniswap | high | defi, dex, governance, dao | https://boards.greenhouse.io/uniswap | https://gov.uniswap.org/, https://snapshot.box/#/s:uniswap | https://discord.gg/uniswap / https://snapshot.box/#/s:uniswap | 2026-07-15 | Protocol ops and contributor roles. |
| MakerDAO | high | defi, stablecoin, governance, treasury | https://www.makerdao.com/en/careers | https://forum.makerdao.com/, https://vote.makerdao.com/ | https://discord.gg/makerdao / - | 2026-07-15 | Core unit ops, governance, treasury. |
| Polymarket | high | prediction-market, governance, ops | https://boards.greenhouse.io/polymarket | - | - / - | 2026-07-15 | High signal for DAO/Ops roles |
| Solana Foundation | high | l1, ecosystem, grants, ops | https://jobs.solana.com/ | https://forum.solana.com/ | https://discord.gg/solana / - | 2026-07-15 | Ecosystem ops, grants, contributor programs. |
| Polygon | high | l2, ecosystem, governance, ops | https://polygon.technology/careers | https://forum.polygon.technology/, https://snapshot.box/#/s:polygon.eth | https://discord.gg/polygon / https://snapshot.box/#/s:polygon.eth | 2026-07-15 | High signal for DAO/Ops roles |
| Ethereum Foundation | high | l1, research, ecosystem, program-management | https://jobs.ethereum.org/ | - | - / - | 2026-07-15 | Core research, ops, program management. |
| Base (Coinbase) | high | l2, ecosystem, ops | https://www.coinbase.com/careers | https://base.mirror.xyz/ | https://discord.gg/base / - | 2026-07-15 | Base ecosystem ops roles often posted under Coinbase. |
| EigenLayer | high | restaking, infra, governance, ops | https://jobs.ashbyhq.com/eigenlayer | https://forum.eigenlayer.xyz/ | https://discord.gg/eigenlayer / - | 2026-07-15 | High signal for DAO/Ops roles |
| Chainlink | medium | oracle, infra, ecosystem, ops | https://chain.link/careers | https://forum.chain.link/ | https://discord.gg/chainlink / - | 2026-07-15 | High signal for DAO/Ops roles |
| TON Foundation | high | l1, ecosystem, ops, growth | https://careers.ton.org/ | https://forum.ton.org/ | https://t.me/toncoin / - | 2026-07-15 | Active growth, operations, ecosystem roles. |
| Blockstream | medium | bitcoin, infra, ops | https://blockstream.com/careers/ | - | - / - | 2026-07-15 | Bitcoin/Web3 infra ops roles. |
| Balancer DAO | high | defi, dao, governance, ops | https://balancer.fi/about#careers | https://forum.balancer.fi/, https://snapshot.box/#/s:balancer.eth | https://discord.gg/balancer / https://snapshot.box/#/s:balancer.eth | 2026-07-15 | High signal for DAO/Ops roles |
| Curve DAO | high | defi, dao, governance, treasury | - | https://gov.curve.fi/, https://snapshot.box/#/s:curve.eth | https://discord.gg/curvefi / https://snapshot.box/#/s:curve.eth | 2026-07-15 | High signal for DAO/Ops roles |
| Sushi DAO | medium | defi, dao, governance | - | https://forum.sushi.com/ | https://discord.gg/sushiswap / - | 2026-07-15 | High signal for DAO/Ops roles |
| Compound | high | defi, lending, governance, treasury | - | https://forum.compound.finance/, https://snapshot.box/#/s:comp | https://discord.gg/compoundfinance / https://snapshot.box/#/s:comp | 2026-07-15 | High signal for DAO/Ops roles |
| ENS DAO | high | dao, governance, naming, ops | - | https://discuss.ens.domains/, https://snapshot.box/#/s:ens.eth | https://discord.gg/ens / https://snapshot.box/#/s:ens.eth | 2026-07-15 | High signal for DAO/Ops roles |
| Decentraland | medium | metaverse, dao, governance, ops | https://decentraland.org/careers | https://forum.decentraland.org/ | https://discord.gg/decentraland / - | 2026-07-15 | High signal for DAO/Ops roles |
| Mercuryo | medium | crypto-services, ops, remote | https://mercuryo.io/careers | - | - / - | 2026-07-15 | High signal for DAO/Ops roles |


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


## Quality Thresholds + Lessons Learned (July 2026 update)

### Per-source accepted_relevance_threshold

| Source              | accepted_relevance_threshold | Rationale |
|---------------------|------------------------------|-----------|
| web3career / remote3 | 0.20                         | General boards — accept lower precision at start for volume |
| findweb3            | 0.35                         | More DAO-focused |
| protocol_seeds / governance forums | 0.40 | Native sources — higher quality and relevance expected |

### Lessons Learned (critical)

**General boards deliver volume but very low target precision** for our narrow segment (Head/Senior Ops + DAO/Governance/Treasury/Contributor Coordination in Web3/DeFi/Protocols).

- After strict scoring (strong seniority + domain required + heavy negatives for CEX/regulatory/trading ops), strict high-relevance on web3.career + remote3 is typically **0–5%**.
- Many "Operations" roles are mid-level execution (Associate/Specialist), TradFi-adjacent (Trading Ops, Clearing, Risk, Compliance), or completely off-domain (Design Ops, Revenue Ops, IT Ops).
- DAO-specific pages sometimes return project names instead of jobs.
- "Program Manager" alone is not enough — must be paired with DAO/Gov/Treasury context.

**Recommendation going forward**:
- **Native protocol/DAO surfaces >> general boards** (priority order).
- Keep general boards (web3.career, remote3, etc.) with low thresholds (0.20) for coverage, but **deprioritize** them in ranking and source selection.
- Use strict `segment_scorer` (new module) everywhere.
- Invest heavily in protocol_seeds (20+ protocols), governance forums, Snapshot, contributor programs, and direct DAO ops surfaces.
- General boards are now secondary "supplement" sources, not primary.

See `src/job_hunter_ai/scoring/segment_scorer.py` for the current strict positive/negative logic + crypto-native bonuses.

### Updated Prioritization (native-first)

1. **Native / High-relevance** (protocol career pages, governance forums, Snapshot, DAO contributor boards, targeted Telegram)
2. **DAO-focused boards** (findweb3, specific DAO job pages)
3. **General Web3 boards** (web3.career, cryptojobslist, remote3) — with low weight
4. **Broad remote/tech** — only if needed for volume

This shift is a direct consequence of the quality evals performed in July 2026.
