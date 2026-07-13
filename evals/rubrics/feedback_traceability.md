# Feedback Traceability Rubric (Phase 9)

## Goals
- Every user action must be traceable to the exact ranking/ghost decision that led to it.
- No silent actions (every action creates a persisted record with context).
- Feedback must be usable to improve ranking and ghosting (future phases).

## Labels
- valid: action recorded with required trace fields (score_breakdown, explanations, ghost_score where applicable).
- invalid_trace: action recorded but missing key fields from RankedJob/ghost.
- silent_action: action taken without any persistence or audit record.

## Gates (from suite)
- traceability_rate >= 0.90 (at least 90% of actions have full trace)
- no_silent_actions: 100% of actions produce records
- explanations_exposed: actions on RankedJob expose match explanations

## Example good record
{
  "action": "relevant",
  "canonical_job_id": "...",
  "profile_id": "...",
  "score_breakdown": { ... },
  "explanations": [ ... ],
  "ghost_score": 0.1,
  "timestamp": "..."
}
