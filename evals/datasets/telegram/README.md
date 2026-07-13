# Telegram Quality Dataset

Labeled examples for measuring job signal vs noise in Telegram channels.

Used for:
- telegram_noise rubric
- Phase 10 operational gates
- Wave 1 Telegram expansion eval

## Key Channels in Wave 1

- tonhunt (TON ecosystem)
- cryptohiring_1 (general crypto hiring)
- smerkisjobs (Blum + partners, often relevant for ops/program roles)

## Fields
- is_job: clear hiring intent
- is_unique: not a duplicate of a recent posting
- freshness_hours: approximate age
- label: good_signal | duplicate_stale | noise

## Gates (from rubric)
- job_signal_rate ≥ 0.60 on active channels
- unique_job_rate ≥ 0.70
- median freshness ≤ 24h for useful signal

## Usage
See `evals/suites/phase10_operational.yaml` and `tests/unit/test_phase10_operational.py`.