# Delivery

Delivery turns evaluated job matches (RankedJob) into inboxes, digests, or alerts.

This layer should never bypass ranking or ghosting policy checks.

## Public API (Phase 9 v1)
- `build_digest(profile, ranked_jobs)` -> payload with explanations
- `apply_action(ranked_job, profile_id, action, reason)` -> FeedbackEvent
- `persist_feedback(event, storage)`

Actions: relevant | not_relevant | duplicate | ghost_likely | applied

All actions produce traceable FeedbackEvent (score_breakdown + explanations + ghost_score).

## Storage
Feedback events can be persisted via extended JobStorage or dedicated feedback store.
MVP uses in-memory for now.
