# feedback_actions

Labeled examples for **Phase 9** Delivery UX (feedback and actions).

## Purpose
Evaluate that user actions (relevant, not_relevant, duplicate, ghost_likely, applied) are:
- persisted with full traceability to RankedJob, ScoreExplanation, ghost_score
- no silent actions
- usable for future iteration (ranking/ghost improvement)

See `implementation-plan.md` Phase 9.

## Format
Each example:
- profile_id
- ranked_job_id (or canonical_job_id)
- action
- reason (optional user note)
- expected_trace: list of fields that must be recorded (score_breakdown, ghost_score, explanations)
- label: valid / invalid_trace / silent_action
