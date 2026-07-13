# Evaluation Datasets

Store curated examples here.

## Dataset groups

| Directory | Phase | Status |
|---|---|---|
| `ingestion/` | 2–3 / 8 | active |
| `normalization_gold/` | 4 | active |
| `dedup_regression/` | 5 / 8 | active |
| `ranking_topk/` | 6 | active |
| `ghosting_precision/` | 7 | active |
| `feedback_actions/` | 9 | active |
| `phase10_operational/` | **10** | active (source health, telegram noise, eval regression) |
| `telegram/` | **10 / Wave 1** | active — expanded channel quality examples (tonhunt, cryptohiring_1, smerkisjobs) |

## Rules for dataset changes
- New operational / health / regression logic → extend `phase10_operational` + re-run gates.
- Material ranking/ghosting/ingestion changes require post-change eval summary (see Phase 10 suite).
- When expanding Telegram (Wave 1), add examples to `telegram/telegram_quality.jsonl`.