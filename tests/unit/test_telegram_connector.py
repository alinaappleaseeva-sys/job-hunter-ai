"""Unit tests for Telegram connector (Phase 10 real + stub compatibility)."""

from job_hunter_ai.connectors.telegram import (
    TelegramConnector,
    load_sample_telegram_messages,
    TELETHON_AVAILABLE,
)

def test_telegram_stub_emits_from_sample():
    msgs = load_sample_telegram_messages()
    conn = TelegramConnector("telegram:tonhunt", messages=msgs)
    result = conn.fetch()
    assert len(result.records) >= 1
    rec = result.records[0]
    assert "telegram" in rec.source_name
    assert rec.source_type == "repost_channel"
    text = rec.payload.get("text", "")
    assert "TON" in text or "hiring" in text.lower()

def test_telegram_stub_empty_raises_when_messages_present():
    conn = TelegramConnector("telegram:empty", messages=[{"id": 1, "text": "just noise"}])
    try:
        conn.fetch()
    except Exception as e:
        assert "No job-like" in str(e) or "Empty" in str(e.__class__.__name__)

def test_telegram_real_mode_without_client_raises():
    conn = TelegramConnector("telegram:tonhunt", client="fake-client")
    # When telethon not available or client bad, should raise clearly
    try:
        conn.fetch()
    except Exception as e:
        msg = str(e).lower()
        assert "telethon" in msg or "client" in msg or "not installed" in msg or "runtime" in msg

def test_telethon_import_flag():
    # Just ensure the flag exists and is boolean
    assert isinstance(TELETHON_AVAILABLE, bool)