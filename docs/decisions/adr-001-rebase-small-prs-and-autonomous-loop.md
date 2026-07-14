# ADR-001: Rebase Workflow + Small PRs + Autonomous Quality Loop

**Date**: 2026-07-14  
**Status**: Accepted  
**Deciders**: Alina + Hermes Agent

## Context
The pipeline quality improvement effort is a long, iterative loop with many small changes (sample cleanup, role family rules, requirements extraction, source additions). We need high traceability, fast feedback, and the ability to roll back or A/B components easily.

Previous work used rebase + small PRs successfully.

## Decision
- Use **rebase** (not merge) on feature branches.
- Keep PRs small and focused on one logical change.
- Run the autonomous quality loop with regular PRs after every meaningful batch.
- Use feature flags / config toggles for ranking components (role_family, hard_reqs, recency soft, penalties) to enable safe iteration.

## Consequences
**Positive**:
- Clean git history.
- Easy to review and revert individual changes.
- Fast integration of incremental improvements.
- Good support for autonomous agent making many small PRs.
- Feature flags reduce risk of breaking the main ranking path.

**Negative / Trade-offs**:
- Requires discipline to rebase frequently.
- More PR overhead than one big branch.
- Feature flag debt must be cleaned up later.

## Alternatives Considered
- Long-lived feature branch → poor visibility and hard to review.
- Merge workflow → messy history, harder to bisect.

This decision aligns with the project's existing preferences for rebase and small reviewable PRs.