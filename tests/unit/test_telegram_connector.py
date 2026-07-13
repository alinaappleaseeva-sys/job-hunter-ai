"""Unit tests for Telegram connector stub (Phase 8)."""

from job_hunter_ai.connectors.telegram import TelegramConnector, load_sample_telegram_messages

def test_telegram_stub_emits_from_sample():
    msgs = load_sample_telegram_messages()
    conn = TelegramConnector("telegram:tonhunt", messages=msgs)
    result = conn.fetch()
    # Sample has 2, but filter may keep job-like
    assert len(result.records) >= 1
    rec = result.records[0]
    assert "telegram" in rec.source_name
    assert rec.source_type == "repost_channel"
    assert "TON" in rec.payload.get("text", "") or "hiring" in rec.payload.get("text", "").lower()
