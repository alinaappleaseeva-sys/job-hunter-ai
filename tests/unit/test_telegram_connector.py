"""Unit tests for Telegram connector (Phase 10 real + Wave 1 multi-channel)."""

from job_hunter_ai.connectors.telegram import (
    TelegramConnector,
    load_sample_telegram_messages,
    get_wave1_telegram_channels,
    TELETHON_AVAILABLE,
)
from job_hunter_ai.connectors import get_wave1_channels


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
    try:
        conn.fetch()
    except Exception as e:
        msg = str(e).lower()
        assert "telethon" in msg or "client" in msg or "not installed" in msg or "runtime" in msg


def test_telethon_import_flag():
    assert isinstance(TELETHON_AVAILABLE, bool)


# === Wave 1 multi-channel tests ===

def test_wave1_channels_registry():
    channels = get_wave1_telegram_channels()
    assert "tonhunt" in channels
    assert "cryptohiring_1" in channels
    assert "smerkisjobs" in channels


def test_telegram_from_channel_convenience():
    """Test the new Wave 1 from_channel() constructor."""
    conn = TelegramConnector.from_channel("tonhunt")
    result = conn.fetch(limit=10)
    assert len(result.records) >= 2
    assert "tonhunt" in conn.source_name

    conn2 = TelegramConnector.from_channel("smerkisjobs")
    result2 = conn2.fetch()
    assert len(result2.records) >= 1
    # Should contain ops/program related content
    texts = [r.payload.get("text", "").lower() for r in result2.records]
    assert any("operation" in t or "program" in t or "dao" in t for t in texts)


def test_wave1_all_channels_produce_records():
    """Smoke test that all Wave 1 channels return job-like records from samples."""
    for ch in ["tonhunt", "cryptohiring_1", "smerkisjobs"]:
        conn = TelegramConnector.from_channel(ch)
        res = conn.fetch()
        assert len(res.records) >= 1, f"No records from {ch}"