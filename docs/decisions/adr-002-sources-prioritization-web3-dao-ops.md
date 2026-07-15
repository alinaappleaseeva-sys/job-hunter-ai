# ADR-002: Sources Prioritization for Web3/DAO/Ops Segment (2026-07-15)

**Status**: Accepted

**Date**: 2026-07-15

## Context
We are building coverage for a specific target segment: Head/Senior Operations + DAO/Governance/Treasury/Contributor Coordination/Program Management in Web3/DeFi/Protocols (broader than pure DAO).

Previous inventory and plan focused heavily on general ATS + broad remote/tech boards. A dedicated "день по выбору sources" was run to re-focus.

Data sources for decision:
- Screenshot of current view of categories with rough (Coverage × Relevance / Effort) scoring.
- Validation of real role examples on web3.career, cryptojobslist, findweb3, protocol boards.
- Feasibility probes (RSS for cryptojobslist confirmed; web3.career public pages; Telegram existing infra).
- Segment confirmation from user.

## Decision
1. **Primary focus shift**: Prioritize pure Web3 boards (web3.career with ops/dao/treasury filters), DAO-specific boards (findweb3.com/jobs/dao etc.), targeted Telegram channels (@web3hiring, @DeJob_Global), and protocol/DAO career + governance surfaces.

2. **New inventory columns**: Added "Approx. Real Roles (examples)", "Feasibility (RSS/API/scraping/...)", "Risk (ghost/speed/anti-bot/noise)" to source-inventory.md. Collected 20 concrete role examples.

3. **Feasibility-first checks**: Top 6–8 sources evaluated for "can we pull real data quickly" (not full implementation). RSS and public HTML look promising for quick wins.

4. **Waves updated** (see implementation-plan-sources.md):
   - Wave 1: Telegram expansion + web3.career + cryptojobslist + DAO boards.
   - Wave 2: Protocol career/gov pages (seed list) + more channels.
   - Lower: Generic tech boards initially.

5. **Protocol surfaces**: Explicit list started (Lido, Arbitrum, Optimism, Gitcoin, karpatkey, Safe etc.) + publication patterns (careers page / governance forum / Discord / X / third-party).

6. **Monitoring plan**: RSS polling, expanded Telegram, X targeted searches, Discord public channels, governance forums, source health tracking, alerts integrated with pipeline.

7. **Segment doc created**: `docs/research/target-segment.md` as single source of truth.

## Consequences
- Higher immediate relevance for the actual target profile.
- Need to strengthen dedup + ghosting + noise filters as more Web3 board/Telegram volume comes in.
- Protocol pages will require seed management + per-source or generic fetchers.
- Monitoring adds operational load but necessary for freshness and "new" signals.
- ATS (Greenhouse/Ashby/Lever) remain valuable multipliers (many protocols use them) — not deprioritized.

## Alternatives Considered
- Continue broad remote/tech first → Rejected (lower relevance to confirmed segment).
- Only protocol pages → Rejected (volume too low without boards + Telegram as base).
- LinkedIn-heavy early → Rejected (high effort/anti-bot, not justified yet).

## Next Steps
- Implement Wave 1 connectors.
- Build protocol seed list + fetch methods.
- Add evals and health for new sources.
- Execute monitoring plan elements.

**Related**:
- docs/research/source-inventory.md (updated)
- docs/research/target-segment.md (new)
- docs/architecture/implementation-plan-sources.md (updated with this day's work)
